"""Unit tests for pure calculation functions in src.model."""

import pytest

from src.model import (
    annual_benefit,
    present_value,
    projected_salary,
    projected_service,
    years_to_retirement,
)


class TestYearsToRetirement:
    def test_age_40_ret_65(self):
        assert years_to_retirement(40, 65) == 25

    def test_ret_age_62(self):
        """CHG-001: retirement age 62 alternative assumption."""
        assert years_to_retirement(40, 62) == 22

    def test_exactly_at_retirement(self):
        assert years_to_retirement(65, 65) == 0

    def test_past_retirement(self):
        assert years_to_retirement(70, 65) == 0

    def test_one_year_away(self):
        assert years_to_retirement(64, 65) == 1


class TestProjectedSalary:
    def test_entirely_pre40(self):
        # Age 30, ytr=5: all 5 years are pre-40 — CHG-004 rate 5.0%
        expected = 50000 * (1.050 ** 5)
        result = projected_salary(50000, 0.050, 0.030, age=30, ytr=5)
        assert abs(result - expected) < 1e-6

    def test_entirely_post40(self):
        # Age 45, ytr=10: all 10 years are post-40 — CHG-004 rate 3.0%
        expected = 80000 * (1.030 ** 10)
        result = projected_salary(80000, 0.050, 0.030, age=45, ytr=10)
        assert abs(result - expected) < 1e-6

    def test_straddles_age_40(self):
        # Age 35, ytr=10: 5 years pre-40 at 5.0%, 5 years post-40 at 3.0%
        expected = 60000 * (1.050 ** 5) * (1.030 ** 5)
        result = projected_salary(60000, 0.050, 0.030, age=35, ytr=10)
        assert abs(result - expected) < 1e-6

    def test_already_past_40_zero_ytr(self):
        # ytr=0: salary unchanged regardless of rates
        assert projected_salary(80000, 0.050, 0.030, age=50, ytr=0) == 80000.0

    def test_pre40_rate_higher_produces_higher_salary_for_young(self):
        # Young employee (age 25, ytr=15): higher pre-40 rate → higher projection
        low = projected_salary(50000, 0.02, 0.02, age=25, ytr=15)
        high = projected_salary(50000, 0.05, 0.02, age=25, ytr=15)
        assert high > low

    def test_post40_rate_irrelevant_for_fully_pre40_period(self):
        # Age 38, ytr=1: only 1 year pre-40; post-40 rate doesn't matter
        r1 = projected_salary(50000, 0.04, 0.00, age=38, ytr=1)
        r2 = projected_salary(50000, 0.04, 0.99, age=38, ytr=1)
        assert abs(r1 - r2) < 1e-6


class TestProjectedService:
    def test_adds_years(self):
        assert projected_service(10.0, 25) == 35.0

    def test_zero_years(self):
        assert projected_service(38.0, 0) == 38.0


class TestAnnualBenefit:
    def test_known_value(self):
        # 0.015 * 30 * 100000 = 45000
        assert abs(annual_benefit(0.015, 30.0, 100000.0) - 45000.0) < 1e-6

    def test_higher_service_increases_benefit(self):
        b1 = annual_benefit(0.015, 20.0, 80000.0)
        b2 = annual_benefit(0.015, 30.0, 80000.0)
        assert b2 > b1


class TestPresentValue:
    def test_discounts_not_compounds(self):
        # PV must be less than the future benefit for ytr > 0
        pv = present_value(50000.0, 0.0475, 10)
        assert pv < 50000.0

    def test_known_value(self):
        # 50000 / (1.0475 ** 10) — CHG-003: discount rate 4.75%
        expected = 50000.0 / (1.0475 ** 10)
        assert abs(present_value(50000.0, 0.0475, 10) - expected) < 1e-6

    def test_zero_years(self):
        # Already retired: no discounting
        assert present_value(50000.0, 0.0475, 0) == 50000.0

    def test_higher_discount_reduces_pv(self):
        pv_low = present_value(50000.0, 0.03, 20)
        pv_high = present_value(50000.0, 0.07, 20)
        assert pv_high < pv_low

    def test_higher_retirement_age_changes_pv(self):
        """Pushing retirement age out increases ytr and lowers PV (for young employees)."""
        pv_65 = present_value(50000.0, 0.0475, years_to_retirement(40, 65))
        pv_70 = present_value(50000.0, 0.0475, years_to_retirement(40, 70))
        assert pv_70 < pv_65
