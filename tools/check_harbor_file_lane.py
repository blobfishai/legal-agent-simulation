#!/usr/bin/env python3
"""Gate the LAB file-lane staging and lane-split artifact contract."""
from __future__ import annotations

import importlib.util
import hashlib
import http.server
import json
import os
import subprocess
import tempfile
import threading
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GENERATOR_PATH = ROOT / "harbor" / "generate.py"
RECOVERY_TREE_FILES = 34
RECOVERY_TREE_BYTES = 113081
RECOVERY_TREE_SHA256 = "bbdcf02717bf2ad491bf5ebbe028ebd5d69f5427609fddb0aaca3ad8d4e88d5a"


def recovery_tree_fingerprint() -> tuple[int, int, str]:
    """Hash path names and bytes for the pinned Harvey sandbox/skill snapshot."""
    root = ROOT / "research" / "harvey-recovery"
    files = sorted(
        path
        for directory in ("sandbox", "skills")
        for path in (root / directory).rglob("*")
        if path.is_file()
    )
    digest = hashlib.sha256()
    byte_count = 0
    for path in files:
        relative = path.relative_to(root).as_posix().encode()
        payload = path.read_bytes()
        byte_count += len(payload)
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    return len(files), byte_count, digest.hexdigest()


def load_generator():
    spec = importlib.util.spec_from_file_location("harbor_generate", GENERATOR_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    generator = load_generator()
    commit = json.loads((ROOT / "research" / "repos-commits.json").read_text())["harveyai@harvey-labs"]
    assert recovery_tree_fingerprint() == (
        RECOVERY_TREE_FILES,
        RECOVERY_TREE_BYTES,
        RECOVERY_TREE_SHA256,
    )
    live_checked = False
    with tempfile.TemporaryDirectory(prefix="harbor-file-lane-") as temporary:
        base = Path(temporary)
        token_path = base / "solve-token.txt"
        token_path.write_text("cd" * 16)
        previous_token = os.environ.get("HARBOR_SOLVE_TOKEN")
        try:
            os.environ["HARBOR_SOLVE_TOKEN"] = "ab" * 16
            assert generator.resolve_solve_token(str(token_path)) == "ab" * 16
            del os.environ["HARBOR_SOLVE_TOKEN"]
            assert generator.resolve_solve_token(str(token_path)) == "cd" * 16
            os.environ["HARBOR_SOLVE_TOKEN"] = "not-a-valid-token"
            try:
                generator.resolve_solve_token(str(token_path))
                raise AssertionError("invalid release solve token was accepted")
            except RuntimeError as error:
                assert "32-128 lowercase hex" in str(error)
        finally:
            if previous_token is None:
                os.environ.pop("HARBOR_SOLVE_TOKEN", None)
            else:
                os.environ["HARBOR_SOLVE_TOKEN"] = previous_token
        documents_source = base / "source-documents"
        skills_source = base / "source-skills"
        documents_source.mkdir()
        for index in range(9):
            (documents_source / f"evidence-{index + 1}.txt").write_text(f"Evidence {index + 1}\n")
        for name in ("docx", "xlsx", "pptx"):
            skill = skills_source / name
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text(f"# {name}\n")
        source_instruction = "Review the evidence and output `antitrust-risk-memo.docx`."
        task = {
            "task_id": "lab_file_lane_gate",
            "prompt": source_instruction,
            "file_lane": {
                "source_task": "antitrust-competition/analyze-antitrust-hsr-strategy",
                "source_commit": commit,
                "documents_source": str(documents_source),
                "skills_source": str(skills_source),
                "deliverables": ["antitrust-risk-memo.docx"],
                "skills": ["docx", "xlsx", "pptx"],
            },
        }
        task_dir = base / "task"
        generator.stage_file_lane(task, str(task_dir))
        documents = sorted(path for path in (task_dir / "environment" / "documents").rglob("*") if path.is_file())
        assert len(documents) == 9, len(documents)
        assert all((task_dir / "environment" / "skills" / name / "SKILL.md").is_file()
                   for name in ("docx", "xlsx", "pptx"))

        # A clean Git checkout does not contain the 3.2 GB ignored Harvey
        # mirror. The tracked, commit-pinned recovery copy must therefore be a
        # complete staging source for authored file lanes.
        recovery_task = {
            **task,
            "task_id": "harvey_recovery_skills_gate",
            "file_lane": {
                **task["file_lane"],
                "skills_source": "research/harvey-recovery/skills",
            },
        }
        recovery_dir = base / "recovery-task"
        generator.stage_file_lane(recovery_task, str(recovery_dir))
        assert all((recovery_dir / "environment" / "skills" / name / "SKILL.md").is_file()
                   for name in ("docx", "xlsx", "pptx"))
        assert (ROOT / "research" / "harvey-recovery" / "sandbox" / "Dockerfile").is_file()

        instruction = generator.instruction_md(task)
        assert source_instruction in instruction
        assert "/workspace/documents" in instruction
        assert "/workspace/output/antitrust-risk-memo.docx" in instruction
        compose = generator.compose_yaml(task["task_id"], "world:v17", True)
        assert "source: ./documents" in compose and "read_only: true" in compose
        dockerfile = generator.lab_agent_dockerfile("lab-agent:v17")
        assert dockerfile.startswith("# File-lane") and "FROM lab-agent:v17" in dockerfile

        input_only = {
            **task,
            "task_id": "v21_input_only_gate",
            "file_lane": {
                **task["file_lane"],
                "inputs_only": True,
                "deliverables": [],
                "skills": [],
                "assertions": [],
                "grading": "determinate-state-and-trace",
            },
        }
        input_only_dir = base / "input-only-task"
        generator.stage_file_lane(input_only, str(input_only_dir))
        assert len(list((input_only_dir / "environment" / "documents").glob("*.txt"))) == 9
        assert not list((input_only_dir / "environment" / "skills").rglob("SKILL.md"))
        input_instruction = generator.instruction_md(input_only)
        assert "## Input-document lane" in input_instruction
        assert "do not create a separate filesystem deliverable" in " ".join(input_instruction.split())
        assert "Follow the exact output filename" not in input_instruction
        assert generator.validated_deliverables(input_only) == []

        output = base / "output"
        logs = base / "logs"
        output.mkdir()
        (output / "antitrust-risk-memo.docx").write_bytes(b"fixture deliverable")
        script = base / "test.sh"
        script.write_text(generator.test_sh(task))
        script.chmod(0o755)
        environment = {
            **os.environ,
            "WORKSPACE_OUTPUT": str(output),
            "HARBOR_LOGS": str(logs),
            "WORLD_VERIFY_URL": "http://127.0.0.1:1/verify",
        }
        subprocess.run(["bash", str(script)], env=environment, check=True,
                       capture_output=True, text=True)
        lane = json.loads((logs / "verifier" / "file-lane.json").read_text())
        reward = json.loads((logs / "verifier" / "reward.json").read_text())
        assert lane["file_passed"] is True
        assert lane["grade_kind"] == "output_contract_only"
        assert lane["state_passed"] is False
        assert lane["lane_split"] is True
        assert reward["reward"] == 0.0  # lanes are diagnosed, never averaged
        assert (logs / "artifacts" / "antitrust-risk-memo.docx").read_bytes() == b"fixture deliverable"

        # A symlink with the expected filename is not a deliverable and cannot
        # be used to smuggle an input/system file into the artifact lane.
        (output / "antitrust-risk-memo.docx").unlink()
        (output / "outside.docx").write_bytes(b"outside")
        (output / "antitrust-risk-memo.docx").symlink_to(output / "outside.docx")
        subprocess.run(["bash", str(script)], env=environment, check=True,
                       capture_output=True, text=True)
        symlink_lane = json.loads((logs / "verifier" / "file-lane.json").read_text())
        assert symlink_lane["file_passed"] is False
        assert any(row["reason"] == "symlink" for row in symlink_lane["rejected_artifacts"])

        unsafe = {**task, "task_id": "unsafe", "file_lane": {
            **task["file_lane"], "deliverables": ["../escape.docx"]}}
        try:
            generator.test_sh(unsafe)
            raise AssertionError("unsafe output path was accepted")
        except RuntimeError as error:
            assert "unsafe deliverable path" in str(error)

        grounded = {
            **task,
            "task_id": "lab_file_lane_grounded",
            "file_lane": {
                **task["file_lane"],
                "deliverables": ["grounded.md"],
                "grading": "determinate",
                "assertions": [{
                    "criterion_id": "C-001",
                    "deliverables": ["grounded.md"],
                    "anchor_groups": [["$54M", "$54 million"], ["Section 7.2(b)"]],
                }],
            },
        }
        oracle_outputs = generator.oracle_file_outputs(grounded)
        assert oracle_outputs == {"grounded.md": "$54M | Section 7.2(b)"}
        oracle_script = generator.solve_sh("fixture-token", grounded)
        assert "from docx import Document" in oracle_script
        assert "from openpyxl import Workbook" in oracle_script
        assert "from pptx import Presentation" in oracle_script
        assert "/workspace/output" in oracle_script
        grounded_script = base / "grounded-test.sh"
        grounded_script.write_text(generator.test_sh(grounded))
        grounded_script.chmod(0o755)
        (output / "antitrust-risk-memo.docx").unlink()
        (output / "grounded.md").write_text("Approved amount: $54M under Section 7.2(b).")
        subprocess.run(["bash", str(grounded_script)], env=environment, check=True,
                       capture_output=True, text=True)
        grounded_lane = json.loads((logs / "verifier" / "file-lane.json").read_text())
        assert grounded_lane["grade_kind"] == "determinate" and grounded_lane["file_passed"] is True
        (output / "grounded.md").write_text("Approved amount: $53M under Section 7.2(b).")
        subprocess.run(["bash", str(grounded_script)], env=environment, check=True,
                       capture_output=True, text=True)
        wrong_lane = json.loads((logs / "verifier" / "file-lane.json").read_text())
        assert wrong_lane["file_contract_passed"] is True and wrong_lane["file_content_passed"] is False
        assert wrong_lane["file_passed"] is False
        (output / "grounded.md").write_text("Approved amount: $54MM under Section 7.2(b).")
        subprocess.run(["bash", str(grounded_script)], env=environment, check=True,
                       capture_output=True, text=True)
        collision_lane = json.loads((logs / "verifier" / "file-lane.json").read_text())
        assert collision_lane["file_content_passed"] is False

        def normalized(value: str) -> str:
            value = unicodedata.normalize("NFKC", value).casefold()
            value = value.replace("\u00a0", " ").replace("–", "-").replace("—", "-")
            return " ".join(value.split())

        state_body = "Approved amount: $54M under Section 7.2(b)."
        state_digest = hashlib.sha256(normalized(state_body).encode()).hexdigest()

        class VerifyHandler(http.server.BaseHTTPRequestHandler):
            digest = state_digest
            def do_POST(self):  # noqa: N802
                payload = json.dumps({"passed": True, "reward": 1.0,
                                      "filed_text_sha256": {"grounded.md": self.digest}}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
            def log_message(self, *_):
                return

        server = http.server.HTTPServer(("127.0.0.1", 0), VerifyHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            (output / "grounded.md").write_text(state_body)
            live_environment = {**environment,
                                "WORLD_VERIFY_URL": f"http://127.0.0.1:{server.server_port}/verify"}
            subprocess.run(["bash", str(grounded_script)], env=live_environment, check=True,
                           capture_output=True, text=True)
            consistent = json.loads((logs / "verifier" / "file-lane.json").read_text())
            assert consistent["file_passed"] and consistent["state_passed"]
            assert consistent["cross_lane_match"] is True
            VerifyHandler.digest = hashlib.sha256(b"different filed body").hexdigest()
            subprocess.run(["bash", str(grounded_script)], env=live_environment, check=True,
                           capture_output=True, text=True)
            divergent = json.loads((logs / "verifier" / "file-lane.json").read_text())
            assert divergent["cross_lane_match"] is False
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

        cross_file = {
            **grounded,
            "task_id": "lab_file_lane_cross_file",
            "file_lane": {
                **grounded["file_lane"],
                "deliverables": ["grounded.md", "annex.md"],
                "assertions": [{
                    "criterion_id": "C-002",
                    "deliverables": ["grounded.md", "annex.md"],
                    "anchor_groups": [["source-grounded finding"]],
                }],
            },
        }
        cross_script = base / "cross-test.sh"
        cross_script.write_text(generator.test_sh(cross_file))
        cross_script.chmod(0o755)
        (output / "grounded.md").write_text("See the annex.")
        (output / "annex.md").write_text("Source-grounded finding.")
        subprocess.run(["bash", str(cross_script)], env=environment, check=True,
                       capture_output=True, text=True)
        cross_lane = json.loads((logs / "verifier" / "file-lane.json").read_text())
        assert cross_lane["file_content_passed"] is True

        live_task = (ROOT / "research" / "repos" / "harveyai@harvey-labs" / "tasks" /
                     "antitrust-competition" / "analyze-antitrust-hsr-strategy")
        if (live_task / "task.json").is_file():
            live_source = json.loads((live_task / "task.json").read_text())
            live = {
                "task_id": "lab_file_lane_live_gate",
                "prompt": live_source["instructions"],
                "file_lane": {
                    "source_task": "antitrust-competition/analyze-antitrust-hsr-strategy",
                    "source_commit": commit,
                    "documents_source": str(live_task / "documents"),
                    "deliverables": list(live_source["deliverables"]),
                    "skills": ["docx", "xlsx", "pptx"],
                },
            }
            live_dir = base / "live-task"
            generator.stage_file_lane(live, str(live_dir))
            live_documents = [path for path in (live_dir / "environment" / "documents").rglob("*")
                              if path.is_file()]
            assert len(live_documents) == 9
            live_checked = True

        image_context = Path(generator.assemble_world_image(
            str(base / "world-build"), str(ROOT / "world" / "blobfish" / "world-v16.json")))
        required_runtime = {
            "server.py", "oracle.py", "v2runtime.py", "v3dialects.py", "evidence.py",
            "paging.py", "wire_errors.py", "product_workflows.py", "query_dsl.py",
        }
        assert required_runtime <= {path.name for path in image_context.iterdir() if path.is_file()}
        world_dockerfile = (image_context / "Dockerfile").read_text()
        assert "ORACLE_PROOF_SHA256" in world_dockerfile
        assert 'ARG SOLVE_TOKEN=""' not in world_dockerfile
        shim_source = (image_context / "shim.py").read_text()
        assert "hmac.compare_digest" in shim_source and "supplied_hash" in shim_source

    print("Harbor file lane: 9 source docs staged read-only, LAB skills present, "
          f"artifact/state lanes stay separate (live_source={str(live_checked).lower()})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
