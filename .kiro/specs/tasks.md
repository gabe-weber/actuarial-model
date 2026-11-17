# Tasks — Simple Pension Projection Model

> Tracking: initial build + change log

---

## Initial Build Tasks (completed)

| # | Task | Status |
|---|------|--------|
| 1 | Requirements summary and ambiguity review | ✅ Done |
| 2 | Propose design and file structure | ✅ Done |
| 3 | Generate synthetic input data (`data/employees.csv`, 12 records) | ✅ Done |
| 4 | Implement validation and pure calculation functions | ✅ Done |
| 5 | Implement CLI, output staging, logging, hashing, run manifest | ✅ Done |
| 6 | Add unit tests (27) and end-to-end tests (8) | ✅ Done |
| 7 | Run tests; fix failures before modifying requirements | ✅ Done — 35/35 pass |
| 8 | Create README | ✅ Done |
| 9 | Save spec artifacts to `.kiro/specs/` | ✅ Done |

---

## Change Log

### CHG-001 — Alternative retirement age 62

| Field | Value |
|-------|-------|
| ID | CHG-001 |
| Date | 2026-11-17 |
| Type | Assumption change (controlled) |
| Author | Kiro (requested by user) |
| Status | ✅ Merged to main |
| Scope | `assumptions.yaml` only |
| Test impact | Existing tests unaffected (parametric); new test added |

**Description:**
Add `retirement_age_alt: 62` to `assumptions.yaml` as a documented alternative
assumption. The primary assumption (`retirement_age: 65`) is unchanged. The
alternative is not wired into the CLI by default; a user passes
`--assumptions assumptions_alt62.yaml` (or edits the YAML) to run under age 62.
A companion file `assumptions_alt62.yaml` is provided for one-command comparison.

**Reason no formula change is needed:**
`retirement_age` flows through `years_to_retirement()` → all downstream
formulas. Changing the value in the YAML file is the entire change.

**Test added:**
`tests/test_model.py::TestYearsToRetirement::test_ret_age_62` — verifies that
age 40 with retirement age 62 produces 22 years to retirement.

**Comparison procedure:**
```bash
# Base run (age 65)
python -m src.model --input data/employees.csv \
  --assumptions assumptions.yaml --output-dir output/run_base65

# Alternative run (age 62)
python -m src.model --input data/employees.csv \
  --assumptions assumptions_alt62.yaml --output-dir output/run_alt62
```
Compare `summary.json` total_liability in each output directory.

---

## Open Items / Future Changes

- None currently open. Add rows here before making any actuarial or formula change.

---

## Change Log (continued)

### CHG-002 — Split salary growth rate by age bracket

| Field | Value |
|-------|-------|
| ID | CHG-002 |
| Date | 2026-11-17 |
| Type | Actuarial formula change (controlled) |
| Author | Kiro (requested by user) |
| Status | ✅ Merged to main (commit 3aeda39) |
| Scope | `assumptions.yaml`, `assumptions_alt62.yaml`, `src/model.py`, tests |
| Test impact | `TestProjectedSalary` rewritten (6 tests replacing 3); end-to-end fixture updated |

**Description:**
Replace the single `salary_growth_rate` with two age-bracketed rates:
- `salary_growth_rate_pre40`: applied for years the employee is under 40.
- `salary_growth_rate_post40`: applied for years the employee is 40 or older.

**Formula:**

```
years_pre40  = max(min(40 − age, ytr), 0)
years_post40 = ytr − years_pre40

projected_salary = salary
                 × (1 + rate_pre40)  ^ years_pre40
                 × (1 + rate_post40) ^ years_post40
```

**Default values:** pre-40 = 4.5%, post-40 = 2.5% (average ≈ 3.5% for a 30-year-old).

**Test coverage:** entirely pre-40, entirely post-40, straddle, zero ytr, rate isolation.

---

### MAINT-001 — Assumption key validation and stray import removal

| Field | Value |
|-------|-------|
| ID | MAINT-001 |
| Date | 2026-11-17 |
| Type | Maintenance (not an actuarial change) |
| Author | Kiro |
| Status | ✅ Merged to main (commit b16c649) |
| Scope | `src/io.py`, `tests/test_io.py`, `tests/test_end_to_end.py` |
| Committed separately from CHG-002 per change-management rules |

**Changes:**
- `load_assumptions()` now checks all six required keys and raises `ValueError` with key names before the model runs — prevents opaque `KeyError` during calculation.
- Three new tests added in `TestLoadAssumptions`.
- Removed unused `import yaml` from `test_end_to_end.py`.
