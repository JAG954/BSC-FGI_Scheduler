"""Scheduler-output analysis and control chart generation."""

from __future__ import annotations

from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from bsc_fgi_scheduler.paths import OUTPUT_DIR

REQUIRED_ANALYSIS_SHEETS = [
    "ChickenTracks",
    "Daily AP Status",
    "Exit Summary",
    "Active AP Status",
    "BTG structure",
    "BTG systems",
    "BTG declam",
    "BTG test",
]


def load_scheduler_trace_workbook(trace_file: str | Path | None = None):
    trace_file = OUTPUT_DIR / "scheduler_trace_output.xlsx" if trace_file is None else Path(trace_file)
    if not trace_file.exists():
        raise FileNotFoundError(f"Missing scheduler trace workbook: {trace_file}")
    workbook = pd.ExcelFile(trace_file)
    missing_sheets = [sheet for sheet in REQUIRED_ANALYSIS_SHEETS if sheet not in workbook.sheet_names]
    if missing_sheets:
        raise ValueError(f"Missing required sheet(s) in {trace_file}: {missing_sheets}")
    return workbook


def build_daily_status_summaries(daily_status_df: pd.DataFrame, active_status_df: pd.DataFrame | None = None):
    btg_cols = ["FGI_tot", "structure", "systems", "declam", "test"]
    if daily_status_df.empty:
        return pd.DataFrame(), pd.DataFrame(), active_status_df if active_status_df is not None else pd.DataFrame()

    status = daily_status_df.copy()
    status["Date"] = pd.to_datetime(status["Date"], errors="coerce").dt.normalize()
    status = status.dropna(subset=["Date"])
    for col in btg_cols:
        if col in status.columns:
            status[col] = pd.to_numeric(status[col], errors="coerce").fillna(0)

    latest_status_date = status["Date"].max()
    latest_daily_ap_status = status[status["Date"] == latest_status_date].sort_values(["Location", "LN"]).reset_index(drop=True)
    summary_rows = [
        {"Metric": "Status date", "Value": latest_status_date.date()},
        {"Metric": "Active AP count", "Value": latest_daily_ap_status["LN"].nunique()},
        {"Metric": "Move required count", "Value": int(latest_daily_ap_status.get("moveReq", pd.Series(dtype=bool)).fillna(False).sum())},
    ]
    for col in btg_cols:
        if col in latest_daily_ap_status.columns:
            summary_rows.append({"Metric": f"Remaining {col}", "Value": latest_daily_ap_status[col].sum()})

    location_summary = (
        latest_daily_ap_status.groupby("Location", dropna=False)
        .agg(
            AP_Count=("LN", "nunique"),
            Move_Required=("moveReq", "sum"),
            Remaining_FGI_Tot=("FGI_tot", "sum"),
            Remaining_Structure=("structure", "sum"),
            Remaining_Systems=("systems", "sum"),
            Remaining_Declam=("declam", "sum"),
            Remaining_Test=("test", "sum"),
        )
        .reset_index()
        .sort_values(["AP_Count", "Location"], ascending=[False, True])
    )
    return pd.DataFrame(summary_rows), location_summary, latest_daily_ap_status


