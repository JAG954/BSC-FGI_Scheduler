# BSC-FGI Scheduler

## Overview

This repository contains a scheduling and trace-output workflow for modeling aircraft progression after Final Assembly rollout into BSC FGI / parking operations.

The scheduler tracks aircraft position, location occupancy, centerline constraints, paint bay assignments, compass calibration, labor-driven BTG completion, queue-based delivery readiness, and Excel-based schedule outputs. The goal is to create a readable planning model that shows how aircraft move through FGI, where capacity gets constrained, and how labor and location availability affect delivery timing.

The main workflow is implemented in:

```text
BSC_FGI_Scheduler.ipynb
```

The supporting move-time model is implemented in:

```text
move_time_estimation.ipynb
```

---

## Repository Structure

```text
BSC-FGI_Scheduler/
|-- BSC_FGI_Scheduler.ipynb
|-- data_import.ipynb
|-- move_time_estimation.ipynb
|-- data/
|   |-- raw/
|   |   |-- Centerlines and Move Times Purdue.xlsx
|   |   |-- FA_Status_FGI_Handoff.xlsx
|   |   |-- FGI_Locations_wPriority.xlsx
|   |   |-- FGI_Staffing_By_Shift.xlsx
|   |   |-- Nodes.xlsx
|   |   `-- paint_schedules.xlsx
|   `-- staged/
|       |-- FGI_liveState.xlsx
|       `-- move_times/
|           |-- location_move_times.xlsx
|           `-- move_time_estimation.xlsx
|-- output/
|   |-- monthly_btg_control_charts.png
|   `-- scheduler_trace_output.xlsx
`-- README.md
```

---

## Data Folder Structure

`data/raw/` contains original source workbooks maintained outside the scheduling algorithm. These files are the external source data used by the import and move-time workflows.

`data/staged/` contains notebook-generated or notebook-assembled files that are directly consumed by later notebooks or by the scheduler itself. In this repo, "staged" means the file has already been cleaned, transformed, calibrated, or assembled into the format expected by the algorithm. These files are not final deliverables, but they are active inputs to the scheduling process.

`output/` contains final exported scheduler results, reports, and visualizations.

The main data pipeline is:

```text
data/raw/*.xlsx
+ data/staged/move_times/move_time_estimation.xlsx
-> data_import.ipynb
-> data/staged/FGI_liveState.xlsx
-> BSC_FGI_Scheduler.ipynb
-> output/*.xlsx / *.png
```

Key staged files:

| File | Purpose |
|---|---|
| `data/staged/FGI_liveState.xlsx` | Main staged scheduler input assembled by `data_import.ipynb`. |
| `data/staged/move_times/move_time_estimation.xlsx` | Active calibrated move-time matrix used by the scheduler. |
| `data/staged/move_times/location_move_times.xlsx` | Uncalibrated/original model output from `move_time_estimation.ipynb`. |

---

## Main Workflow

1. `move_time_estimation.ipynb` reads node layout and historical move-time data from `data/raw/`.
2. It writes the uncalibrated move-time matrix to `data/staged/move_times/location_move_times.xlsx`.
3. It calibrates that matrix against historical move times and writes the active calibrated matrix to `data/staged/move_times/move_time_estimation.xlsx`.
4. `data_import.ipynb` reads raw AP, location, node, paint, and staged move-time inputs.
5. `data_import.ipynb` writes `data/staged/FGI_liveState.xlsx`.
6. `BSC_FGI_Scheduler.ipynb` reads `data/staged/FGI_liveState.xlsx`.
7. `BSC_FGI_Scheduler.ipynb` exports final results to `output/`.

The internal sheets in `data/staged/FGI_liveState.xlsx` are:

- `ap_data`
- `location_data`
- `labor_data`
- `move_times`
- `paint_schedule`

---

## Important Data Files

| File | Purpose | Used by |
|---|---|---|
| `data/raw/FA_Status_FGI_Handoff.xlsx` | Raw AP / FARO status, tank closure, and milestone input. | `data_import.ipynb`. |
| `data/raw/FGI_Locations_wPriority.xlsx` | Location priority, online timing, owner, tooling, obstruction, and note reference. | `data_import.ipynb`. |
| `data/raw/Nodes.xlsx` | Node and adjacency input for location movement modeling. | `move_time_estimation.ipynb`; also cleaned by `data_import.ipynb`. |
| `data/raw/paint_schedules.xlsx` | Paint bay schedule for `BSC1` and `BSC2`. | `data_import.ipynb`. |
| `data/raw/Centerlines and Move Times Purdue.xlsx` | Historical move-time and centerline reference data. | `move_time_estimation.ipynb`. |
| `data/raw/FGI_Staffing_By_Shift.xlsx` | Staffing reference workbook. | Reference file; default import uses notebook staffing assumptions unless changed. |
| `data/staged/move_times/move_time_estimation.xlsx` | Calibrated move-time matrix copied into the live-state workbook. | `data_import.ipynb`; then `BSC_FGI_Scheduler.ipynb`. |
| `data/staged/FGI_liveState.xlsx` | Assembled scheduler input workbook. | `BSC_FGI_Scheduler.ipynb`. |

