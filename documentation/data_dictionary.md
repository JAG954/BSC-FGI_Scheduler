# Data Dictionary

This file documents the main input, staged, and output workbooks used by the BSC FGI scheduling model. It is intended for handoff review and should be checked against the notebooks before changing workbook structure or column names.

## Data Flow

```text
data/raw/*.xlsx
+ data/staged/move_times/move_time_estimation.xlsx
-> notebooks/data_import.ipynb
-> data/staged/FGI_liveState.xlsx
-> notebooks/BSC_FGI_Scheduler.ipynb
-> output/scheduler_trace_output.xlsx
```

The current scheduler notebook reads:

- AP, location, and labor inputs from `data/staged/FGI_liveState.xlsx`
- calibrated move times from `data/staged/move_times/move_time_estimation.xlsx`
- paint schedule assignments from `data/raw/paint_schedules.xlsx`

`data/staged/` contains files prepared for direct algorithm input. `data/raw/` contains source workbooks used to rebuild or audit those staged inputs.

## Workbook Inventory

| Path | Role |
|---|---|
| `data/raw/FA_Status_FGI_Handoff.xlsx` | Raw aircraft status, FA rollout, BTG, tank closure, and P3 milestone source data. |
| `data/raw/FGI_Locations_wPriority.xlsx` | Raw location priority, ownership, tooling, and centerline / obstruction reference data. |
| `data/raw/Nodes.xlsx` | Node and adjacency source for movement routing. |
| `data/raw/Centerlines and Move Times Purdue.xlsx` | Historical move-time and centerline reference data used for move-time calibration. |
| `data/raw/paint_schedules.xlsx` | Paint schedule source workbook. |
| `data/raw/FGI_Staffing_By_Shift.xlsx` | Staffing reference workbook. |
| `data/staged/FGI_liveState.xlsx` | Staged AP, location, and labor workbook used by the scheduler. |
| `data/staged/move_times/location_move_times.xlsx` | Uncalibrated move-time output from the move-time notebook. |
| `data/staged/move_times/move_time_estimation.xlsx` | Calibrated move-time matrix used directly by the scheduler. |
| `output/scheduler_trace_output.xlsx` | Main schedule trace and KPI output workbook. |

## Raw Input Workbooks

### `data/raw/FA_Status_FGI_Handoff.xlsx`

| Sheet | Key fields | Notes |
|---|---|---|
| `FARO_Scorecard` | `LN`, `FA RO`, `FA RO to B1R`, `Total Counters`, `Total BTG`, `P0 BTG`, `P1 BTG`, `P2 BTG`, `P3 BTG`, `Engines BTG`, `Doors BTG`, `Test BTG`, `Tank Closure`, `Ceilings`, `Initial Tests Run`, `Zone Shakes`, `P3 Milestones` | Source AP-level handoff status. Some workbook columns are unnamed spacer or target columns and are not direct scheduler fields. |
| `Tank_Closure_Detail` | `LINE_NUMBER`, `Complete_Jobs`, `Total_Jobs`, `TankStatus` | Tank closure source fields. Meaning inferred: `TankStatus` is a completion or readiness indicator used during staged AP preparation. |
| `P3 Milestone Detail` | `P`, `Milestone`, `Completed_Jobs`, `STATUS (1 Complete, 0 Still Open)` | P3 milestone source detail. Meaning inferred: rows are converted into AP-level P3 completion fields. |

### `data/raw/FGI_Locations_wPriority.xlsx`

| Sheet | Key fields | Notes |
|---|---|---|
| `FA Priority` | `Future State Priority`, `Date Online`, `Location`, `Owner`, `Jacking`, `Wings`, `Tank Closure`, `Notes` | Raw location list and priority source. Meaning inferred: lower priority values are preferred by normal move selection. |
| `Matrix` | Location-labeled matrix columns | Reference matrix in the source workbook. Confirm usage in the notebooks before editing. |

### `data/raw/Nodes.xlsx`

