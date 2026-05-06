# Pycode Incorporation

## Purpose

The `pycode/` directory documents the incorporation of a modular Python implementation layer into the BSC FGI Scheduling Model. This layer was added to improve maintainability, testability, and reuse of the scheduler logic that was originally developed in notebooks.

The notebook workflow remains the primary reviewer-facing execution path. The Python package provides a structured implementation layer that mirrors the scheduler's object-based logic.

## Package Location

```text
pycode/src/bsc_fgi_scheduler/
```

## Package Metadata

Package metadata is defined in:

```text
pycode/pyproject.toml
```

Current package name:

```text
bsc-fgi-scheduler
```

Current Python requirement:

```text
>=3.10
```

Current package dependencies:

```text
pandas
numpy
openpyxl
matplotlib
scikit-learn
pytest
pytest-cov
```

## Module Inventory

```text
pycode/src/bsc_fgi_scheduler/
|-- __init__.py
|-- ap.py
|-- config.py
|-- constants.py
|-- control_charts.py
|-- data_import.py
|-- dataframes.py
|-- export.py
|-- fgi.py
|-- location.py
|-- paths.py
|-- rate_simulations.py
|-- scheduler.py
|-- trace.py
`-- validation.py
```

## Module Responsibilities

| Module | Responsibility |
|---|---|
| `ap.py` | Aircraft / line-number state, BTG state, task status, move request state, and AP-level helpers. |
| `location.py` | Location state, ownership, priority, occupancy, online status, and placement feasibility. |
| `fgi.py` | Main scheduler state manager for APs, locations, queues, movement, labor, paint, compass, and exit handling. |
| `scheduler.py` | Higher-level scheduler execution function for package-based runs. |
| `trace.py` | Daily trace capture for location occupancy, moves, labor allocation, and BTG completion. |
| `export.py` | Excel workbook export and summary export support. |
| `data_import.py` | Raw-to-staged data preparation and live-state workbook generation. |
| `dataframes.py` | Dataframe construction and transformation helpers. |
| `control_charts.py` | Monthly BTG control chart generation. |
| `rate_simulations.py` | Higher-rate scenario detection, execution, export, logging, and summary creation. |
| `validation.py` | Output validation helpers. |
| `config.py` | Runtime configuration helpers. |
| `constants.py` | Shared scheduler constants. |
| `paths.py` | Shared project path definitions. |

## Relationship to Notebook Workflow

The current repository includes both notebooks and `pycode`.

Notebook files are stored in:

```text
jupyter notebooks/
```

The Python package is stored in:

```text
pycode/src/bsc_fgi_scheduler/
```

The relationship between the two layers is:

```text
Raw and staged workbooks
        ↓
Notebook workflow for setup, execution, and handoff review
        ↓
Pycode package for reusable scheduler logic and regression testing
        ↓
Excel outputs, charts, logs, and validation checks
```

The notebooks provide transparency for academic and stakeholder review. The Python package provides separation of concerns, testability, and a cleaner path for future reuse.

## Refactor Interpretation

The `pycode` package should be read as an implementation refactor of the scheduler workflow. It separates the algorithmic responsibilities into focused modules while preserving the project’s object-based structure:

- AP-level state and task behavior belong in `AP`.
- Location feasibility and occupancy behavior belong in `Location`.
- System-level queues, movement, labor, paint, compass, and exit behavior belong in `FGI`.
- Trace recording, workbook export, control charts, data import, and validation are kept outside the core state objects.

This structure makes the project easier to audit than a single large notebook while still preserving the notebook as the clearest handoff run path.

## Handoff Interpretation

The `pycode` package is part of the submitted project state. It should be reviewed as a modular support layer for the scheduler, not as a separate product or independent production system.