---

## Move-Time Estimation Notebook

`move_time_estimation.ipynb` supports the scheduler by building and calibrating the move-time matrix.

It currently:

- loads nodes and adjacency from `data/raw/Nodes.xlsx`
- builds a movement graph
- applies shortest-path logic to estimate route distance
- converts distance to modeled move time using a 3 mph assumption
- exports the uncalibrated matrix to `data/staged/move_times/location_move_times.xlsx`
- loads historical moves from `data/raw/Centerlines and Move Times Purdue.xlsx`
- removes historical centerline moves from the calibration set
- fits a linear calibration model using `sklearn.linear_model.LinearRegression`
- exports the calibrated scheduler matrix to `data/staged/move_times/move_time_estimation.xlsx`

The scheduler uses the calibrated matrix after `data_import.ipynb` copies it into `data/staged/FGI_liveState.xlsx` as the `move_times` sheet.

---

## Scheduler Notebook

`BSC_FGI_Scheduler.ipynb` loads all active scheduler inputs from:

```text
data/staged/FGI_liveState.xlsx
```

The scheduler notebook follows this general sequence:

1. Set local paths, run dates, forecast behavior, and export settings.
2. Load AP, location, labor, move-time, and paint-schedule data from the staged live-state workbook.
3. Initialize the core `AP`, `Location`, `FGI`, and `FGITrace` objects.
4. Add locations, active aircraft, move-time dictionaries, queues, and trace tracking to the scheduler.
5. Run a day-by-day simulation from `STARTDATE` to `ENDDATE`, with optional forecast continuation.
6. Roll APs into FGI when their FA rollout date is reached.
7. Apply shift-based labor capacity to structure, systems, declam, and test BTG.
8. Schedule paint moves and compass moves.
9. Process feasible moves during the move window.
10. Check end-of-day delivery readiness.
11. Record daily AP status and trace state.
12. Export final scheduler workbooks and visualizations to `output/`.

---

## Core Scheduler Objects

### `AP`

Represents one aircraft / line number. It stores rollout timing, BTG values, P3 milestones, shake and test status, current location, task state, move request state, destination, and task completion flags.

### `Location`

Represents a physical or temporary scheduler location. It stores priority, online status, owner and tooling fields, centerline dependencies, current AP occupancy, schedule history, temporary-location flag, and move times to other locations.

### `FGI`

Owns the active scheduler state: active APs, locations, move queue, paint queue, compass queue, labor queues, AP movement, centerline movement, paint scheduling, compass scheduling, labor assignment, delivery readiness, daily status rows, delivery rows, and KPI tables.

### `FGITrace`

Records daily location occupancy, labor allocation, successful moves, and BTG completion by team. At export time, these trace dictionaries are converted into dataframes and written to Excel.

---

## Queue and Task Logic

| Queue | Meaning |
|---|---|
| `move` | APs with an active move request. |
| `FGI task:paint` | APs still waiting on paint workflow completion. |
| `FGI task:compass` | APs still waiting on compass calibration completion. |
| `labor:structure` | APs with remaining structure BTG. |
| `labor:systems` | APs with remaining systems BTG. |
| `labor:declam` | APs with remaining declam BTG. |
| `labor:test` | APs with remaining test BTG. |

When an AP enters FGI, it is added to paint and compass queues. It is also added to each labor queue where that AP has remaining FGI BTG.

Labor capacity is applied by shift. The notebook converts available manhours into BTG completion using `FGI_CPJ`, then works APs in queue order. Once a team's BTG reaches zero for an AP, that AP is removed from that team's labor queue.

---

## Movement Logic

The scheduler uses the `move_times` sheet in `data/staged/FGI_liveState.xlsx`. Row labels and column labels are converted to strings, values are coerced to numeric, and the matrix is stored as a nested dictionary.

A move destination is only feasible if:

- the destination exists in `fgi.Locations`
- the destination is online
- the destination is empty
- the origin-to-destination move time is finite
- the destination is not a temporary staging location during normal move selection

When an AP needs a move and does not have a fixed destination, `AP.get_move_candidates()` builds feasible destinations and sorts them by:

1. lower location priority value
2. lower move time

Temporary `N##` locations are staging locations, not normal parking locations. They are only used when a centerline-constrained move requires another AP to be temporarily cleared out of the way.

---

## Paint, Compass, and Delivery Logic

Paint scheduling looks ahead to the next day's paint schedule. If an AP is scheduled for `BSC1` or `BSC2`, it receives a fixed destination move request for that bay. Paint is considered complete when an AP moves out of `BSC1` or `BSC2`.

