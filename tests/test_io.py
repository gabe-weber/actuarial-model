"""Unit tests for validation logic in src.io."""

import csv
import io
import textwrap
from pathlib import Path

import pytest

from src.io import load_employees


def _write_csv(tmp_path: Path, rows: list[dict], filename: str = "emp.csv") -> Path:
    p = tmp_path / filename
    if rows:
        with open(p, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
    else:
        p.write_text("")
    return p


VALID_ROW = {"employee_id": "E001", "age": "40", "salary": "80000", "service": "15"}


class TestMissingColumns:
    def test_missing_salary_column(self, tmp_path):
        p = tmp_path / "emp.csv"
        p.write_text("employee_id,age,service\nE001,40,15\n")
        with pytest.raises(ValueError, match="salary"):
            load_employees(p)

    def test_missing_multiple_columns(self, tmp_path):
        p = tmp_path / "emp.csv"
        p.write_text("employee_id\nE001\n")
        with pytest.raises(ValueError):
            load_employees(p)


class TestDuplicateId:
    def test_duplicate_employee_id(self, tmp_path):
        rows = [
            VALID_ROW.copy(),
            {**VALID_ROW, "age": "35", "service": "10"},
        ]
        p = _write_csv(tmp_path, rows)
        with pytest.raises(ValueError, match="duplicate"):
            load_employees(p)


class TestInvalidSalary:
    def test_nonnumeric_salary(self, tmp_path):
        rows = [{**VALID_ROW, "salary": "not_a_number"}]
        p = _write_csv(tmp_path, rows)
        with pytest.raises(ValueError, match="salary"):
            load_employees(p)

    def test_zero_salary(self, tmp_path):
        rows = [{**VALID_ROW, "salary": "0"}]
        p = _write_csv(tmp_path, rows)
        with pytest.raises(ValueError, match="salary"):
            load_employees(p)

    def test_negative_salary(self, tmp_path):
        rows = [{**VALID_ROW, "salary": "-500"}]
        p = _write_csv(tmp_path, rows)
        with pytest.raises(ValueError, match="salary"):
            load_employees(p)


class TestInvalidAge:
    def test_age_below_minimum(self, tmp_path):
        rows = [{**VALID_ROW, "age": "17"}]
        p = _write_csv(tmp_path, rows)
        with pytest.raises(ValueError, match="age"):
            load_employees(p)

    def test_age_above_maximum(self, tmp_path):
        rows = [{**VALID_ROW, "age": "81", "service": "10"}]
        p = _write_csv(tmp_path, rows)
        with pytest.raises(ValueError, match="age"):
            load_employees(p)

    def test_nonnumeric_age(self, tmp_path):
        rows = [{**VALID_ROW, "age": "forty"}]
        p = _write_csv(tmp_path, rows)
        with pytest.raises(ValueError, match="age"):
            load_employees(p)


class TestInvalidService:
    def test_service_exceeds_age_minus_14(self, tmp_path):
        # age=25 → max service = 11; service=12 is invalid
        rows = [{"employee_id": "E001", "age": "25", "salary": "50000", "service": "12"}]
        p = _write_csv(tmp_path, rows)
        with pytest.raises(ValueError, match="service"):
            load_employees(p)

    def test_negative_service(self, tmp_path):
        rows = [{**VALID_ROW, "service": "-1"}]
        p = _write_csv(tmp_path, rows)
        with pytest.raises(ValueError, match="service"):
            load_employees(p)


class TestValidData:
    def test_valid_rows_load_cleanly(self, tmp_path):
        rows = [VALID_ROW.copy(), {**VALID_ROW, "employee_id": "E002", "age": "30", "service": "5"}]
        p = _write_csv(tmp_path, rows)
        result = load_employees(p)
        assert len(result) == 2
        assert result[0]["employee_id"] == "E001"
        assert result[0]["age"] == 40
        assert result[0]["salary"] == 80000.0
        assert result[0]["service"] == 15.0
