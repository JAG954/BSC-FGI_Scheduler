# BSC FGI Scheduling Model

## Project Summary

This repository contains a Boeing 787 Final Assembly (FA) to Final Ground Integration (FGI) scheduling model built as a Purdue capstone handoff artifact. The model represents aircraft rollout from FA, FGI task completion, paint routing, compass calibration, movement constraints, exit staging, labor allocation, and schedule trace export generation.

The included workbooks are sanitized or non-proprietary handoff data prepared for this project. The scheduler is a decision-support and analysis model, not a validated production scheduler.

## Current Status

- The included baseline output workbook completes all 93 aircraft and leaves 0 active aircraft at termination.
- The checked-in output is a reference baseline from a successful run, not a universal performance guarantee.
- The repository includes a notebook workflow, a modular Python package layer, staged data inputs, simulated higher-rate inputs, and committed reference outputs.
- The model remains a capstone handoff artifact. Additional validation against internal production data and operating rules would be needed before operational use.

## Repository Structure

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

## Output Files

The main scheduler output is:

```text
output/scheduler_trace_output.xlsx
```

The current baseline output set includes:

```text
output/scheduler_trace_output.xlsx
output/monthly_btg_control_charts.png
output/nodemap.png
```

Committed higher-rate simulation output folders are present for:

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

The repository includes an `R20` simulated input workbook, but the submitted file set does not include a committed `output/rate simulation/R20/` output folder.

## Main Trace Workbook

The main scheduler trace workbook is expected to contain:

| Sheet | Contents |
|---|---|
| `ChickenTracks` | Daily location trace by date and location. |
| `Labor Allocation` | Daily AP labor allocation by FGI team. |
| `Moves Per Day` | Successful move trace by date and line number. |
| `Daily AP Status` | End-of-day AP location, remaining FGI BTG, and move request status. |
| `Exit Summary` | FA rollout, planned B1R, actual exit, days in system, lateness, and final location. |
| `Active AP Status` | APs still active at termination and their queue or task blockers. |
| `KPI Summary` | Run-level delivery, active AP, time-in-system, move, and labor KPIs. |
| `Team KPIs` | Team-level AP count, BTG completion, and workday KPIs. |
| `BTG structure` | Daily structure BTG completion by line number. |
| `BTG systems` | Daily systems BTG completion by line number. |
| `BTG declam` | Daily declam BTG completion by line number. |
| `BTG test` | Daily test BTG completion by line number. |

## Pycode Package Layer

The repository includes a modular Python package under:

```text
pycode/src/bsc_fgi_scheduler/
```

This package separates scheduler functionality into reusable modules for aircraft state, location state, scheduler state, trace recording, data import, Excel export, control chart generation, rate simulations, validation, constants, configuration, and paths.

Important modules include:

| Module | Purpose |
|---|---|
| `ap.py` | Aircraft / line-number state, BTG state, task status, move request state, and AP-level helpers. |
| `location.py` | Location state, ownership, priority, occupancy, online status, and placement feasibility. |
| `fgi.py` | Main scheduler state manager for APs, locations, queues, movement, labor, paint, compass, and exit handling. |
| `scheduler.py` | Higher-level scheduler execution function for package-based runs. |
| `trace.py` | Daily trace capture for location occupancy, moves, labor allocation, and BTG completion. |
| `export.py` | Excel workbook export and summary export support. |
| `data_import.py` | Raw-to-staged data preparation and live-state workbook generation. |
| `control_charts.py` | Monthly BTG control chart generation. |
| `rate_simulations.py` | Higher-rate scenario detection, execution, export, logging, and summary creation. |
| `validation.py` | Output validation helpers. |

## Rate Simulation Run Conditions

The higher-rate simulation workflow is implemented in:

```text
pycode/src/bsc_fgi_scheduler/rate_simulations.py
```

The submitted rate simulation runner uses these conditions:

| Setting | Value |
|---|---|
| `STARTDATE` | `2026-04-01` |
| `ENDDATE` | `2028-06-30` |
| `FORECAST_UNTIL_COMPLETION` | `True` |
| `FORECAST_CAP_DAYS` | `365` |
| `CODECELL_OUTPUT` | `False` |
| Export | `True` |

Each detected `data/simulated/FA_Status_FGI_Handoff_R*.xlsx` workbook is treated as a separate scenario.

## How To Run

Clone the repository and enter it:

```bash
git clone <repo-url>
cd BSC-FGI_Scheduler
```

Create and activate a local Python environment:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

Install notebook dependencies:

```bash
pip install -r documentation/requirements.txt
```

Open the scheduler notebook:

```bash
cd "jupyter notebooks"
jupyter notebook BSC_FGI_Scheduler.ipynb
```

Run the scheduler notebook cells in order.

To run the modular Python package tests:

```bash
cd pycode
pip install -e .
pytest
```

To run all detected rate simulations:

```bash
cd pycode
python -m bsc_fgi_scheduler.rate_simulations
```

## Model Assumptions

- APs enter the model at their FA rollout date.
- FGI work is represented through converted BTG labor buckets by team.
- Paint routing follows the input paint schedule, currently using `BSC1` and `BSC2`.
- Compass calibration uses `CR3`; `CR1` and `CR2` must be clear for the completion condition.
- DC / A-stall style locations represent exit staging in the model.
- Movement feasibility depends on location availability, online status, move-time availability, and centerline constraints.
- Outputs are simulation and decision-support traces. They should be reviewed before being used for planning decisions.
- Internal Boeing validation would be needed before operational use.

## Known Limitations

- Sanitized handoff data may not match the live production state.
- Movement times and location constraints depend on the included input assumptions and calibration data.
- Task logic is simplified relative to real production execution.
- Shake and tank-closure details are represented only to the extent reflected in the current staged inputs and notebook logic.
- The current model supports analysis and handoff review. It is not an autonomous production scheduling system.
- The notebooks are path-sensitive in places; review path setup cells when running from a new Jupyter environment.
- R20 exists as a simulated input, but no committed R20 output folder is included in the submitted repository state.

## License / Ownership Note

No license file is currently included. Usage rights should be confirmed with the project authors / Purdue capstone team before reuse.

This repository should not be read as a Boeing-owned or Boeing-licensed software release.

## Handoff Note

Before relying on results, users should review input assumptions, inspect the staged inputs, rerun the notebooks locally, and compare regenerated outputs against expected workbook sheets and KPI rows. The checked-in output workbooks are reference artifacts for review, not guarantees of future run performance.
