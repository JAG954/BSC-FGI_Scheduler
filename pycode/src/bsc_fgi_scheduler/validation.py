"""Lightweight validation helpers for scheduler outputs."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from bsc_fgi_scheduler.export import SCHEDULER_TRACE_SHEETS


def validate_no_temp_locations_active(fgi):
    return [ln for ln, ap in fgi.APs.items() if ap.Location is not None and getattr(ap.Location, "is_temp", False)]


def validate_exit_summary(delivery_df: pd.DataFrame):
    required = ["LN", "FA_RO_Date", "Planned_B1R_Date", "Actual_Exit_Date", "Time_In_System_Days", "Days_Late", "Final_Location"]
    missing = [col for col in required if col not in delivery_df.columns]
    return {"passed": len(missing) == 0, "missing_columns": missing}


def validate_required_sheets(workbook_path: str | Path, required_sheets=None):
    workbook_path = Path(workbook_path)
    required_sheets = SCHEDULER_TRACE_SHEETS if required_sheets is None else required_sheets
    sheets = pd.ExcelFile(workbook_path).sheet_names
    missing = [sheet for sheet in required_sheets if sheet not in sheets]
    return {"passed": len(missing) == 0, "missing_sheets": missing, "sheets": sheets}


def validate_run_outputs(result: dict):
    issues = []
    for output_file in result.get("output_files", []):
        path = Path(output_file)
        if not path.exists():
            issues.append(f"missing output: {path}")
        elif path.stat().st_size == 0:
            issues.append(f"empty output: {path}")
    if "delivery_df" in result:
        exit_validation = validate_exit_summary(result["delivery_df"])
        if not exit_validation["passed"]:
            issues.append(f"exit summary missing columns: {exit_validation['missing_columns']}")
    return {"passed": len(issues) == 0, "issues": issues}
