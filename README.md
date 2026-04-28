# BSC-FGI Scheduler

## Overview

This repository contains a scheduling and trace-output workflow for modeling aircraft progression after Final Assembly rollout into BSC FGI / parking operations.

The scheduler tracks aircraft position, location occupancy, centerline constraints, paint bay assignments, compass calibration, labor-driven BTG completion, queue-based delivery readiness, and Excel-based schedule outputs. The goal is to create a readable planning model that can show how aircraft move through FGI, where capacity gets constrained, and how labor and location availability affect delivery timing.

The main workflow is implemented in:

```text
BSC_FGI_Scheduler.ipynb
```

A cleaner public-facing notebook is planned, but the current full notebook is the authoritative run reference.

---

## Current Repository Status

This repository is still a work in progress. The current version is being prepared for review and will continue to be modified before the final project handoff next Tuesday.

The current notebook is functional enough to represent the project structure, scheduler design, major data inputs, and trace-output workflow. However, several areas are still being refined before final handoff:

- Exit logic is still being debugged and formatted. The intended delivery condition is queue absence, but final validation and output formatting are still in progress.
- Control chart generation is still being refined. The goal is to generate clean monthly BTG control charts and related visual summaries from either the scheduler output workbook or the notebook’s trace data.
- KPI formatting is still being finalized, including average days in system, average days late, average days worked by each labor team, and final active-AP blocker reporting.
- The clean public notebook has not been added yet. The current full notebook should be treated as the working reference.
- Some supporting output files are previous-run artifacts and may be cleaned, renamed, or reorganized before the final handoff.

After this README is added, the README should be updated at each main-branch commit that changes scheduler behavior, input assumptions, output workbook structure, or repository organization.

---

## Project Purpose

The scheduler was built to test how aircraft move through FGI after Final Assembly rollout and to make that process easier to inspect through traceable daily outputs.

The model is designed around a few core questions:

- Where is each aircraft located each day?
- Which aircraft are waiting on paint, compass calibration, or BTG completion?
- Which moves are feasible given location occupancy and centerline constraints?
- How does labor capacity affect daily BTG completion?
- When is an aircraft ready to leave the active FGI system?
- Where do bottlenecks appear when paint bays, compass locations, or parking locations fill up?

The notebook is intentionally object-based so that aircraft, locations, queues, moves, and outputs are all traceable through the scheduler state.

---

## Repository Structure

