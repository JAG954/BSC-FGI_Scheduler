"""Higher-rate simulation utilities for detected R## input workbooks."""

from __future__ import annotations

import datetime as dt
import json
import re
import traceback
from pathlib import Path

import pandas as pd

from bsc_fgi_scheduler.control_charts import generate_monthly_btg_control_charts
from bsc_fgi_scheduler.data_import import build_live_state_workbook
from bsc_fgi_scheduler.export import export_summary
from bsc_fgi_scheduler.paths import DATA_SIMULATED_DIR, OUTPUT_DIR, PROJECT_ROOT
from bsc_fgi_scheduler.scheduler import run_scheduler
from bsc_fgi_scheduler.validation import validate_run_outputs

SIM_STARTDATE = "2026-04-01"
SIM_ENDDATE = "2028-06-30"
SIM_FORECAST_CAP_DAYS = 365


def find_rate_files(simulated_dir: str | Path | None = None) -> dict[str, Path]:
    simulated_dir = DATA_SIMULATED_DIR if simulated_dir is None else Path(simulated_dir)
    rate_files = {}
    for fp in sorted(simulated_dir.glob("FA_Status_FGI_Handoff_R*.xlsx")):
        match = re.search(r"_R(\d+)\.xlsx$", fp.name)
        if match:
            rate_files[f"R{match.group(1)}"] = fp
    return rate_files


def _extract_kpi_metrics(trace_path: Path) -> dict:
    metrics = {}
    if not trace_path.exists():
        return metrics
    try:
        xf = pd.ExcelFile(trace_path, engine="openpyxl")
        if "Exit Summary" in xf.sheet_names:
            exits = pd.read_excel(xf, sheet_name="Exit Summary")
            if len(exits) > 0:
                if "Time_In_System_Days" in exits.columns:
                    metrics["avg_time_in_system_days"] = round(exits["Time_In_System_Days"].mean(), 1)
                if "Days_Late" in exits.columns:
                    metrics["avg_days_late"] = round(exits["Days_Late"].mean(), 1)
                metrics["delivered_ap_count"] = len(exits)
    except Exception as exc:
        metrics["kpi_parse_error"] = str(exc)
    return metrics


def run_one_rate(rate_id: str, simulated_file: str | Path, output_root: str | Path | None = None) -> dict:
    simulated_file = Path(simulated_file)
    output_root = OUTPUT_DIR / "rate simulation" if output_root is None else Path(output_root)
    rate_dir = output_root / rate_id
    scheduler_dir = rate_dir / "scheduler_outputs"
    chart_dir = rate_dir / "control_charts"
    log_dir = rate_dir / "logs"
    for directory in [scheduler_dir, chart_dir, log_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    live_state_path = scheduler_dir / "FGI_liveState.xlsx"
    start_time = dt.datetime.now()
    status = "success"
    error_msg = None
    output_files = []

    try:
        build_live_state_workbook(fa_status_path=simulated_file, output_path=live_state_path, simulated=True)
        result = run_scheduler(
            live_state_path=live_state_path,
            output_dir=scheduler_dir,
            config={
                "STARTDATE": SIM_STARTDATE,
                "ENDDATE": SIM_ENDDATE,
                "FORECAST_UNTIL_COMPLETION": True,
                "FORECAST_CAP_DAYS": SIM_FORECAST_CAP_DAYS,
                "CODECELL_OUTPUT": False,
            },
            export=True,
        )
        output_files.extend(result["output_files"])
        chart_path = generate_monthly_btg_control_charts(
            trace_file=scheduler_dir / "scheduler_trace_output.xlsx",
            output_path=chart_dir / "monthly_btg_control_charts.png",
        )
        output_files.append(chart_path)
        validation = validate_run_outputs(result)
    except Exception as exc:
        status = "fail"
        error_msg = str(exc)
        validation = {"passed": False, "issues": [str(exc)]}
        traceback.print_exc()

    end_time = dt.datetime.now()
    duration = round((end_time - start_time).total_seconds(), 1)
    trace_path = scheduler_dir / "scheduler_trace_output.xlsx"
    kpi = _extract_kpi_metrics(trace_path)
    run_log = {
        "rate_id": rate_id,
        "input_file": str(simulated_file),
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "duration_seconds": duration,
        "status": status,
        "error": error_msg,
        "output_files": [str(Path(path)) for path in output_files],
        "validation": validation,
        "kpi_metrics": kpi,
    }
    log_path = log_dir / "run_log.json"
    log_path.write_text(json.dumps(run_log, indent=2, default=str))

    return {
        "rate_id": rate_id,
        "input_file": simulated_file.name,
        "status": status,
        "scheduler_output_folder": str(scheduler_dir),
        "control_chart_folder": str(chart_dir),
        "num_output_files": len(output_files),
        "error_message": error_msg,
        "duration_seconds": duration,
        "delivered_ap_count": kpi.get("delivered_ap_count", ""),
        "avg_time_in_system_days": kpi.get("avg_time_in_system_days", ""),
        "avg_days_late": kpi.get("avg_days_late", ""),
        "validation_passed": validation["passed"],
        "validation_issues": "; ".join(validation["issues"]) if validation["issues"] else "",
    }


def run_rate_simulations(simulated_dir: str | Path | None = None, output_root: str | Path | None = None, rates=None):
    output_root = OUTPUT_DIR / "rate simulation" if output_root is None else Path(output_root)
    rate_files = find_rate_files(simulated_dir)
    if rates is not None:
        wanted = {str(rate).upper() for rate in rates}
        rate_files = {rate: path for rate, path in rate_files.items() if rate.upper() in wanted}
    output_root.mkdir(parents=True, exist_ok=True)
    summary_rows = [run_one_rate(rate_id, simulated_file, output_root=output_root) for rate_id, simulated_file in rate_files.items()]
    summary_df = pd.DataFrame(summary_rows)
    summary_path = output_root / "rate_simulation_summary.xlsx"
    export_summary(summary_df, summary_path)
    return summary_df, summary_path


if __name__ == "__main__":
    summary, summary_path = run_rate_simulations()
    print(summary_path)
    print(summary)
