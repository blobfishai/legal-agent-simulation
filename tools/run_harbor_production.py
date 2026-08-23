#!/usr/bin/env python3
"""Generate or check the full Harbor export using immutable production images."""
from __future__ import annotations

import argparse
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
        ]
    subprocess.run(command, cwd=ROOT, check=True)
    if args.action == "generate":
        rebuild_dataset(output)
    else:
        subprocess.run(
            locked_harbor_command(
                "python", str(ROOT / "tools" / "check_harbor_dataset.py"),
                "--root", str(output), "--expected-tasks", "23310",
            ),
            cwd=ROOT,
            check=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
