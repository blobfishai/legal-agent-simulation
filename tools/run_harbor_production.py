#!/usr/bin/env python3
"""Generate or check the full Harbor export using immutable production images."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORLD_REPOSITORY = "ghcr.io/blobfishai/legal-agent-sim-world"
LAB_REPOSITORY = "ghcr.io/blobfishai/legal-agent-sim-agent-lab"
DIGEST_REFERENCE = re.compile(r"^(?P<repository>[^@]+)@sha256:[0-9a-f]{64}$")
DATASET_DESCRIPTION = (
    "23,310 deterministic legal-agent simulation tasks with Harbor-isolated "
    "MCP worlds, Harvey-derived file lanes, and v21 seeded documents."
)
ORACLE_PROOF_REPORT = ROOT / "reports" / "v21-oracle-proof-audit.json"


class ImageInspectionUnavailable(RuntimeError):
    """The immutable remote image could not be read by the local Docker client."""


class OracleProofMismatch(RuntimeError):
    """A readable image carried a proof hash for a different export token."""

    def __init__(self, expected: str, actual: str) -> None:
        super().__init__(
            "full export solve token does not match the production world image proof"
        )
        self.expected = expected
        self.actual = actual


def immutable_reference(value: str, repository: str, label: str) -> str:
    match = DIGEST_REFERENCE.fullmatch(value.strip())
    if not match or match.group("repository") != repository:
        raise ValueError(
            f"{label} must be {repository}@sha256:<64 lowercase hex characters>"
        )
    return value.strip()


def locked_harbor_command(*arguments: str) -> list[str]:
    uv = shutil.which("uv")
    if not uv:
        raise RuntimeError("uv is required to materialize the locked Harbor runner")
    return [
        uv,
        "run",
        "--project", str(ROOT / "harbor" / "runner"),
        "--locked",
        *arguments,
    ]


def proof_from_environment(values: list[str]) -> str:
    prefix = "ORACLE_PROOF_SHA256="
    matches = [value.removeprefix(prefix) for value in values if value.startswith(prefix)]
    if len(matches) != 1 or not re.fullmatch(r"[0-9a-f]{64}", matches[0]):
        raise RuntimeError("production world image has no unique oracle proof hash")
    return matches[0]


def image_environment(image: str) -> list[str]:
    docker = shutil.which("docker")
    if not docker:
        raise RuntimeError("docker buildx is required to verify the production image proof")

    def inspect(reference: str) -> list[str] | None:
        try:
            result = subprocess.run(
                [docker, "buildx", "imagetools", "inspect", reference,
                 "--format", "{{json .Image.Config.Env}}"],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=True,
            )
        except subprocess.CalledProcessError as error:
            raise ImageInspectionUnavailable(
                f"cannot inspect immutable production image {reference}"
            ) from error
        value = json.loads(result.stdout)
        return value if isinstance(value, list) else None

    environment = inspect(image)
    if environment is not None:
        return [str(value) for value in environment]

    try:
        raw = subprocess.run(
            [docker, "buildx", "imagetools", "inspect", image, "--raw"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError as error:
        raise ImageInspectionUnavailable(
            f"cannot inspect immutable production image {image}"
        ) from error
    manifest = json.loads(raw.stdout)
    candidates = [
        row for row in manifest.get("manifests") or []
        if (row.get("platform") or {}).get("os") == "linux"
        and (row.get("platform") or {}).get("architecture") == "amd64"
    ]
    if len(candidates) != 1 or not DIGEST_REFERENCE.fullmatch(
        image.split("@", 1)[0] + "@" + str(candidates[0].get("digest") or "")
    ):
        raise RuntimeError("production world image lacks one linux/amd64 manifest")
    platform_image = image.split("@", 1)[0] + "@" + str(candidates[0]["digest"])
    environment = inspect(platform_image)
    if environment is None:
        raise RuntimeError("production world image config is unavailable")
    return [str(value) for value in environment]


def verify_oracle_proof(world_image: str, output: Path) -> str:
    token_path = output / "world-image" / "solve-token.txt"
    token = token_path.read_text("utf-8").strip()
    expected = hashlib.sha256(token.encode()).hexdigest()
    actual = proof_from_environment(image_environment(world_image))
    if actual != expected:
        raise OracleProofMismatch(expected, actual)
    print(f"production oracle proof matched: sha256:{expected}")
    return actual


def write_oracle_proof_report(
    world_image: str,
    output: Path,
    *,
    image_proof_sha256: str | None,
    failure_class: str | None,
    error: str | None,
) -> None:
    token = (output / "world-image" / "solve-token.txt").read_text("utf-8").strip()
    expected = hashlib.sha256(token.encode()).hexdigest()
    if image_proof_sha256 is not None and not re.fullmatch(
        r"[0-9a-f]{64}", image_proof_sha256
    ):
        raise RuntimeError("image oracle proof has an invalid format")
    matched = image_proof_sha256 == expected
    if matched:
        failure_class = None
        error = None
    elif image_proof_sha256 is not None:
        failure_class = "oracle_integrity_failure"
        error = error or "production image proof does not match the export token"
    elif failure_class not in {
        "remote_image_inspection_unavailable",
        "oracle_integrity_failure",
    } or not error:
        raise RuntimeError("failed oracle proof reports require a classified error")
    report = {
        "schema_version": 2,
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "world_image": world_image,
        "export_solve_token_sha256": expected,
        "image_oracle_proof_sha256": image_proof_sha256,
        "matched": matched,
        "failure_class": failure_class,
        "error": error,
    }
    ORACLE_PROOF_REPORT.parent.mkdir(parents=True, exist_ok=True)
    ORACLE_PROOF_REPORT.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", "utf-8"
    )


def audit_oracle_proof(world_image: str, output: Path) -> bool:
    proof_error = None
    proof_failure_class = None
    image_proof_sha256 = None
    try:
        image_proof_sha256 = verify_oracle_proof(world_image, output)
    except ImageInspectionUnavailable as error:
        proof_failure_class = "remote_image_inspection_unavailable"
        proof_error = str(error)
        print(f"production oracle proof check failed: {proof_error}", file=sys.stderr)
    except OracleProofMismatch as error:
        image_proof_sha256 = error.actual
        proof_failure_class = "oracle_integrity_failure"
        proof_error = str(error)
        print(f"production oracle proof check failed: {proof_error}", file=sys.stderr)
    except (OSError, RuntimeError, json.JSONDecodeError) as error:
        # A readable image with missing/mismatched proof metadata is an
        # integrity failure. Registry privacy must never excuse it.
        proof_failure_class = "oracle_integrity_failure"
        proof_error = str(error)
        print(f"production oracle proof check failed: {proof_error}", file=sys.stderr)
    write_oracle_proof_report(
        world_image,
        output,
        image_proof_sha256=image_proof_sha256,
        failure_class=proof_failure_class,
        error=proof_error,
    )
    return proof_error is None


def rebuild_dataset(output: Path) -> None:
    dataset = output / "dataset"
    if dataset.is_symlink():
        raise RuntimeError(f"refusing symlinked dataset path: {dataset}")
    if dataset.exists():
        if not (dataset / "dataset.toml").is_file():
            raise RuntimeError(f"refusing to replace non-dataset directory: {dataset}")
        shutil.rmtree(dataset)
    subprocess.run(
        locked_harbor_command(
            "harbor", "init", "legal-agent-simulation/v21", "--dataset",
            "--output-dir", str(dataset), "--description", DATASET_DESCRIPTION,
        ),
        cwd=ROOT,
        check=True,
    )
    added = subprocess.run(
        locked_harbor_command(
            "harbor", "add", str(output / "tasks"), "--scan", "--to", str(dataset)
        ),
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    if added.returncode:
        sys.stderr.write(added.stdout)
        sys.stderr.write(added.stderr)
        added.check_returncode()
    print(f"dataset manifest rebuilt from {output / 'tasks'}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("generate", "check"))
    parser.add_argument("--out", type=Path, default=ROOT / "dist" / "harbor-v21-prod")
    parser.add_argument("--world-image", default=os.environ.get("V21_WORLD_IMAGE", ""))
    parser.add_argument("--lab-image", default=os.environ.get("V21_LAB_IMAGE", ""))
    args = parser.parse_args()

    try:
        world_image = immutable_reference(args.world_image, WORLD_REPOSITORY, "world image")
        lab_image = immutable_reference(args.lab_image, LAB_REPOSITORY, "LAB image")
    except ValueError as error:
        parser.error(str(error))

    if args.out.is_symlink():
        parser.error(f"--out may not be a symlink: {args.out}")
    output = args.out.resolve()
    allowed_root = (ROOT / "dist").resolve()
    if output == allowed_root or allowed_root not in output.parents:
        parser.error(f"--out must be a child of {allowed_root}")
    if args.action == "generate":
        command = [
            sys.executable,
            str(ROOT / "harbor" / "generate.py"),
            "--world", str(ROOT / "world" / "blobfish" / "world-v21.json"),
            "--contracts", str(ROOT / "mcp" / "v5" / "contracts"),
            "--out", str(output),
            "--image-tag", world_image,
            "--lab-agent-image", lab_image,
        ]
    else:
        command = [
            sys.executable,
            str(ROOT / "tools" / "check_harbor_export.py"),
            "--root", str(output),
            "--world", str(ROOT / "world" / "blobfish" / "world-v21.json"),
            "--expected-tasks", "23310",
            "--world-image", world_image,
            "--lab-image", lab_image,
            "--require-all-world-tasks",
            "--verify-evidence",
            "--report", str(ROOT / "reports" / "v21-harbor-export-audit.json"),
        ]
    subprocess.run(command, cwd=ROOT, check=True)
    if args.action == "generate":
        rebuild_dataset(output)
    else:
        subprocess.run(
            locked_harbor_command(
                "python", str(ROOT / "tools" / "check_harbor_dataset.py"),
                "--root", str(output), "--expected-tasks", "23310",
                "--report", str(ROOT / "reports" / "v21-harbor-dataset-audit.json"),
            ),
            cwd=ROOT,
            check=True,
        )
        # Registry visibility and remote image metadata are external
        # publication state. Evaluate both only after structural and dataset
        # evidence exists, then aggregate their failures.
        visibility = subprocess.run(
            [
                sys.executable,
                str(ROOT / "tools" / "check_ghcr_public.py"),
                "--report", str(ROOT / "reports" / "v21-ghcr-public-audit.json"),
                world_image,
                lab_image,
            ],
            cwd=ROOT,
        )
        proof_matched = audit_oracle_proof(world_image, output)
        if visibility.returncode or not proof_matched:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
