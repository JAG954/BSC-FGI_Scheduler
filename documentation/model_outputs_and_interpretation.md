# Model Outputs and Interpretation

## Purpose

This document explains how to interpret the committed output artifacts in the submitted repository.

The outputs are included so reviewers can inspect the expected workbook structure, trace format, control chart format, and higher-rate scenario outputs.

## Baseline Output Files

The submitted repository includes these baseline output artifacts:

```text
output/scheduler_trace_output.xlsx
output/monthly_btg_control_charts.png
output/nodemap.png
```

## Main Scheduler Trace Workbook

The main baseline scheduler output workbook is:

```text
output/scheduler_trace_output.xlsx
```

The workbook is expected to contain scheduler trace and KPI sheets such as:

```text
ChickenTracks
Labor Allocation
Moves Per Day
Daily AP Status
Exit Summary
Active AP Status
KPI Summary
Team KPIs
BTG structure
BTG systems
BTG declam
BTG test
```

## Higher-Rate Simulation Outputs

Committed higher-rate output folders are present for:

```text
output/rate simulation/R10/
output/rate simulation/R12/
output/rate simulation/R14/
```

Each committed rate scenario folder includes:

```text
scheduler_outputs/FGI_liveState.xlsx
scheduler_outputs/scheduler_trace_output.xlsx
control_charts/monthly_btg_control_charts.png
```

The repository also contains:

```text
data/simulated/FA_Status_FGI_Handoff_R20.xlsx
```

but no committed `output/rate simulation/R20/` folder is included in the submitted repository state.

## Interpretation of Checked-In Outputs

The checked-in outputs are reference artifacts from the submitted model state. They are included for handoff review and reproducibility inspection.

They can be used to review:

- daily aircraft location traces,
- labor allocation output structure,
- move records,
- AP exit summaries,
- active AP status at termination,
- KPI table structure,
- team-level KPI structure,
- BTG completion traces,
- monthly BTG control chart format,
- and simulated-rate scenario output structure.

## Limitations

The outputs should not be interpreted as operational commitments or production forecasts.

The output values depend on:

- the submitted input workbooks,
- the staged live-state workbook,
- move-time assumptions,
- location availability assumptions,
- task logic,
- queue logic,
- labor assumptions,
- forecast settings,
- and the current scheduler implementation.

Before operational use, all assumptions and results would need validation against internal production data and current operating rules.
