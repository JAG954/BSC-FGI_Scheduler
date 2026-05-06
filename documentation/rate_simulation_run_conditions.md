# Rate Simulation Run Conditions

## Purpose

This document records the run conditions used by the higher-rate simulation workflow in the submitted repository state.

The rate simulation workflow is implemented in:

```text
pycode/src/bsc_fgi_scheduler/rate_simulations.py
```

The workflow detects simulated higher-rate input workbooks, converts each one into a staged live-state workbook, runs the scheduler, exports scheduler outputs, generates monthly BTG control charts, and writes run logs.

## Simulated Input Files

The submitted repository contains the following simulated input workbooks:

```text
data/simulated/FA_Status_FGI_Handoff_R10.xlsx
data/simulated/FA_Status_FGI_Handoff_R12.xlsx
data/simulated/FA_Status_FGI_Handoff_R14.xlsx
data/simulated/FA_Status_FGI_Handoff_R20.xlsx
```

The runner detects files matching:

```text
data/simulated/FA_Status_FGI_Handoff_R*.xlsx
```

The `R##` value in each filename becomes the scenario identifier.

| Input file | Scenario ID |
|---|---|
| `FA_Status_FGI_Handoff_R10.xlsx` | `R10` |
| `FA_Status_FGI_Handoff_R12.xlsx` | `R12` |
| `FA_Status_FGI_Handoff_R14.xlsx` | `R14` |
| `FA_Status_FGI_Handoff_R20.xlsx` | `R20` |

## Run Conditions Used

The current rate simulation runner uses these constants:

| Setting | Value |
|---|---|
| `SIM_STARTDATE` | `2026-04-01` |
| `SIM_ENDDATE` | `2028-06-30` |
| `SIM_FORECAST_CAP_DAYS` | `365` |

Each scheduler run is called with this configuration:

```python
config={
    "STARTDATE": "2026-04-01",
    "ENDDATE": "2028-06-30",
    "FORECAST_UNTIL_COMPLETION": True,
    "FORECAST_CAP_DAYS": 365,
    "CODECELL_OUTPUT": False,
}
```

The scheduler export flag is enabled:

```python
export=True
```

## Scenario Execution Sequence

For each detected rate scenario, the runner performs this sequence:

1. Creates the scenario output folders.
2. Builds a live-state workbook from the simulated FA status input.
3. Runs the scheduler using the configured start date, end date, forecast behavior, and forecast cap.
4. Exports scheduler outputs.
5. Generates a monthly BTG control chart.
6. Validates the run outputs.
7. Writes a per-run JSON log.
8. Adds the scenario row to the top-level rate simulation summary.

## Output Structure

The runner writes each scenario under:

```text
output/rate simulation/R##/
```

Expected per-scenario structure:

```text
output/rate simulation/R##/
|-- scheduler_outputs/
|   |-- FGI_liveState.xlsx
|   `-- scheduler_trace_output.xlsx
|-- control_charts/
|   `-- monthly_btg_control_charts.png
`-- logs/
    `-- run_log.json
```

The runner also writes a top-level summary workbook when executed:

```text
output/rate simulation/rate_simulation_summary.xlsx
```

## Committed Simulation Outputs

The submitted repository contains committed output folders for:

```text
output/rate simulation/R10/
output/rate simulation/R12/
output/rate simulation/R14/
```

Each of those committed folders contains:

```text
scheduler_outputs/FGI_liveState.xlsx
scheduler_outputs/scheduler_trace_output.xlsx
control_charts/monthly_btg_control_charts.png
```

The repository contains an R20 simulated input file, but the submitted file set does not include a committed R20 output folder. Therefore, the submitted higher-rate simulation outputs should be interpreted as committed for R10, R12, and R14 only.

## Summary Metrics

When a scheduler trace workbook exists, the runner attempts to parse the `Exit Summary` sheet and extract:

| Metric | Meaning |
|---|---|
| `delivered_ap_count` | Number of delivered AP rows in `Exit Summary`. |
| `avg_time_in_system_days` | Mean of `Time_In_System_Days`. |
| `avg_days_late` | Mean of `Days_Late`. |

If KPI parsing fails, the parsing error is stored in the run log rather than stopping every scenario.

## Reproducibility Command

From the repository root, the rate simulation workflow can be executed with:

```bash
cd pycode
python -m bsc_fgi_scheduler.rate_simulations
```

This command runs all detected `R##` input files under `data/simulated/`.

## Interpretation Notes

The rate simulation outputs are scenario-specific outputs under the submitted run configuration. They should not be interpreted as universal production forecasts.

The outputs depend on:

- the specific simulated FA status workbook,
- the staged location and move-time assumptions,
- the scheduler logic in the submitted branch,
- the configured start date and end date,
- the enabled forecast continuation behavior,
- and the 365-day forecast cap.

The committed rate simulation outputs are reference artifacts for handoff review.
