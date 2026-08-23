#!/usr/bin/env python3
"""Fail unless immutable GHCR image references are anonymously readable."""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import urllib.parse
from collections.abc import Callable
from typing import Any


REFERENCE = re.compile(
    r"^ghcr\.io/(?P<repository>"
    r"[a-z0-9]+(?:[._-]+[a-z0-9]+)*"
    r"(?:/[a-z0-9]+(?:[._-]+[a-z0-9]+)*)+"
    r")@"
    r"(?P<digest>sha256:[0-9a-f]{64})$"
)
ACCEPT = ", ".join(
    (
        "application/vnd.oci.image.manifest.v1+json",
        "application/vnd.docker.distribution.manifest.v2+json",
        "application/vnd.oci.image.index.v1+json",
        "application/vnd.docker.distribution.manifest.list.v2+json",
    )
)
MAX_TOKEN_RESPONSE = 128 * 1024


def parse_reference(image: str) -> tuple[str, str]:
    match = REFERENCE.fullmatch(image.strip())
    if not match:
        raise ValueError(
            "image must be ghcr.io/<lowercase repository>@sha256:<64 lowercase hex>"
        )
    return match.group("repository"), match.group("digest")


def anonymous_manifest_digest(
    image: str,
    runner: Callable[..., Any] = subprocess.run,
    curl_path: str | None = None,
) -> str:
    repository, expected = parse_reference(image)
    curl = curl_path or shutil.which("curl")
    if not curl:
        raise RuntimeError("curl is required for the anonymous GHCR check")
    token_query = urllib.parse.urlencode(
        {"service": "ghcr.io", "scope": f"repository:{repository}:pull"}
    )
    token_marker = "GHCR_TOKEN_HTTP_STATUS:"
    token_result = runner(
        [
            curl,
            "--silent",
            "--show-error",
            "--max-time",
            "30",
            "--max-filesize",
            str(MAX_TOKEN_RESPONSE),
            "--header",
            "Accept: application/json",
            "--write-out",
            f"\n{token_marker}%{{http_code}}\n",
            f"https://ghcr.io/token?{token_query}",
        ],
        text=True,
        capture_output=True,
    )
    if token_result.returncode:
        raise RuntimeError(f"anonymous GHCR token request failed for {repository}")
    token_status_match = re.search(
        rf"\n{token_marker}([0-9]{{3}})\s*$", token_result.stdout
    )
    token_status = token_status_match.group(1) if token_status_match else "000"
    if token_status != "200":
        raise RuntimeError(
            f"anonymous GHCR token request failed with HTTP {token_status} "
            f"for {repository}"
        )
    payload = token_result.stdout[: token_status_match.start()]
    if len(payload) > MAX_TOKEN_RESPONSE:
        raise RuntimeError("anonymous GHCR token response exceeded the size limit")
    try:
        token_payload = json.loads(payload)
    except json.JSONDecodeError as error:
        raise RuntimeError("GHCR returned an invalid anonymous token response") from error
    token = token_payload.get("token") if isinstance(token_payload, dict) else None
    if not isinstance(token, str) or not token:
        raise RuntimeError("GHCR did not issue an anonymous pull token")

    marker = "GHCR_HTTP_STATUS:"
    manifest_result = runner(
        [
            curl,
            "--silent",
            "--show-error",
            "--head",
            "--max-time",
            "30",
            "--header",
            f"Authorization: Bearer {token}",
            "--header",
            f"Accept: {ACCEPT}",
            "--write-out",
            f"\n{marker}%{{http_code}}\n",
            f"https://ghcr.io/v2/{repository}/manifests/{expected}",
        ],
        text=True,
        capture_output=True,
    )
    if manifest_result.returncode:
        raise RuntimeError(f"anonymous GHCR request failed for {repository}")
    status_match = re.search(rf"\n{marker}([0-9]{{3}})\s*$", manifest_result.stdout)
    status = status_match.group(1) if status_match else "000"
    if status != "200":
        raise RuntimeError(
            f"anonymous GHCR pull failed with HTTP {status} for {repository}"
        )
    digest_headers = re.findall(
        r"^docker-content-digest:\s*(\S+)\s*$",
        manifest_result.stdout,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    actual = digest_headers[-1].rstrip("\r") if digest_headers else ""

    if actual != expected:
        raise RuntimeError(
            f"anonymous GHCR digest mismatch for {repository}: {actual or '<missing>'}"
        )
    return actual


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("images", nargs="+")
    args = parser.parse_args()
    try:
        for image in args.images:
            digest = anonymous_manifest_digest(image)
            repository, _ = parse_reference(image)
            print(f"public GHCR manifest: {repository}@{digest}")
    except (RuntimeError, ValueError) as error:
        print(f"GHCR public check failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