| Sheet | Fields | Notes |
|---|---|---|
| `Node` | `node_id`, `x`, `y`, `type`, `req_centerline` | Physical or logical node definitions used by route estimation. |
| `adjacency` | `from_node`, `to_node` | Allowed node connections used to build the movement graph. |

### `data/raw/Centerlines and Move Times Purdue.xlsx`

| Sheet | Fields | Notes |
|---|---|---|
| `Move Times` | `Date`, `AP`, `Starting Position`, `Move Time`, `Centerline`, `Down Time`, `Ending Position`, `H/O`, `RFO` | Historical move records used for calibration. Duplicate `Move Time`, `H/O`, and `RFO` labels appear in the source workbook. |
| `Centerlines` | `Position`, `Centerlines Required` | Centerline requirement reference. |

### `data/raw/paint_schedules.xlsx`

| Sheet | Fields | Notes |
|---|---|---|
| `Historical` | `Date`, `BSC1`, `BSC2` | Scheduler paint input. `BSC1` and `BSC2` contain AP / line-number assignments by date. |
| `Rate_10`, `Rate_12`, `Rate_14`, `Rate_20` | No populated fields in the checked-in workbook | Scenario sheets are present but empty in the inspected baseline workbook. |

### `data/raw/FGI_Staffing_By_Shift.xlsx`

| Sheet | Fields | Notes |
|---|---|---|
| `FGI Headcount Buckets` | `Shift/Skill` and shift / staffing bucket columns | Staffing reference workbook. The active scheduler assumptions should be verified in the notebooks before changing this file. |

## Staged Scheduler Inputs

### `data/staged/FGI_liveState.xlsx`

The checked-in baseline workbook contains these sheets: `ap_data`, `location_data`, and `labor_data`.

#### `ap_data`

| Field | Meaning |
|---|---|
| `LN` | Aircraft / AP line number. |
| `FA RO` | FA rollout date. |
| `FA RO to B1R` | Planned elapsed days from FA rollout to B1R. Meaning inferred from field name and output comparisons. |
| `Total Counters` | Counter total from source data. Meaning should be verified before changing task logic. |
| `TankStatus` | Tank closure status indicator from source detail. |
| `Ceilings` | Ceiling work status or count. Meaning inferred from source workbook. |
| `Initial Tests Run` | Initial test status or count. Meaning inferred from source workbook. |
| `BTG_tot` | Total BTG remaining or represented for the AP. |
| `BTG_p0`, `BTG_p1`, `BTG_p2`, `BTG_p3` | Source BTG categories by phase / priority bucket. |
| `BTG_engines`, `BTG_doors`, `BTG_test` | Source BTG categories for engines, doors, and test. |
| `P3_Engine Hang` | P3 engine hang completion indicator. |
| `P3_Flight Controls` | P3 flight controls completion indicator. |
| `P3_Gear Swing` | P3 gear swing completion indicator. |
| `P3_Medium Pressure Test` | P3 medium pressure test completion indicator. |
| `P3_Oil On` | P3 oil-on completion indicator. |
| `P3_Power On` | P3 power-on completion indicator. |
| `P3_Engine_Type` | Engine type or engine-related P3 category. Meaning inferred from field name. |
| `P3_Milestone_Completion_Percentage` | Percent completion of tracked P3 milestones. |
| `shakes_complete` | Shake completion indicator. |
| `shakes_req` | Shake requirement indicator. |

#### `location_data`

| Field | Meaning |
|---|---|
| `Location` | Scheduler location name. Must match move-time matrix labels. |
| `Future State Priority` | Location priority used by normal move candidate ordering. Lower values are preferred. |
| `Date Online` | Date or flag used to determine when the location is available. |
| `Owner` | Owning group or responsibility label. |
| `tooling_jacking` | Jacking tooling availability flag. |
| `tooling_wings` | Wings tooling availability flag. |
| `tooling_tankClosure` | Tank-closure tooling availability flag. |
| `centerline_dependencies` | Centerline dependencies that may force staging moves. |
| `obstructions` | Obstruction reference for the location. Meaning inferred from source notes. |
| `notes` | Free-form location notes. |

