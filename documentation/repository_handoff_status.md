# Repository Handoff Status

## Purpose

This document summarizes the repository state at handoff for the BSC FGI Scheduling Model. It is intended to support review by Boeing stakeholders and Purdue course evaluators by documenting the current file organization, model layers, committed inputs, committed outputs, and interpretation limits.

## Project Scope

This repository contains a Boeing 787 Final Assembly (FA) to Final Ground Integration (FGI) scheduling model developed as a Purdue capstone handoff artifact. The model represents aircraft rollout from FA, FGI task completion, paint routing, compass calibration, movement constraints, labor allocation, exit staging, and schedule trace output generation.

The repository uses sanitized or non-proprietary handoff data prepared for this academic project. The model should be interpreted as a decision-support and analysis model, not as a production-validated operational scheduler.

## Current Repository Structure

The handoff repository is organized into data inputs, staged algorithm inputs, notebook workflows, modular Python code, reference outputs, and supporting documentation.

```text
BSC-FGI_Scheduler/
|-- README.md
|-- .gitignore
|-- data/
|   |-- raw/
|   |-- simulated/
|   `-- staged/
|-- documentation/
|-- jupyter notebooks/
|-- output/
`-- pycode/
```

## Notebook Workflow

The current notebook workflow is stored in:

```text
jupyter notebooks/
```

Current notebook files:

```text
jupyter notebooks/BSC_FGI_Scheduler.ipynb
jupyter notebooks/data_import.ipynb
jupyter notebooks/move_time_estimation.ipynb
jupyter notebooks/analyze_scheduler_output.ipynb
```

The notebook workflow remains the clearest reviewer-facing execution path because it exposes setup assumptions, data loading, scheduler execution, and output review in a linear format.

## Data Layout

Raw source workbooks are stored under:

```text
data/raw/
```

Current raw files:

```text
data/raw/Centerlines and Move Times Purdue.xlsx
data/raw/FA_Status_FGI_Handoff.xlsx
data/raw/FGI_Locations_wPriority.xlsx
data/raw/FGI_Staffing_By_Shift.xlsx
data/raw/Nodes.xlsx
data/raw/paint_schedules.xlsx
```

Staged algorithm-ready files are stored under:

```text
data/staged/
```

Current staged files:

```text
data/staged/FGI_liveState.xlsx
data/staged/move_times/location_move_times.xlsx
data/staged/move_times/move_time_estimation.xlsx
```

Simulated higher-rate inputs are stored under:

```text
data/simulated/
```

Current simulated input files:

```text
data/simulated/FA_Status_FGI_Handoff_R10.xlsx
data/simulated/FA_Status_FGI_Handoff_R12.xlsx
data/simulated/FA_Status_FGI_Handoff_R14.xlsx
data/simulated/FA_Status_FGI_Handoff_R20.xlsx
```

## Output Layout

The repository includes baseline scheduler outputs and selected higher-rate simulation outputs.

Current baseline output files:

```text
output/scheduler_trace_output.xlsx
output/monthly_btg_control_charts.png
output/nodemap.png
```

Current committed rate simulation output folders:

```text
output/rate simulation/R10/
output/rate simulation/R12/
output/rate simulation/R14/
```

Each committed rate simulation output folder contains:

```text
scheduler_outputs/FGI_liveState.xlsx
scheduler_outputs/scheduler_trace_output.xlsx
control_charts/monthly_btg_control_charts.png
```

The repository includes an `R20` simulated input workbook, but the current committed handoff files do not include a matching `output/rate simulation/R20/` output folder. Therefore, the committed rate simulation outputs should be interpreted as available for R10, R12, and R14 only.

## Python Package Layer

The repository includes a modular Python package under:

```text
pycode/src/bsc_fgi_scheduler/
```

This package separates scheduler functionality into reusable modules for aircraft state, location state, scheduler state, trace recording, data import, Excel export, control chart generation, rate simulations, validation, constants, configuration, and paths.

The Python package supports maintainability and testing. It does not replace the notebook workflow as the primary handoff interface.

## Current Test Layer

The repository includes package tests under:

```text
pycode/tests/
```

These tests cover selected smoke checks and high-risk scheduler behaviors, including imports, AP logic, location placement, queue behavior, paint logic, compass logic, exit behavior, simulated-rate data import, and export workbook structure.

The tests should be interpreted as regression support for the refactored code layer. Passing tests do not constitute operational validation.

## Handoff Interpretation

The repository should be understood as having three integrated layers:

1. Notebook workflow for transparent execution and review.
2. Data workbooks for raw, staged, and simulated scenario inputs.
3. Modular Python code for reusable scheduler logic and regression testing.

The checked-in outputs are reference artifacts generated under the current committed assumptions and code. They are useful for reviewing expected workbook structure, trace format, and scenario outputs, but they should not be interpreted as production guarantees.

## Use Limitations

The model is not an autonomous production scheduling system. Before operational use, the model would require validation against internal production data, current operating rules, actual resource constraints, and stakeholder-approved decision logic.
