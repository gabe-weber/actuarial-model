"""Build the run manifest dict."""

from __future__ import annotations

import hashlib
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _git_commit() -> str | None:
    """Return current HEAD commit hash, or None if unavailable."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def sha256_file(path: Path) -> str:
    """Hex SHA-256 of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    """Hex SHA-256 of a UTF-8 string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_manifest(
    *,
    run_id: str,
    start_time: datetime,
    end_time: datetime,
    status: str,
    input_path: Path,
    assumptions_path: Path,
    assumptions: dict[str, Any],
    output_dir: Path,
    output_files: list[Path],
    warnings: list[str],
    cli_args: list[str],
) -> dict[str, Any]:
    """Assemble and return the run manifest as a dict."""
    commit = _git_commit()

    requirements_path = Path(__file__).parent.parent / "requirements.txt"
    req_hash: str | None = None
    if requirements_path.exists():
        req_hash = sha256_file(requirements_path)

    output_hashes = {
        f.name: sha256_file(f) for f in output_files if f.exists()
    }

    exclusions = [
        "No mortality decrement",
        "No turnover decrement",
        "No retirement decrement",
        "No annuity factor (payment timing not modeled)",
        "No vesting schedule",
        "No plan limits (IRC 415/401(a)(17))",
        "No taxes",
        "Benefit basis: current service only (not projected service under benefit_service_basis variants)",
    ]

    return {
        "run_id": run_id,
        "start_time_utc": start_time.isoformat(),
        "end_time_utc": end_time.isoformat(),
        "status": status,
        "cli_args": cli_args,
        "git_commit": commit,
        "git_commit_warning": None if commit else "Git commit unavailable; not a git repository or git not found.",
        "python_version": sys.version,
        "platform": platform.platform(),
        "requirements_txt_sha256": req_hash,
        "input_file": str(input_path.resolve()),
        "input_file_sha256": sha256_file(input_path),
        "assumptions_file": str(assumptions_path.resolve()),
        "assumptions_file_sha256": sha256_file(assumptions_path),
        "resolved_assumptions": assumptions,
        "output_dir": str(output_dir.resolve()),
        "output_file_sha256": output_hashes,
        "warnings": warnings,
        "model_exclusions": exclusions,
    }