No standalone `canPlace` field is present in the checked-in staged workbook. Placement feasibility is derived in notebook logic from location availability, occupancy, move feasibility, and related constraints.

#### `labor_data`

| Field | Meaning |
|---|---|
| `category` | Labor assumption category, such as staffing or conversion parameters. |
| `shift` | Shift label. |
| `team` | FGI team, such as `structure`, `systems`, `declam`, or `test`. |
| `value` | Numeric assumption value for the category / shift / team row. |

### `data/staged/move_times/location_move_times.xlsx`

| Sheet | Fields | Notes |
|---|---|---|
| `location_move_times` | `from_loc` plus destination-location columns such as `A1`, `BSC1`, `CR3`, `P3SW`, `FGI1` | Uncalibrated move-time matrix generated by `notebooks/move_time_estimation.ipynb`. |
| `distance_matrix` | `from_loc` plus destination-location columns | Distance matrix supporting the uncalibrated move-time output. |

### `data/staged/move_times/move_time_estimation.xlsx`

| Sheet | Fields | Notes |
|---|---|---|
| `location_move_times` | `from_loc` plus destination-location columns | Calibrated origin-destination move-time matrix used directly by the scheduler. Values are expected to be numeric where moves are feasible. |

## Output Workbook

### `output/scheduler_trace_output.xlsx`

| Sheet | Key fields | Contents |
|---|---|---|
| `ChickenTracks` | `Date` plus location columns such as `D1`, `A1`, `CR3`, `BSC1`, `P3SW`, `FGI1`, `N40` | Daily location occupancy trace. |
| `Labor Allocation` | `Date`, `structure`, `systems`, `declam`, `test` | Daily AP assignments by labor team. |
| `Moves Per Day` | `Date` plus LN columns | Successful AP movement trace. Values identify recorded destinations / move outcomes by LN. |
| `Daily AP Status` | `Date`, `LN`, `Location`, `FGI_tot`, `structure`, `systems`, `declam`, `test`, `moveReq` | End-of-day AP state and remaining BTG by team. |
| `Exit Summary` | `LN`, `FA_RO_Date`, `Planned_B1R_Date`, `Actual_Exit_Date`, `Time_In_System_Days`, `Days_Late`, `Final_Location` | AP-level exit timing and final location summary. |
| `Active AP Status` | `LN`, `Location`, `Task_State`, `Move_Req`, `Destination`, `Queues`, `Queue_Count`, `FGI_structure`, `FGI_systems`, `FGI_declam`, `FGI_test`, `Compass_Complete`, `Paint_Complete` | APs still active at termination and their remaining blockers. Empty data rows mean no active APs were left. |
| `KPI Summary` | `KPI`, `Value`, `Definition` | Run-level delivery, active AP, time-in-system, movement, and labor metrics. |
| `Team KPIs` | `Team`, `AP_Count_Worked`, `Total_BTG_Completed`, `Average_Days_Worked_Per_AP`, `Max_Days_Worked_On_One_AP`, `Average_BTG_Per_Workday` | Team-level labor and BTG metrics. |
| `BTG structure` | `Date` plus LN columns | Daily structure BTG completion by AP. |
| `BTG systems` | `Date` plus LN columns | Daily systems BTG completion by AP. |
| `BTG declam` | `Date` plus LN columns | Daily declam BTG completion by AP. |
| `BTG test` | `Date` plus LN columns | Daily test BTG completion by AP. |

## Edit Guidance

- Keep `data/raw/` and `data/staged/` terminology. `data/staged/` files are active algorithm inputs, not final deliverables.
- Do not rename sheets or columns without updating the notebooks that read them.
- Keep `output/scheduler_trace_output.xlsx` visible in the repository when reference outputs are intended for review.
- Treat inferred field meanings as handoff notes, not legal or production definitions.
