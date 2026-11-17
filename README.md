# Simple Pension Projection Model

> **NOT FOR PRODUCTION USE.** This is a demonstration model using synthetic data only.
> It must not be used for client valuations or any regulated actuarial work.

---

## Purpose

This model projects defined-benefit pension liabilities for a synthetic employee group. It exists to demonstrate controlled development, testing, documentation, and reproducibility practices in an actuarial context.

---

## Formula Definitions

| Step | Formula |
|---|---|
| Years to retirement | `max(retirement_age − age, 0)` |
| Projected salary | `salary × (1 + salary_growth_rate) ^ years_to_retirement` |
| Projected service | `service + years_to_retirement` |
| Annual benefit | `benefit_multiplier × projected_service × projected_salary` |
| Present value | `annual_benefit ÷ (1 + discount_rate) ^ years_to_retirement` |

Employees at or above retirement age receive zero additional growth or service. Their present value equals their annual benefit directly.

### Exclusions

This model intentionally omits:

- Mortality decrement
- Turnover / withdrawal decrement
- Retirement decrement (assumed 100% retire at plan age)
- Annuity factors and payment timing
- Vesting schedules
- IRC Section 415 / 401(a)(17) plan limits
- Taxes

These exclusions are documented in every run manifest.

---

## Repository Structure

```
actuarial-model/
  .kiro/              # Kiro Crew spec and steering files
  data/
    employees.csv     # Synthetic input data
  output/
    .gitkeep          # Keeps folder in Git; run outputs are gitignored
  src/
    __init__.py
    model.py          # Calculation functions and CLI entry point
    io.py             # File reading, validation, and writing
    manifest.py       # Run manifest builder
  tests/
    test_model.py     # Unit tests for calculation functions
    test_io.py        # Unit tests for validation
    test_end_to_end.py
  assumptions.yaml    # Externalized actuarial assumptions
  requirements.txt
  README.md
  .gitignore
```

---

## Setup (clean machine)

Requires Python 3.11+.

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt
```

---

## Run Tests

```bash
pytest
```

All tests are deterministic and require no network access.

---

## Run the Model

```bash
python -m src.model \
  --input data/employees.csv \
  --assumptions assumptions.yaml \
  --output-dir output/run_001
```

Successful run returns exit code 0 and writes four files to `output/run_001/`.

To overwrite an existing run directory:

```bash
python -m src.model \
  --input data/employees.csv \
  --assumptions assumptions.yaml \
  --output-dir output/run_001 \
  --overwrite
```

---

## Input Definitions

`data/employees.csv` columns:

| Column | Type | Rules |
|---|---|---|
| employee_id | string | Required; unique; non-blank |
| age | integer | 18–80 inclusive |
| salary | decimal | Greater than 0 |
| service | decimal | ≥ 0; ≤ age − 14 |

No names, dates of birth, Social Security numbers, addresses, or real client data may appear in this file.

---

## Output Definitions

Each run creates a unique output directory containing:

| File | Contents |
|---|---|
| `employee_results.csv` | Per-employee computed fields (see below) |
| `summary.json` | Employee count and total liability |
| `run_manifest.json` | Full run evidence (see spec §8) |
| `run.log` | Timestamped log of the run |

`employee_results.csv` columns:

`employee_id`, `age`, `salary`, `service`, `years_to_retirement`, `projected_salary`, `projected_service`, `annual_benefit`, `present_value`

---

## Troubleshooting Common Validation Failures

| Error | Cause | Fix |
|---|---|---|
| `missing required column(s)` | CSV header does not include all four required columns | Add the missing column(s) to the CSV |
| `duplicate employee_id` | Two rows share the same ID | Correct the input file |
| `salary must be greater than 0` | Zero or negative salary | Check the data source |
| `age … outside the allowed range 18–80` | Age value out of bounds | Verify the employee record |
| `service … exceeds age-minus-14 limit` | More service than the employee's age allows | Confirm hire date and age |
| `Output directory … already contains files` | Re-running into an existing output | Use `--overwrite` or choose a new `--output-dir` |

---

## Reproducibility Procedure

1. Record the Git commit hash from `run_manifest.json → git_commit`.
2. Check out that exact commit: `git checkout <commit_hash>`.
3. Create a fresh virtual environment and install `requirements.txt`.
4. Run the model with the same `--input` and `--assumptions` files.
5. Compare `employee_results.csv` and `summary.json` to the originals.
6. Verify SHA-256 hashes in both manifests match.

Reproducibility is defined by the approved code and evidence in the manifest, not by regenerating outputs from an AI prompt.

---

## Rollback Procedure

```bash
# View commit history
git log --oneline

# Check out a prior version
git checkout <commit_hash>

# Or revert the most recent commit while keeping history
git revert HEAD
```

After rollback, re-run the model and confirm outputs match the earlier manifest.

---

## Assumptions File

`assumptions.yaml` holds all actuarial assumptions. Do not hard-code values in source files.

```yaml
valuation:
  valuation_year: 2026
  retirement_age: 65
  salary_growth_rate: 0.035
  discount_rate: 0.05
  benefit_multiplier: 0.015
  benefit_service_basis: current_service
  rounding_decimals: 2
```

Every run manifest records the full resolved assumptions and the SHA-256 hash of the assumptions file.