```text
BSC-FGI_Scheduler/
|-- BSC_FGI_Scheduler.ipynb
|-- move_time_estimation.ipynb
|-- FGI_liveState.xlsx
|-- scheduler_trace_output.xlsx
|-- input/
|   |-- Centerlines and Move Times Purdue.xlsx
|   |-- FA_Status_FGI_Handoff.xlsx
|   |-- FGI_Locations_wPriority.xlsx
|   |-- FGI_Staffing_By_Shift.xlsx
|   |-- Nodes.xlsx
|   |-- adjusted_location_move_times.xlsx
|   |-- location_move_times.xlsx
|   |-- move_time_estimation.xlsx
|   `-- paint_schedules.xlsx
|-- output/
|   |-- FGI_liveState.xlsx
|   |-- location_move_times.xlsx
|   |-- location_move_times_calibrated.xlsx
|   |-- location_move_times_linear_calibrated.xlsx
|   |-- monthly_btg_control_charts.png
|   |-- move_time_estimation.xlsx
|   `-- scheduler_trace_output.xlsx
|-- schedule/
|-- templates/
`-- README.md
```

The root-level `FGI_liveState.xlsx` is used by the current notebook when:

```python
INPUT_TYPE = 'FGI_LIVESTATE'
```

The notebook currently exports the main trace workbook to:

```text
output/scheduler_trace_output.xlsx
```

The root-level `scheduler_trace_output.xlsx` appears to be a previous exported workbook and should be treated as a reference artifact rather than the active export path.

---

## Main Notebook Workflow

The scheduler notebook follows this general sequence:

1. Set local paths, input files, run dates, forecast behavior, and export settings.
2. Load AP, location, labor, move-time, and paint-schedule data.
3. Initialize the core `AP`, `Location`, `FGI`, and `FGITrace` objects.
4. Add locations, active aircraft, move-time dictionaries, queues, and trace tracking to the scheduler.
5. Run a day-by-day simulation from `STARTDATE` to `ENDDATE`, with optional forecast continuation.
6. Roll APs into FGI when their FA rollout date is reached.
7. Apply shift-based labor capacity to structure, systems, declam, and test BTG.
8. Schedule paint moves and compass moves.
9. Process feasible moves during the move window.
10. Check end-of-day delivery readiness.
11. Record daily AP status and trace state.
12. Export the trace workbook, status tables, delivery information, and KPI summaries.

Weekend logic is handled separately in the current loop. When `today.weekday() >= 5`, normal labor and movement work are skipped.

---

## Input Modes

The notebook currently supports two input modes.

### 1. `FGI_LIVESTATE`

This is the current default run mode.

It reads:

```text
FGI_liveState.xlsx
```

from the repository root. That workbook is expected to include:

- `ap_data`
- `location_data`
- `labor_data`

This mode is useful when the scheduler should start from a known live or saved state instead of rebuilding all AP/location data from raw source files.

### 2. `FARO_SCORECARD_WITH_MILESTONES`

This mode builds AP and location inputs from the raw source workbooks in `input/`, including FARO, milestone, location, and move-time files.

---

## Important Input Files

| File | Purpose | Used by |
|---|---|---|
| `FGI_liveState.xlsx` | Root-level live-state workbook used by the current default input mode. | Main scheduler notebook when `INPUT_TYPE = 'FGI_LIVESTATE'`. |
| `input/FA_Status_FGI_Handoff.xlsx` | Raw AP / FARO status input. | `FARO_SCORECARD_WITH_MILESTONES` input path. |
| `input/FGI_Locations_wPriority.xlsx` | Location priority, online timing, and capability reference. | Location dataframe builder. |
| `input/Nodes.xlsx` | Node and adjacency input for location movement modeling. | Move-time estimation workflow. |
| `input/move_time_estimation.xlsx` | Current scheduler move-time matrix. | `load_move_times()` in the main scheduler notebook. |
| `input/paint_schedules.xlsx` | Paint bay schedule for `BSC1` and `BSC2`. | `load_paint_schedule()`. |
| `input/location_move_times.xlsx` | Supporting/generated move-time workbook. | Reference / supporting output. |
| `input/adjusted_location_move_times.xlsx` | Adjusted move-time matrix. | Supporting file; not the current default scheduler input. |
| `input/Centerlines and Move Times Purdue.xlsx` | Historical move-time and centerline reference data. | `move_time_estimation.ipynb`. |
| `input/FGI_Staffing_By_Shift.xlsx` | Staffing reference workbook. | Present as a reference file; current notebook uses hardcoded or live-state labor values. |

---

## Move-Time Logic

The scheduler uses a location-to-location move-time matrix. The current default matrix file is:

```text
input/move_time_estimation.xlsx
```

`load_move_times()` reads the move-time matrix with `from_loc` as the index. Row labels and column labels are converted to strings, values are coerced to numeric, and the matrix is stored as a nested dictionary.

The scheduler then attaches move times to each `Location` object through:

```python
Location.time_to
```

A move destination is only feasible if:

- the destination exists in `fgi.Locations`
- the destination is online
- the destination is empty
- the origin-to-destination move time is finite
- the destination is not a temporary staging location during normal move selection

When an AP needs a move and does not have a fixed destination, `AP.get_move_candidates()` builds feasible destinations and sorts them by:

1. lower location priority value
2. lower move time

Lower priority values are treated as higher-priority destinations.

---

## Temporary Locations and Centerline Constraints

Temporary `N##` locations are staging locations, not normal parking locations.

Any location whose name starts with `N` is treated as temporary through the location object. These locations should not be selected as normal final destinations. They are only used when a centerline-constrained move requires another AP to be temporarily cleared out of the way.

The intended centerline move sequence is:

1. Move the blocking AP to an available temporary `N##` location.
2. Move the target AP into its destination.
3. Move the blocking AP back to its original location.

The temporary blocker moves are not recorded as normal final moves in the trace output. The target AP move is recorded.

Centerline dependencies are stored on:

```python
Location.centerlines
```

If a destination has occupied centerline dependencies, `move_ap_with_centerline()` handles the temporary staging transaction.

---

## Move-Time Estimation Notebook

`move_time_estimation.ipynb` supports the scheduler by building and calibrating the move-time matrix.

It currently:

- loads nodes and adjacency from `input/Nodes.xlsx`
- builds a movement graph
- applies shortest-path logic to estimate route distance
- converts distance to modeled move time using a 3 mph assumption
- exports `output/location_move_times.xlsx`
- loads historical moves from `input/Centerlines and Move Times Purdue.xlsx`
- removes historical centerline moves from the calibration set
- fits a linear calibration model using `sklearn.linear_model.LinearRegression`
- exports the calibrated scheduler matrix to `input/move_time_estimation.xlsx`

