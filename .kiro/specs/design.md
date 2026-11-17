# Design — Simple Pension Projection Model

> Status: Approved (matches built implementation)

---

## Repository Layout

```
actuarial-model/
  .kiro/
    specs/          ← requirements, design, tasks (this folder)
    steering/       ← Kiro steering rules
  data/
    employees.csv   ← synthetic input (12 records)
  output/
    .gitkeep
    run_*/          ← gitignored; created at runtime
  src/
    __init__.py
    model.py        ← pure calc functions + CLI entry point
    io.py           ← file reading, validation, writing
    manifest.py     ← run manifest builder
  tests/
    __init__.py
    test_model.py   ← 15 unit tests (pure functions)
    test_io.py      ← 12 unit tests (validation)
    test_end_to_end.py ← 8 integration tests
  assumptions.yaml  ← all actuarial assumptions
  requirements.txt  ← PyYAML>=6.0, pytest>=7.4
  README.md
  .gitignore
```

---

## Module Responsibilities

### `src/model.py`
- Five pure, independently testable calculation functions:
  `years_to_retirement`, `projected_salary`, `projected_service`,
  `annual_benefit`, `present_value`
- `calculate_employee`: applies all formulas for one employee dict
- `main()`: CLI entry point; orchestrates load → validate → calculate →
  stage → promote; returns exit code

### `src/io.py`
- `load_assumptions(path)`: reads and validates YAML structure
- `load_employees(path)`: reads CSV, validates all columns/types/ranges,
  raises `ValueError` with row + field context on any failure
- `write_employee_results`, `write_summary`, `write_manifest`: output writers
- `sha256_file(path)`: utility used by manifest and summary

### `src/manifest.py`
- `build_manifest(...)`: assembles the full evidence record
- Captures: run ID, UTC timestamps, status, CLI args, git commit (or null +
  warning), Python version, OS, requirements hash, input/assumptions paths
  and hashes, resolved assumptions, output file hashes, warnings, exclusions

---

## Data Flow

```
CLI args
   │
   ├─ load_assumptions() → assumptions dict
   ├─ load_employees()   → validated employee list
   │
   ├─ calculate_employee() × N  (pure, no I/O)
   │
   ├─ [write to temp dir]
   │     employee_results.csv
   │     summary.json
   │     run_manifest.json
   │     run.log
   │
   └─ promote temp → output_dir  (only on full success)
```

Failed runs: temp dir is cleaned up; output_dir is never created or populated.

---

## Output Staging (Atomicity)

Outputs are written to `tempfile.mkdtemp()` and copied to the final
`--output-dir` only after all files are written successfully. The log handler
is explicitly closed before temp-dir removal (required on Windows due to
exclusive file locks).

---

## Overwrite Protection

If `--output-dir` exists and is non-empty, the run exits with code 1 and
a clear message unless `--overwrite` is passed.

---

## Run Manifest Fields

run_id · start_time_utc · end_time_utc · status · cli_args · git_commit ·
git_commit_warning · python_version · platform · requirements_txt_sha256 ·
input_file · input_file_sha256 · assumptions_file · assumptions_file_sha256 ·
resolved_assumptions · output_dir · output_file_sha256 · warnings ·
model_exclusions

---

## Test Strategy

| Suite | File | Count | Scope |
|-------|------|-------|-------|
| Unit — calculations | test_model.py | 15 | Pure functions only; no I/O |
| Unit — validation | test_io.py | 12 | CSV validation edge cases |
| End-to-end | test_end_to_end.py | 8 | Full CLI round-trips; pass + fail paths |

All tests use `pytest`, are deterministic, and require no network access.

---

## Dependency Rationale

| Package | Reason |
|---------|--------|
| PyYAML | Read `assumptions.yaml`; stdlib has no YAML parser |
| pytest | Test runner; industry standard |

No other third-party dependencies. All other needs (CSV, JSON, hashing,
logging, argparse, tempfile, subprocess) are covered by the standard library.