def generate_monthly_system_flow(trace_file: str | Path | None = None, output_path: str | Path | None = None, plot_start="2024-06-01", plot_end="2026-04-30"):
    trace_file = OUTPUT_DIR / "scheduler_trace_output.xlsx" if trace_file is None else Path(trace_file)
    output_path = OUTPUT_DIR / "monthly_system_flow.png" if output_path is None else Path(output_path)
    daily_status_df = pd.read_excel(trace_file, sheet_name="Daily AP Status")
    delivery_df = pd.read_excel(trace_file, sheet_name="Exit Summary")
    plot_start = pd.Timestamp(plot_start)
    plot_end = pd.Timestamp(plot_end)
    plot_months = pd.date_range(plot_start, plot_end, freq="MS")
    plot_days = pd.date_range(plot_start, plot_end, freq="D")

    if daily_status_df.empty:
        monthly_rollouts = pd.Series(0, index=plot_months, dtype="int64")
        aps_in_system = pd.Series(0, index=plot_days, dtype="int64")
    else:
        status = daily_status_df.copy()
        status["Date"] = pd.to_datetime(status["Date"], errors="coerce").dt.normalize()
        status = status.dropna(subset=["Date"])
        first_seen_dates = status.groupby("LN")["Date"].min()
        monthly_rollouts = first_seen_dates.dt.to_period("M").dt.to_timestamp().value_counts().sort_index().reindex(plot_months, fill_value=0)
        aps_in_system = status.groupby("Date")["LN"].nunique().sort_index().reindex(plot_days, fill_value=0)

    if len(delivery_df) > 0 and "Actual_Exit_Date" in delivery_df.columns:
        exit_dates = pd.to_datetime(delivery_df["Actual_Exit_Date"], errors="coerce").dropna().dt.normalize()
        monthly_exits = exit_dates.dt.to_period("M").dt.to_timestamp().value_counts().sort_index().reindex(plot_months, fill_value=0)
    else:
        monthly_exits = pd.Series(0, index=plot_months, dtype="int64")

    fig, ax1 = plt.subplots(figsize=(10, 5.5))
    ax1.bar(plot_months - pd.Timedelta(days=5), monthly_rollouts, width=9, color="royalblue", alpha=0.35, label="Monthly Rollouts")
    ax1.bar(plot_months + pd.Timedelta(days=5), monthly_exits, width=9, color="orange", alpha=0.35, label="Monthly Exits")
    ax1.set_title("Monthly System Flow", fontweight="bold")
    ax1.set_xlabel("Date", fontweight="bold")
    ax1.set_ylabel("Monthly Rollout / Exit Count", fontweight="bold")
    ax1.set_xlim(plot_start, plot_end)
    ax1.set_ylim(0, 8.4)
    ax1.set_yticks(range(0, 9, 1))
    ax1.grid(True, alpha=0.25)
    ax2 = ax1.twinx()
    ax2.plot(aps_in_system.index, aps_in_system, color="purple", alpha=0.7, linewidth=2, label="APs in System")
    ax2.set_ylabel("APs in System", fontweight="bold")
    ax2.set_ylim(-0.5, 11.5)
    ax2.set_yticks(range(0, 11, 2))
    ax1.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 4, 7, 10]))
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    lines_1, labels_1 = ax1.get_legend_handles_labels()
    lines_2, labels_2 = ax2.get_legend_handles_labels()
    ax1.legend(lines_1 + lines_2, labels_1 + labels_2, loc="upper left")
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return output_path