The scheduler reads that calibrated file by default.

---

## Core Scheduler Objects

### `AP`

Represents one aircraft / line number.

The object stores:

- LN
- FA rollout date
- planned days to B1R
- raw counters and BTG values
- FGI BTG buckets
- P3 milestone fields
- shake / test-related status
- current location
- task state
- move request state
- destination
- task completion flags

It also converts raw BTG into FGI labor categories for:

- structure
- systems
- declam
- test

### `Location`

Represents a physical or temporary scheduler location.

The object stores:

- location name
- priority
- online status
- owner / capability fields
- centerline dependencies
- current AP occupancy
- schedule history
- temporary-location flag
- move times to other locations

### `FGI`

Owns the active scheduler state.

The object manages:

- active APs
- locations
- move queue
- paint queue
- compass queue
- labor queues
- AP movement
- centerline movement
- paint scheduling
- compass scheduling
- labor assignment
- delivery readiness
- daily status rows
- delivery rows
- KPI tables

The main loop is intentionally routed through `FGI` methods so that state changes stay centralized.

### `FGITrace`

Records scheduler trace output while the notebook runs.

It stores:

- daily location occupancy
- labor allocation
- successful moves
- BTG completion by team

At export time, these trace dictionaries are converted into dataframes and written to Excel.

---

## Queue and Task Logic

The scheduler uses queues to represent work that still needs to happen.

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

Labor capacity is applied by shift. The notebook converts available manhours into BTG completion using `FGI_CPJ`, then works APs in queue order. Once a team’s BTG reaches zero for an AP, that AP is removed from that team’s labor queue.

---

## Paint Logic

Paint scheduling looks ahead to the next day’s paint schedule.

If an AP is scheduled for `BSC1` or `BSC2`, it receives a fixed destination move request for that bay.

If a paint bay is currently occupied by a different AP, the current occupant is queued to move out before the scheduled AP can move in.

Paint is considered complete when an AP moves out of `BSC1` or `BSC2`, not when it moves into the bay. This keeps the AP in the paint queue while it is still occupying the paint bay.

---

## Compass Logic

Compass calibration is centered on `CR3`.

When an AP moves into `CR3`, it receives a compass start date. It remains in the compass queue while it is occupying `CR3`.

Compass is considered complete only after:

- the AP has occupied `CR3` for at least one workday, and
- `CR1` and `CR2` are unoccupied on that qualifying workday

After compass completion, the AP is moved out of `CR3` to the closest feasible normal destination. If another AP is waiting for compass, `CR1` and `CR2` are avoided as move-away destinations unless there is no other feasible option.

---

## Delivery Logic

Delivery readiness is based on queue absence, not only on the planned B1R date.

At the end of each simulated day, an AP can leave active FGI only if:

- it is not in the move queue
- it is not in the paint queue
- it is not in the compass queue
- it is not in any labor queue
- `moveReq` is false
- no destination is still assigned

When those blockers are clear, `complete_AP()` records the delivery row, removes the AP from active FGI, clears its location, and removes it from all queues defensively.

`toB1R` is used for timing comparison and KPI reporting, not as the direct delivery condition.

---

## Output Files

| Output | Description |
|---|---|
| `output/scheduler_trace_output.xlsx` | Main scheduler trace and KPI workbook. |
| `output/FGI_liveState.xlsx` | Optional exported live-state workbook when `EXPORT_TO_FGI_LIVESTATE = True`. |
| `output/location_move_times.xlsx` | Move-time estimator output before calibration. |
| `input/move_time_estimation.xlsx` | Calibrated move-time matrix used by the scheduler. |
| `output/monthly_btg_control_charts.png` | Optional monthly BTG control chart image from supporting analysis. |

---

## Main Trace Workbook

The main scheduler export is:

```text
output/scheduler_trace_output.xlsx
```

Expected sheets include:

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

## KPI Outputs

`KPI Summary` includes:

- delivered AP count
- active AP count at termination
- average days in system
- average days late
- active APs with no queue membership
- average located APs per day
- total successful moves recorded
- average days worked by each team
- total BTG completed by each team

`Team KPIs` includes:

- team name
- AP count worked
- total BTG completed
- average days worked per AP
- max days worked on one AP
- average BTG per workday

---

## Current Bugs / Metrics Being Refined

The following items are still being worked before final handoff:

