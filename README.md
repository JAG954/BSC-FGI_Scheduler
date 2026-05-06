# BSC FGI Scheduling Model

## Project Summary

This repository contains a Boeing 787 Final Assembly (FA) to Final Ground Integration (FGI) scheduling model built as a Purdue capstone handoff artifact. The model represents aircraft rollout from FA, FGI task completion, paint routing, compass calibration, movement constraints, exit staging, labor allocation, and schedule trace export generation.

The included workbooks are sanitized or non-proprietary handoff data prepared for this project. The scheduler is a decision-support and analysis model, not a validated production scheduler.

## Current Status

- The included baseline output workbook completes all 93 aircraft and leaves 0 active aircraft at termination.
- The checked-in output is a reference baseline from a successful run, not a universal performance guarantee.
- The model remains a work in progress and capstone handoff artifact. Additional validation against internal production data and operating rules would be needed before operational use.

## Repository Structure

```text
BSC-FGI_Scheduler/
|-- README.md
|-- requirements.txt
|-- notebooks/
|   |-- BSC_FGI_Scheduler.ipynb
|   |-- data_import.ipynb
|   |-- move_time_estimation.ipynb
|   `-- analyze_scheduler_output.ipynb
|-- data/
|   |-- raw/
|   |   |-- FA_Status_FGI_Handoff.xlsx
|   |   |-- FGI_Locations_wPriority.xlsx
|   |   |-- FGI_Staffing_By_Shift.xlsx
|   |   |-- Nodes.xlsx
|   |   |-- Centerlines and Move Times Purdue.xlsx
|   |   `-- paint_schedules.xlsx
|   `-- staged/
|       |-- FGI_liveState.xlsx
|       `-- move_times/
|           |-- location_move_times.xlsx
|           `-- move_time_estimation.xlsx
|-- output/
|   |-- scheduler_trace_output.xlsx
|   |-- monthly_btg_control_charts.png
|   `-- nodemap.png
`-- documentation/
    |-- data_dictionary.md
    `-- requirements.txt
```

`data/raw/` contains source input files used by the import and move-time notebooks.

`data/staged/` contains files prepared for direct algorithm input. In the included baseline, `data/staged/FGI_liveState.xlsx` provides AP, location, and labor inputs, and `data/staged/move_times/move_time_estimation.xlsx` provides the calibrated movement-time matrix used by the scheduler.

`output/` is intentionally visible and trackable. It contains reference outputs from successful runs so reviewers can inspect the expected workbook structure and baseline trace outputs.

`documentation/` contains supporting handoff documentation, including the data dictionary.

## Input Files

The current scheduler run uses the following files.

| Path | Purpose |
|---|---|
| `data/staged/FGI_liveState.xlsx` | Staged AP, location, and labor input workbook used directly by `notebooks/BSC_FGI_Scheduler.ipynb`. |
| `data/staged/move_times/move_time_estimation.xlsx` | Calibrated origin-destination move-time matrix used directly by the scheduler. |
| `data/raw/paint_schedules.xlsx` | Paint schedule input. The scheduler reads the `Historical` sheet and uses `BSC1` / `BSC2` bay assignments. |
| `data/raw/FA_Status_FGI_Handoff.xlsx` | Raw AP, FA rollout, BTG, tank closure, and P3 milestone source workbook used by `notebooks/data_import.ipynb`. |
| `data/raw/FGI_Locations_wPriority.xlsx` | Raw FGI location priority, online date, owner, tooling, centerline, obstruction, and notes source workbook. |
| `data/raw/Nodes.xlsx` | Node and adjacency source used for route and move-time estimation. |
| `data/raw/Centerlines and Move Times Purdue.xlsx` | Historical move-time and centerline reference data used by the move-time estimation notebook. |
| `data/raw/FGI_Staffing_By_Shift.xlsx` | Staffing reference workbook. Current scheduler staffing assumptions should be checked in the notebooks before use. |

## Output Files

The main scheduler output is:

```text
output/scheduler_trace_output.xlsx
```

The current output workbook contains these sheets:

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

Additional reference outputs include:

| Path | Purpose |
|---|---|
| `output/monthly_btg_control_charts.png` | Generated BTG control chart image from the analysis notebook. |
| `output/nodemap.png` | Generated node map image from the move-time notebook. |

## How To Run

1. Clone the repository and enter it.

   ```bash
   git clone <repo-url>
   cd BSC-FGI_Scheduler
   ```

2. Create and activate a local Python environment.

   ```bash
   python3.11 -m venv .venv
   source .venv/bin/activate
   ```

3. Install notebook dependencies.

   ```bash
   pip install -r requirements.txt
   ```

4. Start Jupyter and open the scheduler notebook.

   ```bash
   cd notebooks
   jupyter notebook BSC_FGI_Scheduler.ipynb
   ```

5. Run the scheduler notebook cells in order.

6. Confirm the main output workbook was generated or updated. From the notebook working directory this is:

   ```text
   ../output/scheduler_trace_output.xlsx
   ```

   From the repository root this is:

   ```text
   output/scheduler_trace_output.xlsx
   ```

The current scheduler notebook uses notebook-relative path assumptions and is normally run from the `notebooks/` directory. If paths fail, check the path setup cells before changing input files.

If raw inputs or import assumptions change, rerun `notebooks/data_import.ipynb` from the repository root to rebuild `data/staged/FGI_liveState.xlsx`, then rerun the scheduler notebook. If the move-time matrix needs to be rebuilt, review and rerun `notebooks/move_time_estimation.ipynb`, then rerun the scheduler.

## Requirements / Environment

The current notebooks were inspected against Python 3.11. Required packages are listed in `requirements.txt`.

Core dependencies:

- `pandas`, `numpy`, and `openpyxl` for workbook input/output and data transformations
- `matplotlib` for generated charts and node maps
- `seaborn` because it is imported by the scheduler notebook
- `scikit-learn` for move-time calibration in `notebooks/move_time_estimation.ipynb`
- `jupyter` and `ipykernel` for notebook execution

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

## License / Ownership Note

No license file is currently included. Usage rights should be confirmed with the project authors / Purdue capstone team before reuse.

This repository should not be read as a Boeing-owned or Boeing-licensed software release.

## Handoff Note

Before relying on results, users should review input assumptions, inspect the staged inputs, rerun the notebooks locally, and compare the regenerated outputs against expected workbook sheets and KPI rows. The checked-in output workbook is a reference baseline for review, not a guarantee of future run performance.
