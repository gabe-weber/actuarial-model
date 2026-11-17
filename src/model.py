"""Pure calculation functions and CLI entry point for the pension model."""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.io import (
    load_assumptions,
    load_employees,
    sha256_file,
    write_employee_results,
    write_manifest,
    write_summary,
)
from src.manifest import build_manifest

# ---------------------------------------------------------------------------
# Pure calculation functions
# ---------------------------------------------------------------------------


def years_to_retirement(age: int, retirement_age: int) -> int:
    """Return years until retirement; zero if already at or past retirement age.

    Args:
        age: Current age of the employee.
        retirement_age: Plan retirement age from assumptions.

    Returns:
        Non-negative integer number of years to retirement.
    """
    return max(retirement_age - age, 0)


def projected_salary(
    salary: float,
    salary_growth_rate: float,
    ytr: int,
) -> float:
    """Project salary to retirement date using compound growth.

    Args:
        salary: Current annual salary.
        salary_growth_rate: Annual salary growth rate (e.g. 0.040).
        ytr: Years to retirement (from :func:`years_to_retirement`).

    Returns:
        Projected salary at retirement.
    """
    return salary * (1 + salary_growth_rate) ** ytr


def projected_service(service: float, ytr: int) -> float:
    """Project service to retirement date.

    Args:
        service: Current years of service.
        ytr: Years to retirement.

    Returns:
        Projected years of service at retirement.
    """
    return service + ytr


def annual_benefit(
    benefit_multiplier: float,
    proj_service: float,
    proj_salary: float,
) -> float:
    """Calculate the projected annual pension benefit.

    Formula: multiplier × projected_service × projected_salary.

    Args:
        benefit_multiplier: Per-year-of-service benefit rate (e.g. 0.015).
        proj_service: Projected service at retirement.
        proj_salary: Projected salary at retirement.

    Returns:
        Annual pension benefit amount.
    """
    return benefit_multiplier * proj_service * proj_salary


def present_value(benefit: float, discount_rate: float, ytr: int) -> float:
    """Discount the annual benefit to a present value.

    Args:
        benefit: Annual pension benefit.
        discount_rate: Annual discount rate (e.g. 0.05).
        ytr: Years to retirement used as discount period.

    Returns:
        Present value of the benefit. Returns the benefit unchanged when ytr is 0.
    """
    if ytr == 0:
        return benefit
    return benefit / (1 + discount_rate) ** ytr


# ---------------------------------------------------------------------------
# Per-employee calculation
# ---------------------------------------------------------------------------


