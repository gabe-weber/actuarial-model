"""Input/output helpers: reading, validating, and writing files."""

from __future__ import annotations

import csv
import hashlib
import json
import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = {"employee_id", "age", "salary", "service"}


def sha256_file(path: Path) -> str:
    """Return the hex SHA-256 digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_assumptions(path: Path) -> dict[str, Any]:
    """Load and return the assumptions YAML as a dict.

    Raises:
        FileNotFoundError: if the file does not exist.
        ValueError: if the expected structure is missing.
    """
    if not path.exists():
        raise FileNotFoundError(f"Assumptions file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    if not isinstance(raw, dict) or "valuation" not in raw:
        raise ValueError(
            f"Assumptions file must contain a 'valuation' mapping: {path}"
        )
    return raw["valuation"]


def load_employees(path: Path) -> list[dict[str, Any]]:
    """Read and validate employee CSV; return list of row dicts.

    Raises:
        FileNotFoundError: if the file does not exist.
        ValueError: on any validation failure (missing columns, bad values, etc.).
    """
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        raise ValueError("Input file is empty or has no data rows.")

    # Column presence check
    actual_columns = set(rows[0].keys())
    missing = REQUIRED_COLUMNS - actual_columns
    if missing:
        raise ValueError(f"Input file is missing required column(s): {sorted(missing)}")

    seen_ids: set[str] = set()
    cleaned: list[dict[str, Any]] = []

    for i, row in enumerate(rows, start=2):  # row 1 is header
        eid = row["employee_id"].strip()
        if not eid:
            raise ValueError(f"Row {i}: employee_id is blank.")
        if eid in seen_ids:
            raise ValueError(f"Row {i}: duplicate employee_id '{eid}'.")
        seen_ids.add(eid)

        # age
        try:
            age = int(row["age"])
        except (ValueError, TypeError):
            raise ValueError(
                f"Row {i} (id={eid}): age must be an integer, got '{row['age']}'."
            )
        if not (18 <= age <= 80):
            raise ValueError(
                f"Row {i} (id={eid}): age {age} is outside the allowed range 18–80."
            )

        # salary
        try:
            salary = float(row["salary"])
        except (ValueError, TypeError):
            raise ValueError(
                f"Row {i} (id={eid}): salary must be numeric, got '{row['salary']}'."
            )
        if salary <= 0:
            raise ValueError(
                f"Row {i} (id={eid}): salary must be greater than 0, got {salary}."
            )

        # service
        try:
            service = float(row["service"])
        except (ValueError, TypeError):
            raise ValueError(
                f"Row {i} (id={eid}): service must be numeric, got '{row['service']}'."
            )
        if service < 0:
            raise ValueError(
                f"Row {i} (id={eid}): service cannot be negative, got {service}."
            )
        max_service = age - 14
        if service > max_service:
            raise ValueError(
                f"Row {i} (id={eid}): service {service} exceeds age-minus-14 "
                f"limit of {max_service}."
            )

        cleaned.append(
            {
                "employee_id": eid,
                "age": age,
                "salary": salary,
                "service": service,
            }
        )

    logger.info("Loaded %d employee record(s) from %s.", len(cleaned), path)
    return cleaned


def write_employee_results(path: Path, results: list[dict[str, Any]]) -> None:
    """Write employee-level results to a CSV file."""
    fieldnames = [
        "employee_id",
        "age",
        "salary",
        "service",
        "years_to_retirement",
        "projected_salary",
        "projected_service",
        "annual_benefit",
        "present_value",
    ]
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    logger.info("Wrote %d result row(s) to %s.", len(results), path)


def write_summary(path: Path, summary: dict[str, Any]) -> None:
    """Write summary JSON."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    logger.info("Wrote summary to %s.", path)


def write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    """Write run manifest JSON."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, default=str)
    logger.info("Wrote manifest to %s.", path)
