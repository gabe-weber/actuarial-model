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
    def test_known_value(self):
        # salary=50000, growth=0.035, ytr=10 → 50000*(1.035**10)
        expected = 50000 * (1.035 ** 10)
        assert abs(projected_salary(50000, 0.035, 10) - expected) < 1e-6

    def test_zero_years(self):
        # No growth when already retired
        assert projected_salary(80000, 0.035, 0) == 80000.0

    def test_higher_growth_produces_higher_salary(self):
        low = projected_salary(60000, 0.02, 20)
        high = projected_salary(60000, 0.05, 20)
        assert high > low


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
        pv = present_value(50000.0, 0.05, 10)
        assert pv < 50000.0

    def test_known_value(self):
        # 50000 / (1.05 ** 10)
        expected = 50000.0 / (1.05 ** 10)
        assert abs(present_value(50000.0, 0.05, 10) - expected) < 1e-6

    def test_zero_years(self):
        # Already retired: no discounting
        assert present_value(50000.0, 0.05, 0) == 50000.0

    def test_higher_discount_reduces_pv(self):
        pv_low = present_value(50000.0, 0.03, 20)
        pv_high = present_value(50000.0, 0.07, 20)
        assert pv_high < pv_low

    def test_higher_retirement_age_changes_pv(self):
        """Pushing retirement age out increases ytr and lowers PV (for young employees)."""
        # age=40, benefit=50000, rate=0.05
        pv_65 = present_value(50000.0, 0.05, years_to_retirement(40, 65))
        pv_70 = present_value(50000.0, 0.05, years_to_retirement(40, 70))
        assert pv_70 < pv_65