def calculate_employee(
    employee: dict[str, Any], assumptions: dict[str, Any]
) -> dict[str, Any]:
    """Run all formulas for a single employee and return a result dict.

    Args:
        employee: Validated employee record (id, age, salary, service).
        assumptions: Resolved assumption values.

    Returns:
        Dict containing input fields plus all computed output fields.
    """
    ret_age: int = assumptions["retirement_age"]
    growth: float = assumptions["salary_growth_rate"]
    disc: float = assumptions["discount_rate"]
    mult: float = assumptions["benefit_multiplier"]
    decimals: int = assumptions["rounding_decimals"]

    age: int = employee["age"]
    sal: float = employee["salary"]
    svc: float = employee["service"]

    ytr = years_to_retirement(age, ret_age)
    proj_sal = projected_salary(sal, growth, ytr)
    proj_svc = projected_service(svc, ytr)
    ann_ben = annual_benefit(mult, proj_svc, proj_sal)
    pv = present_value(ann_ben, disc, ytr)

    return {
        "employee_id": employee["employee_id"],
        "age": age,
        "salary": round(sal, decimals),
        "service": svc,
        "years_to_retirement": ytr,
        "projected_salary": round(proj_sal, decimals),
        "projected_service": round(proj_svc, decimals),
        "annual_benefit": round(ann_ben, decimals),
        "present_value": round(pv, decimals),
        # keep unrounded PV for summation before final display rounding
        "_pv_unrounded": pv,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _setup_logging(log_path: Path) -> tuple[logging.FileHandler, logging.StreamHandler]:
    """Configure logging and return the handlers so they can be closed explicitly."""
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setFormatter(fmt)
    root.addHandler(fh)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    root.addHandler(sh)
    return fh, sh


def _teardown_logging(fh: logging.FileHandler, sh: logging.StreamHandler) -> None:
    """Flush, close, and remove log handlers (required on Windows before temp-dir cleanup)."""
    root = logging.getLogger()
    for handler in (fh, sh):
        try:
            handler.flush()
            handler.close()
            root.removeHandler(handler)
        except Exception:
            pass


def main(argv: list[str] | None = None) -> int:
    """Entry point. Returns exit code (0 = success, non-zero = failure)."""
    parser = argparse.ArgumentParser(
        description="Simple pension projection model."
    )
    parser.add_argument("--input", required=True, help="Path to employees CSV.")
    parser.add_argument(
        "--assumptions", required=True, help="Path to assumptions YAML."
    )
    parser.add_argument("--output-dir", required=True, help="Directory for outputs.")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow overwriting an existing output directory.",
    )
    args = parser.parse_args(argv)

    input_path = Path(args.input).resolve()
    assumptions_path = Path(args.assumptions).resolve()
    output_dir = Path(args.output_dir).resolve()

    # Guard against silent overwrite
    if output_dir.exists() and any(output_dir.iterdir()):
        if not args.overwrite:
            print(
                f"ERROR: Output directory '{output_dir}' already contains files. "
                "Use --overwrite to allow replacement.",
                file=sys.stderr,
            )
            return 1
        shutil.rmtree(output_dir)

    run_id = str(uuid.uuid4())
    start_time = datetime.now(timezone.utc)

    # Stage outputs in a temp directory; promote only on full success.
    # We manage the temp dir manually to close the log file handler before
    # cleanup (Windows holds an exclusive lock on open files).
    tmp_dir = tempfile.mkdtemp()
    tmp = Path(tmp_dir)
    log_path = tmp / "run.log"
    fh, sh = _setup_logging(log_path)
    logger = logging.getLogger(__name__)
    logger.info("Run %s started.", run_id)

    warnings: list[str] = []
    cli_args = sys.argv[1:] if argv is None else list(argv)

    try:
        try:
            assumptions = load_assumptions(assumptions_path)
            employees = load_employees(input_path)
        except (FileNotFoundError, ValueError) as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            logger.error("Startup error: %s", exc)
            _teardown_logging(fh, sh)
            shutil.rmtree(tmp_dir, ignore_errors=True)
            return 1

        results = [calculate_employee(emp, assumptions) for emp in employees]

        # Strip internal key before writing
        output_rows = [
            {k: v for k, v in r.items() if not k.startswith("_")}
            for r in results
        ]

        total_liability_unrounded = sum(r["_pv_unrounded"] for r in results)
        total_liability = round(
            total_liability_unrounded, assumptions["rounding_decimals"]
        )

        results_path = tmp / "employee_results.csv"
        summary_path = tmp / "summary.json"
        manifest_path = tmp / "run_manifest.json"

        write_employee_results(results_path, output_rows)

        input_hash = sha256_file(input_path)
        assumptions_hash = sha256_file(assumptions_path)

        summary = {
            "run_id": run_id,
            "employee_count": len(results),
            "total_liability": total_liability,
            "assumptions_file_hash": assumptions_hash,
            "input_file_hash": input_hash,
        }
        write_summary(summary_path, summary)

        end_time = datetime.now(timezone.utc)

        manifest = build_manifest(
            run_id=run_id,
            start_time=start_time,
            end_time=end_time,
            status="success",
            input_path=input_path,
            assumptions_path=assumptions_path,
            assumptions=assumptions,
            output_dir=output_dir,
            output_files=[results_path, summary_path, manifest_path],
            warnings=warnings,
            cli_args=cli_args,
        )
        write_manifest(manifest_path, manifest)

        # Close log handler before copying (Windows lock) then promote
        _teardown_logging(fh, sh)
        output_dir.mkdir(parents=True, exist_ok=True)
        for src in [results_path, summary_path, manifest_path, log_path]:
            shutil.copy2(src, output_dir / src.name)

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    logger_final = logging.getLogger(__name__)
    logger_final.info(
        "Run %s complete. %d employee(s), total liability %.2f.",
        run_id,
        len(results),
        total_liability,
    )
    print(
        f"Run complete. {len(results)} employee(s), "
        f"total liability {total_liability:,.2f}. "
        f"Outputs in: {output_dir}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
