# Requirements — Simple Pension Projection Model

> Source: KIRO_SPEC_Simple_Pension_Model.md (verbatim distillation)
> Status: Approved for initial build

---

## Purpose

Build a small, transparent Python pension projection model to evaluate Kiro Crew's
support for controlled development, testing, documentation, change management, and
reproducibility. Synthetic data only. Not for client or production use.

---

## Functional Requirements

| ID | Requirement |
|----|-------------|
| FR-01 | Read assumptions from `assumptions.yaml`; never hard-code values in calculation functions. |
| FR-02 | Accept employee data path from the command line. |
| FR-03 | Validate required columns, types, uniqueness, and ranges before calculating. |
| FR-04 | Fail closed (nonzero exit code + clear message) on any validation failure. |
| FR-05 | Implement each formula as a small, separately testable pure function. |
| FR-06 | Write employee-level results to CSV. |
| FR-07 | Write a summary JSON (employee count, total liability). |
| FR-08 | Write a run manifest JSON (full evidence record — see §8 of spec). |
| FR-09 | Never silently overwrite existing output; require `--overwrite` or a unique run directory. |
| FR-10 | Write to a temporary location; promote outputs only after all checks succeed. |

---

## Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| NF-01 | Python 3.11+. Standard library + PyYAML + pytest only unless justified. |
| NF-02 | Type hints and docstrings on all public functions. |
| NF-03 | Calculation logic separate from I/O and CLI parsing. |
| NF-04 | No network calls, databases, cloud services, email, or external MCP servers. |
| NF-05 | No secrets or credentials anywhere in the repository. |
| NF-06 | No real or sensitive employee data (no names, DOB, SSN, addresses). |
| NF-07 | Deterministic, reproducible outputs for the same code + inputs + assumptions. |
| NF-08 | A second user on a clean machine must be able to reproduce approved results. |

---

## Input Data Contract

File: `data/employees.csv`

| Column | Type | Validation |
|--------|------|------------|
| employee_id | string | Required; unique; non-blank |
| age | integer | 18–80 inclusive |
| salary | decimal | > 0 |
| service | decimal | ≥ 0; ≤ age − 14 |

---

## Formulas

| Step | Formula |
|------|---------|
| years_to_retirement | `max(retirement_age − age, 0)` |
| projected_salary | `salary × (1 + salary_growth_rate) ^ ytr` |
| projected_service | `service + ytr` |
| annual_benefit | `benefit_multiplier × projected_service × projected_salary` |
| present_value | `annual_benefit ÷ (1 + discount_rate) ^ ytr` |

Employees at or above retirement age: ytr = 0; no growth or service added.

---

## Intentional Exclusions

Mortality · Turnover · Retirement decrement · Annuity factors · Payment timing ·
Vesting · IRC 415/401(a)(17) plan limits · Taxes

All exclusions must appear in the README and every run manifest.

---

## Definition of Done

- `pytest` passes in a clean virtual environment.
- Documented command executes successfully without Kiro.
- Sample run creates all four output files and a run manifest.
- Repeated run produces identical calculated values and stable hashes.
- Invalid inputs fail safely with nonzero exit code.
- Assumptions are externalized and traceable.
- No real or sensitive data included.
- README enables independent handoff.