def generate_monthly_btg_control_charts(
    trace_file: str | Path | None = None,
    output_path: str | Path | None = None,
    selected_teams=None,
    control_window_months=36,
    control_start_month=None,
    control_end_month=None,
):
    trace_file = OUTPUT_DIR / "scheduler_trace_output.xlsx" if trace_file is None else Path(trace_file)
    output_path = OUTPUT_DIR / "monthly_btg_control_charts.png" if output_path is None else Path(output_path)
    selected_teams = ["total", "structure", "systems", "declam", "test"] if selected_teams is None else selected_teams
    btg_sheet_map = {"structure": "BTG structure", "systems": "BTG systems", "declam": "BTG declam", "test": "BTG test"}
    remaining_col_map = {"total": "FGI_tot", "structure": "structure", "systems": "systems", "declam": "declam", "test": "test"}

    def _monthly_completion_from_sheet(workbook_path, sheet_name):
        df = pd.read_excel(workbook_path, sheet_name=sheet_name)
        if len(df.columns) == 0:
            return pd.Series(dtype=float)
        date_col = "Date" if "Date" in df.columns else df.columns[0]
        df = df.copy()
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce").dt.normalize()
        df = df[df[date_col].notna()].reset_index(drop=True)
        value_cols = [col for col in df.columns if col != date_col]
        if len(value_cols) == 0:
            return pd.Series(dtype=float)
        daily = df.groupby(date_col)[value_cols].sum(numeric_only=True).sum(axis=1).sort_index()
        monthly = daily.groupby(pd.Grouper(freq="MS")).sum(min_count=1).fillna(0)
        monthly.index.name = "Month"
        return monthly

    def _monthly_remaining_from_sheet(workbook_path, sheet_name, value_col):
        df = pd.read_excel(workbook_path, sheet_name=sheet_name)
        if "Date" not in df.columns or value_col not in df.columns:
            return pd.Series(dtype=float)
        df = df.copy()
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.normalize()
        df[value_col] = pd.to_numeric(df[value_col], errors="coerce")
        df = df[df["Date"].notna()].reset_index(drop=True)
        daily = df.groupby("Date")[value_col].sum(min_count=1).sort_index()
        monthly = daily.groupby(pd.Grouper(freq="MS")).last()
        monthly.index.name = "Month"
        return monthly

    def _month_floor(value):
        return pd.Timestamp(value).to_period("M").to_timestamp()

    def _filter_month_window(series, months=None, start_month=None, end_month=None):
        if series is None or len(series) == 0:
            return series
        s = series.sort_index().copy()
        if start_month is not None or end_month is not None:
            start = _month_floor(start_month) if start_month is not None else s.index.min()
            end = _month_floor(end_month) if end_month is not None else s.index.max()
        elif months is not None and months > 0:
            end = s.index.max()
            start = (end - pd.DateOffset(months=months - 1)).to_period("M").to_timestamp()
        else:
            start = s.index.min()
            end = s.index.max()
        if start > end:
            start, end = end, start
        return s[(s.index >= start) & (s.index <= end)]

    def _control_limits(series):
        clean = series.dropna().astype(float)
        if clean.empty:
            return np.nan, np.nan, np.nan
        mean = clean.mean()
        std = clean.std(ddof=0)
        return mean, mean + (2 * std), max(mean - (2 * std), 0)

    def _shared_axis_limits(*series_list):
        y_values = []
        date_values = []
        for series in series_list:
            if series is None or len(series) == 0:
                continue
            clean = series.dropna().astype(float)
            if clean.empty:
                continue
            y_values.extend(clean.tolist())
            date_values.extend(clean.index.tolist())
            mean, ucl, lcl = _control_limits(clean)
            for value in [mean, ucl, lcl]:
                if pd.notna(value):
                    y_values.append(value)
        if len(y_values) == 0:
            y_limit = (0, 1)
        else:
            y_max = max(max(y_values), 1)
            step = 1 if y_max <= 10 else 5 if y_max <= 50 else 25 if y_max <= 200 else 50
            y_limit = (0, np.ceil((y_max * 1.08) / step) * step)
        if len(date_values) == 0:
            x_limit = None
        else:
            x_limit = (min(date_values) - pd.DateOffset(days=15), max(date_values) + pd.DateOffset(days=15))
        return y_limit, x_limit

    def _month_tick_interval(x_limit):
        if x_limit is None:
            return 1
        start = pd.Timestamp(x_limit[0])
        end = pd.Timestamp(x_limit[1])
        month_count = max(1, ((end.year - start.year) * 12) + end.month - start.month + 1)
        return max(1, int(np.ceil(month_count / 6)))

    def _plot_control_chart(ax, series, chart_name, ylabel, line_label, y_limit=None, x_limit=None, line_color="#0070C0"):
        series = series.dropna().astype(float)
        ax.set_title(f"Control Chart: {chart_name} vs. Dates\nUCL/LCL at Mean +/- 2 sigma", fontsize=13, fontweight="bold", pad=16)
        ax.set_ylabel(ylabel, fontsize=10, fontweight="bold")
        ax.set_xlabel("Date", fontsize=10, fontweight="bold")
        ax.grid(True, axis="both", color="#D9D9D9", alpha=0.5)
        ax.set_axisbelow(True)
        for spine in ax.spines.values():
            spine.set_color("black")
            spine.set_linewidth(0.8)
        if y_limit is not None:
            ax.set_ylim(y_limit)
        if x_limit is not None:
            ax.set_xlim(x_limit)
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=_month_tick_interval(x_limit)))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        ax.tick_params(axis="x", rotation=45)
        if series.empty:
            ax.text(0.5, 0.5, "No data available for selected window", ha="center", va="center", transform=ax.transAxes)
            return
        mean, ucl, lcl = _control_limits(series)
        ax.plot(series.index, series.values, color=line_color, marker="o", markersize=2.5, linewidth=1.0, label=line_label, zorder=3)
        ax.axhline(mean, color="green", linestyle="--", linewidth=1.3, label=f"Mean ({mean:.1f})", zorder=2)
        ax.axhline(ucl, color="red", linestyle="-", linewidth=1.3, label=f"UCL ({ucl:.1f}) - Add Vertical Day", zorder=2)
        ax.axhline(lcl, color="orange", linestyle="-", linewidth=1.3, label=f"LCL ({lcl:.1f}) - Can Add New LN", zorder=2)
        ax.axhspan(0, lcl, color="#FFD966", alpha=0.25, label="Available Capacity Zone", zorder=0)
        ax.legend(fontsize=8, loc="upper left", frameon=True)

    valid_teams = list(remaining_col_map.keys())
    selected_teams = [team for team in selected_teams if team in valid_teams]
    if len(selected_teams) == 0:
        raise ValueError(f"No valid teams selected. Choose from: {valid_teams}")

    monthly_completion = {team: _monthly_completion_from_sheet(trace_file, btg_sheet_map[team]) for team in ["structure", "systems", "declam", "test"]}
    monthly_completion["total"] = pd.concat(monthly_completion.values(), axis=1).fillna(0).sum(axis=1)
    monthly_remaining = {team: _monthly_remaining_from_sheet(trace_file, "Daily AP Status", column) for team, column in remaining_col_map.items()}

    chart_specs = [(team_key, f'{team_key.capitalize() if team_key != "total" else "Total"} BTG') for team_key in selected_teams]
    fig, axes = plt.subplots(len(chart_specs), 2, figsize=(18, max(6 * len(chart_specs), 8)), constrained_layout=True, squeeze=False)
    fig.patch.set_facecolor("white")
    fig.patch.set_edgecolor("black")
    fig.patch.set_linewidth(2)
    fig.suptitle("BTG Control Charts", fontsize=18, fontweight="bold")

    for row_idx, (team_key, display_name) in enumerate(chart_specs):
        completion_series = _filter_month_window(monthly_completion.get(team_key, pd.Series(dtype=float)), months=control_window_months, start_month=control_start_month, end_month=control_end_month)
        remaining_series = _filter_month_window(monthly_remaining.get(team_key, pd.Series(dtype=float)), months=control_window_months, start_month=control_start_month, end_month=control_end_month)
        team_label = team_key.capitalize() if team_key != "total" else "Total"
        shared_y_limit, shared_x_limit = _shared_axis_limits(completion_series, remaining_series)
        _plot_control_chart(axes[row_idx, 0], completion_series, f"{display_name} Completed", "Completed BTG", f"Completed BTG {team_label}", y_limit=shared_y_limit, x_limit=shared_x_limit)
        _plot_control_chart(axes[row_idx, 1], remaining_series, f"{display_name} Remaining", "Remaining BTG", f"Active BTG {team_label}", y_limit=shared_y_limit, x_limit=shared_x_limit)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=200, bbox_inches="tight", facecolor="white", edgecolor="black")
    plt.close(fig)
    return output_path


# Notebook compatibility alias.
control_chart = generate_monthly_btg_control_charts