Compass calibration is centered on `CR3`. Compass is considered complete only after the AP has occupied `CR3` for at least one workday and `CR1` and `CR2` are unoccupied on that qualifying workday.

Delivery readiness is based on queue absence. At the end of each simulated day, an AP can leave active FGI only if it has no move, paint, compass, or labor blockers and no assigned destination.

---

## Output Files

| Output | Description |
|---|---|
| `output/scheduler_trace_output.xlsx` | Main scheduler trace and KPI workbook. |
| `output/monthly_btg_control_charts.png` | Monthly BTG control chart image from supporting analysis. |

Expected sheets in `output/scheduler_trace_output.xlsx` include:

| Sheet | Contents |
|---|---|
| `ChickenTracks` | Daily location occupancy by location. |
| `Labor Allocation` | LNs worked by team and date. |
| `Moves Per Day` | Successful AP moves by date and LN. |
| `Daily AP Status` | End-of-day AP state and remaining BTG. |
| `Exit Summary` | Delivery timing, planned B1R comparison, and time in system. |
| `Active AP Status` | Active APs remaining at termination and their queue blockers. |
| `KPI Summary` | High-level schedule and labor KPIs. |
| `Team KPIs` | Team-level BTG and workday KPIs. |
| `BTG structure` | Daily structure BTG completion by LN. |
| `BTG systems` | Daily systems BTG completion by LN. |
| `BTG declam` | Daily declam BTG completion by LN. |
| `BTG test` | Daily test BTG completion by LN. |

---

## How to Run

1. Clone the repository.

   ```bash
   git clone <repo-url>
   cd BSC-FGI_Scheduler
   ```

2. Install required Python / Jupyter packages.

   ```bash
   pip install jupyter pandas numpy openpyxl matplotlib seaborn scikit-learn
   ```

   `scikit-learn` is only needed for `move_time_estimation.ipynb`.

3. Confirm the staged scheduler input exists:

   ```text
   data/staged/FGI_liveState.xlsx
   ```

4. If raw workbooks or import assumptions changed, run:

   ```text
   data_import.ipynb
   ```

5. Run:

   ```text
   BSC_FGI_Scheduler.ipynb
   ```

6. Review the final outputs:

   ```text
   output/scheduler_trace_output.xlsx
   output/monthly_btg_control_charts.png
   ```

7. If the move-time matrix needs to be rebuilt or recalibrated, run:

   ```text
   move_time_estimation.ipynb
   ```

   Then rerun `data_import.ipynb` so the updated calibrated matrix is copied into `data/staged/FGI_liveState.xlsx`, and rerun the scheduler notebook.

---

## Current Assumptions

- The full scheduler notebook loads staged scheduler input from `data/staged/FGI_liveState.xlsx`.
- Locations are only usable when their online-date logic marks them online.
- Lower location priority values are preferred before shorter move times.
- The move-time matrix must include finite move times for usable origin-destination pairs.
- Temporary `N##` locations are used only for centerline staging.
- Paint bay scheduling is controlled by the `BSC1` and `BSC2` paint schedule.
- Compass calibration uses `CR3`, with `CR1` and `CR2` clear as part of the completion condition.
- Labor teams reduce FGI BTG using shift staffing and CPJ assumptions.
- Delivery readiness is based on queue/task state being clear.
- Weekend days skip normal labor and movement processing in the current loop.
- Input naming consistency matters. Location names, line numbers, and matrix labels must match across files.

---

## Known Limitations / Work in Progress

- The repository is still being refined before final handoff.
- The current full notebook is the reliable run reference. A clean public notebook is planned but should be added after the current workflow is finalized.
- Forecast mode stops when all APs are delivered or when the forecast cap is reached.
- If the move queue blocks because there is no feasible destination, no finite move time, or no temporary staging location, the AP remains active and should be reviewed in `Active AP Status`.
- `data/raw/FGI_Staffing_By_Shift.xlsx` is present as a staffing reference file; the default import notebook currently uses notebook staffing assumptions unless explicitly changed.
- The move-time matrix needs to be regenerated or edited when locations, nodes, historical calibration data, or movement assumptions change.
- Centerline blocker staging moves are part of the move transaction but are not recorded as normal final moves.
- Data quality matters. Missing dates, mismatched LNs, or location names that do not match the move-time matrix can change the scheduler output.

---

## Development Notes

`BSC_FGI_Scheduler.ipynb` is the full development notebook. It includes the run conditions, scheduler workflow, object definitions, export logic, and supporting analysis cells.

`move_time_estimation.ipynb` is a supporting notebook. It is only needed when the move-time matrix needs to be rebuilt or recalibrated.

The main expected scheduler artifact is:

```text
output/scheduler_trace_output.xlsx
```

Debug exports, old workbooks, and diagnostic files should not be required for normal scheduler use.