| Area | Current status |
|---|---|
| Exit logic | Queue-based exit logic is implemented conceptually, but still needs final debugging, validation, and cleaner formatting in output sheets. |
| Control chart generation | Monthly BTG control chart generation exists as a supporting output but still needs final integration and formatting. |
| KPI formatting | KPI sheets need final formatting and validation so average days in system, average days late, and team workday metrics are easier to interpret. |
| Active AP status | Remaining active AP blockers are being refined so the output clearly distinguishes capacity limits, queue blockers, and unfinished task states. |
| Clean notebook | A public-facing clean notebook will be generated after the current full notebook is finalized. |
| Output cleanup | Old or supporting output files may be reorganized so the repo presents one clear run path. |

---

## How to Run

1. Clone the repository.

   ```bash
   git clone <repo-url>
   cd BSC-FGI_Scheduler
   ```

2. Install required Python / Jupyter packages.

   There is no `requirements.txt` in the repo right now. The main packages used are:

   ```bash
   pip install jupyter pandas numpy openpyxl matplotlib seaborn scikit-learn
   ```

   `scikit-learn` is only needed for `move_time_estimation.ipynb`.

3. Confirm input files are present.

   The scheduler currently expects the main input workbooks in `input/`, and the default live-state workbook at the repo root:

   ```text
   FGI_liveState.xlsx
   input/move_time_estimation.xlsx
   input/paint_schedules.xlsx
   ```

4. Open:

   ```text
   BSC_FGI_Scheduler.ipynb
   ```

5. Set local paths in the user path / root path cell.

   If needed, update `rootpath` so it points to the cloned repository.

6. Review the main run settings:

   ```python
   STARTDATE
   ENDDATE
   FORECAST_UNTIL_COMPLETION
   INPUT_TYPE
   EXPORT_PATH
   EXPORT_TO_FGI_LIVESTATE
   ```

7. Run the notebook top to bottom.

8. Review the main output workbook:

   ```text
   output/scheduler_trace_output.xlsx
   ```

9. If the move-time matrix needs to be rebuilt, run:

   ```text
   move_time_estimation.ipynb
   ```

   Then rerun the scheduler notebook.

---

## Current Assumptions

- The full scheduler notebook currently defaults to live-state input through `FGI_liveState.xlsx`.
- Locations are only usable when their online-date logic marks them online.
- Lower location priority values are preferred before shorter move times.
- The move-time matrix must include finite move times for usable origin-destination pairs.
- Temporary `N##` locations are used only for centerline staging.
- Centerline blockers may be staged into `N##` locations temporarily, then returned.
- Paint bay scheduling is controlled by the `BSC1` and `BSC2` paint schedule.
- Compass calibration uses `CR3`, with `CR1` and `CR2` clear as part of the completion condition.
- Labor teams reduce FGI BTG using shift staffing and CPJ assumptions.
- Delivery readiness is based on queue/task state being clear.
- Weekend days skip normal labor and movement processing in the current loop.
- Input naming consistency matters. Location names, line numbers, and matrix labels must match across files.

---

## Known Limitations / Work in Progress

- The repository is still being refined before final handoff next Tuesday.
- The current full notebook is the reliable run reference. A clean public notebook is planned but should be added after the current workflow is finalized.
- Forecast mode stops when all APs are delivered or when the forecast cap is reached.
- If the move queue blocks because there is no feasible destination, no finite move time, or no temporary staging location, the AP remains active and should be reviewed in `Active AP Status`.
- `FGI_Staffing_By_Shift.xlsx` is present but not directly wired into the current default scheduler run.
- `adjusted_location_move_times.xlsx` and several existing output move-time files are supporting or previous-run artifacts, not the active scheduler input.
- The move-time matrix needs to be regenerated or edited when locations, nodes, or movement assumptions change.
- Centerline blocker staging moves are part of the move transaction but are not recorded as normal final moves.
- Input data quality matters. Missing dates, mismatched LNs, or location names that do not match the move-time matrix can change the scheduler output.
- This README will be updated after each main-branch commit that changes model logic, inputs, outputs, or repo structure.

---

## Development Notes

`BSC_FGI_Scheduler.ipynb` is the full development notebook. It includes the run conditions, scheduler workflow, object definitions, export logic, and supporting analysis cells.

`move_time_estimation.ipynb` is a supporting notebook. It is only needed when the move-time matrix needs to be rebuilt or recalibrated.

The main expected scheduler artifact is:

```text
output/scheduler_trace_output.xlsx
```

Debug exports, old workbooks, and diagnostic files should not be required for normal scheduler use.

---

## Context Note

This README describes the repository at the capstone scheduling and parking-optimization level. It intentionally stays at the workflow, object-model, and data-interface level and avoids adding operational detail beyond the project context and files already present in the repository.
