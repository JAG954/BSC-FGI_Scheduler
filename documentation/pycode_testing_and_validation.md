# Pycode Testing and Validation

## Purpose

This document summarizes the current testing layer for the modular scheduler package.

The tests in `pycode/tests/` provide regression and smoke checks for selected high-risk scheduler behaviors. They support maintainability of the refactored Python implementation layer, but they do not establish production validation.

## Test Location

```text
pycode/tests/
```

## Current Test Files

```text
pycode/tests/conftest.py
pycode/tests/test_ap.py
pycode/tests/test_compass_logic.py
pycode/tests/test_data_import_smoke.py
pycode/tests/test_exit_logic.py
pycode/tests/test_export_smoke.py
pycode/tests/test_fgi_queues.py
pycode/tests/test_imports.py
pycode/tests/test_location.py
pycode/tests/test_paint_logic.py
```

## Current Test Coverage Areas

| Test file | Coverage intent |
|---|---|
| `test_imports.py` | Confirms the package imports cleanly. |
| `test_ap.py` | Checks AP BTG completion and exit-readiness behavior. |
| `test_location.py` | Checks location placement rules. |
| `test_fgi_queues.py` | Checks move request and queue removal behavior. |
| `test_paint_logic.py` | Checks paint start, paint completion, and paint move-request behavior. |
| `test_compass_logic.py` | Checks compass queue-head behavior and CR3 completion behavior. |
| `test_exit_logic.py` | Checks DC / exit-pending behavior. |
| `test_data_import_smoke.py` | Checks simulated-rate live-state workbook generation. |
| `test_export_smoke.py` | Checks scheduler workbook export sheet structure. |

## Running Tests

From the repository root:

```bash
cd pycode
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .
pytest
```

On Windows PowerShell:

```powershell
cd pycode
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
pytest
```

For coverage:

```bash
pytest --cov=bsc_fgi_scheduler
```

## Interpretation

A passing test run means the tested package behaviors are working under the test conditions. It does not guarantee that every notebook cell has been fully ported, every production edge case is covered, or every scheduler output is correct.

The tests are best interpreted as regression support for the current refactor. They are useful for detecting broken object behavior, queue behavior, task behavior, import behavior, and export structure after code changes.

## Validation Boundary

The submitted model remains an academic decision-support model. Production validation would require review against internal production data, current operating rules, actual movement and labor constraints, and stakeholder-approved scheduling logic.
