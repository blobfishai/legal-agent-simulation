#!/usr/bin/env python3
"""Run the v21 rendering gate locally or inside the locked LAB image."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "tools" / "check_v21_document_rendering.py"
DEFAULT_IMAGE = "legal-agent-sim-agent-lab:render-audit"


def local_renderer_available() -> bool:
    return bool(
        shutil.which("soffice")
        or shutil.which("libreoffice")
        or Path("/Applications/LibreOffice.app/Contents/MacOS/soffice").is_file()
        or Path("/usr/bin/libreoffice").is_file()
    )


def docker_image_available(docker: str, image: str) -> bool:
    result = subprocess.run(
        [docker, "image", "inspect", image],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def main() -> int:
    arguments = sys.argv[1:]
    if local_renderer_available() or "--help" in arguments or "-h" in arguments:
        return subprocess.run([sys.executable, str(CHECKER), *arguments], cwd=ROOT).returncode

    docker = shutil.which("docker")
    image = os.environ.get("V21_RENDER_IMAGE", DEFAULT_IMAGE).strip()
    if not docker or not image or not docker_image_available(docker, image):
        print(
            "v21 document rendering requires LibreOffice on the host or a local "
            f"{image or DEFAULT_IMAGE!r} LAB image; set V21_RENDER_IMAGE to an "
            "equivalent locked image",
            file=sys.stderr,
        )
        return 2

    command = [
        docker,
        "run",
        "--rm",
        "--network", "none",
        "--volume", f"{ROOT}:/repo",
        "--workdir", "/repo",
        image,
        "python",
        "/repo/tools/check_v21_document_rendering.py",
        *arguments,
    ]
    print(f"host LibreOffice unavailable; using locked renderer image {image}", file=sys.stderr)
    return subprocess.run(command, cwd=ROOT).returncode


if __name__ == "__main__":
    raise SystemExit(main())
