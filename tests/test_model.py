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
    def test_age_40_ret_62(self):
        """CHG-005: primary retirement age is now 62."""
        assert years_to_retirement(40, 62) == 22

    def test_ret_age_65_still_works(self):
        """Parametric check; function unchanged."""
        assert years_to_retirement(40, 65) == 25

    def test_ret_age_62(self):
        """CHG-001: retirement age 62 alternative assumption."""
        assert years_to_retirement(40, 62) == 22

    def test_exactly_at_retirement(self):
        assert years_to_retirement(62, 62) == 0

    def test_past_retirement(self):
        assert years_to_retirement(70, 62) == 0

    def test_one_year_away(self):
        assert years_to_retirement(61, 62) == 1


class TestProjectedSalary:
    def test_known_value(self):
        # salary=50000, growth=0.040, ytr=10 → 50000*(1.040**10) — CHG-006
        expected = 50000 * (1.040 ** 10)
        assert abs(projected_salary(50000, 0.040, 10) - expected) < 1e-6

    def test_zero_years(self):
        # Already retired: no growth applied
        assert projected_salary(80000, 0.040, 0) == 80000.0

    def test_higher_growth_produces_higher_salary(self):
        low = projected_salary(60000, 0.02, 20)
        high = projected_salary(60000, 0.05, 20)
        assert high > low

    def test_changing_rate_changes_result(self):
        # Confirm 4.0% and 3.5% produce different results
        at_35 = projected_salary(60000, 0.035, 15)
        at_40 = projected_salary(60000, 0.040, 15)
        assert at_40 > at_35


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
