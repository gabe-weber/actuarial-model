"""End-to-end tests for the pension model CLI."""

import csv
import json
import shutil
from pathlib import Path

import pytest

from src.model import main

SAMPLE_DATA = """\
employee_id,age,salary,service
E001,40,80000,15
E002,55,120000,25
E003,65,90000,38
"""

ASSUMPTIONS_YAML = """\
valuation:
  valuation_year: 2026
  retirement_age: 65
  salary_growth_rate_pre40: 0.045
  salary_growth_rate_post40: 0.025
  discount_rate: 0.05
  benefit_multiplier: 0.015
  benefit_service_basis: current_service
  rounding_decimals: 2
"""


@pytest.fixture()
def sample_input(tmp_path: Path) -> Path:
    p = tmp_path / "employees.csv"
    p.write_text(SAMPLE_DATA, encoding="utf-8")
    return p


@pytest.fixture()
def sample_assumptions(tmp_path: Path) -> Path:
    p = tmp_path / "assumptions.yaml"
    p.write_text(ASSUMPTIONS_YAML, encoding="utf-8")
    return p


class TestSuccessfulRun:
    def test_creates_all_four_files(self, tmp_path, sample_input, sample_assumptions):
        out = tmp_path / "run_001"
        rc = main([
            "--input", str(sample_input),
            "--assumptions", str(sample_assumptions),
            "--output-dir", str(out),
        ])
        assert rc == 0
        for name in ("employee_results.csv", "summary.json", "run_manifest.json", "run.log"):
            assert (out / name).exists(), f"Missing: {name}"

    def test_employee_count_matches_input(self, tmp_path, sample_input, sample_assumptions):
        out = tmp_path / "run_001"
        main([
            "--input", str(sample_input),
            "--assumptions", str(sample_assumptions),
            "--output-dir", str(out),
        ])
        with open(out / "employee_results.csv", newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 3  # three employees in SAMPLE_DATA

    def test_total_liability_matches_sum_of_pv(self, tmp_path, sample_input, sample_assumptions):
        out = tmp_path / "run_001"
        main([
            "--input", str(sample_input),
            "--assumptions", str(sample_assumptions),
            "--output-dir", str(out),
        ])
        # Re-compute present values independently to verify the summary total.
        # We use the unrounded formula so the comparison isn't contaminated by
        # per-row rounding (the spec requires tolerance of 0.01 on the final total).
        from src.model import (
            years_to_retirement,
            projected_salary,
            projected_service,
            annual_benefit,
            present_value,
        )
        from src.io import load_employees, load_assumptions

        asmp = load_assumptions(sample_assumptions)
        employees = load_employees(sample_input)
        expected_total = 0.0
        for emp in employees:
            ytr = years_to_retirement(emp["age"], asmp["retirement_age"])
            ps = projected_salary(
                emp["salary"],
                asmp["salary_growth_rate_pre40"],
                asmp["salary_growth_rate_post40"],
                emp["age"],
                ytr,
            )
            psvc = projected_service(emp["service"], ytr)
            ab = annual_benefit(asmp["benefit_multiplier"], psvc, ps)
            pv = present_value(ab, asmp["discount_rate"], ytr)
            expected_total += pv

        with open(out / "summary.json", encoding="utf-8") as f:
            summary = json.load(f)
        assert abs(summary["total_liability"] - round(expected_total, asmp["rounding_decimals"])) <= 0.01

    def test_reproducibility(self, tmp_path, sample_input, sample_assumptions):
        """Same inputs → same calculated values on two consecutive runs."""
        out1 = tmp_path / "run_a"
        out2 = tmp_path / "run_b"
        for out in (out1, out2):
            main([
                "--input", str(sample_input),
                "--assumptions", str(sample_assumptions),
                "--output-dir", str(out),
            ])

        def read_pv(out: Path) -> list[float]:
            with open(out / "employee_results.csv", newline="", encoding="utf-8") as f:
                return [float(r["present_value"]) for r in csv.DictReader(f)]

        assert read_pv(out1) == read_pv(out2)

        def read_hashes(out: Path):
            with open(out / "run_manifest.json", encoding="utf-8") as f:
                m = json.load(f)
            return m["input_file_sha256"], m["assumptions_file_sha256"]

        h1 = read_hashes(out1)
        h2 = read_hashes(out2)
        assert h1 == h2


class TestFailedRun:
    def test_bad_input_returns_nonzero(self, tmp_path, sample_assumptions):
        bad = tmp_path / "bad.csv"
        bad.write_text("employee_id,age,salary,service\nE001,999,50000,5\n", encoding="utf-8")
        out = tmp_path / "out"
        rc = main([
            "--input", str(bad),
            "--assumptions", str(sample_assumptions),
            "--output-dir", str(out),
        ])
        assert rc != 0

    def test_failed_run_leaves_no_final_outputs(self, tmp_path, sample_assumptions):
        bad = tmp_path / "bad.csv"
        bad.write_text("employee_id,age,salary,service\nE001,999,50000,5\n", encoding="utf-8")
        out = tmp_path / "out"
        main([
            "--input", str(bad),
            "--assumptions", str(sample_assumptions),
            "--output-dir", str(out),
        ])
        # Output dir should not exist, or if it does, not have completed-looking files
        if out.exists():
            assert not (out / "employee_results.csv").exists()
            assert not (out / "summary.json").exists()

    def test_overwrite_flag_prevents_silent_overwrite(self, tmp_path, sample_input, sample_assumptions):
        out = tmp_path / "run_001"
        # First run
        main([
            "--input", str(sample_input),
            "--assumptions", str(sample_assumptions),
            "--output-dir", str(out),
        ])
        # Second run without --overwrite should fail
        rc = main([
            "--input", str(sample_input),
            "--assumptions", str(sample_assumptions),
            "--output-dir", str(out),
        ])
        assert rc != 0
