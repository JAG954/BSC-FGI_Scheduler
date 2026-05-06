"""Callable scheduler loop extracted from BSC_FGI_Scheduler.ipynb."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

import bsc_fgi_scheduler.config as default_config
from bsc_fgi_scheduler.dataframes import add_move_times, init_aps, init_locations, load_live_state, load_move_times, load_paint_schedule
from bsc_fgi_scheduler.export import export_scheduler_trace
from bsc_fgi_scheduler.fgi import FGI
from bsc_fgi_scheduler.trace import FGITrace


def _cfg(config, name):
    if config is None:
        return getattr(default_config, name)
    if isinstance(config, dict):
        return config.get(name, getattr(default_config, name))
    return getattr(config, name, getattr(default_config, name))


def run_scheduler(live_state_path=None, output_dir=None, config=None, paint_schedule_path=None, export=True):
    ap_df, location_df, labor_df, staffing_by_shift, cpj = load_live_state(live_state_path, return_config=True)
    move_times = load_move_times()
    paint_schedule = load_paint_schedule(filepath=paint_schedule_path) if paint_schedule_path is not None else load_paint_schedule()

    APs = init_aps(ap_df)
    Locations = init_locations(location_df)

    start = pd.to_datetime(_cfg(config, "STARTDATE"))
    end = pd.to_datetime(_cfg(config, "ENDDATE"))
    forecast_cap_days = _cfg(config, "FORECAST_CAP_DAYS")
    forecast_end = end + pd.Timedelta(days=forecast_cap_days)
    forecast_until_completion = _cfg(config, "FORECAST_UNTIL_COMPLETION")
    planned_buffer_days = _cfg(config, "PLANNED_BUFFER_DAYS")
    codecell_output = _cfg(config, "CODECELL_OUTPUT")

    today = start
    termination = False

    for _, ap in APs.items():
        ap.reset_state()

    for _, loc in Locations.items():
        loc.AP = None
        loc.schedule = {}

    fgi = FGI(labor=staffing_by_shift, CPJ=cpj, paint_schedule=paint_schedule)
    trace = FGITrace()
    fgi.trace = trace

    for loc_name, loc in Locations.items():
        fgi.add_Location(loc_name, loc)

    add_move_times(fgi, move_times)

    while termination is False:
        if codecell_output:
            default_config.header(f'{today.strftime("%Y-%m-%d")}', '=')

        if today > end:
            if not forecast_until_completion:
                termination = True
                break
            if len(fgi.APs) == 0:
                termination = True
                break
            if today > forecast_end:
                termination = True
                break

        trace.record_day_start(today, fgi)

        for LN, ap in APs.items():
            if LN not in fgi.APs and today == ap.get_FAROdate():
                fgi.add_ap(ap)
                if codecell_output:
                    default_config.header('RO')
                    print(f'AP {LN} rolled out from FA on {today.strftime("%Y-%m-%d")}')
                    print('Added to FGI object')
                    default_config.line()

        shift = 0
        while shift < 3 and len(fgi.APs) > 0:
            fgi.shift = shift

            if shift == 0:
                for _, AP in fgi.APs.items():
                    AP.toB1R -= 1

                if today.weekday() < 5:
                    fgi.refresh_ap_states()
                    if codecell_output:
                        print('Workday')
                    shift = 1
                else:
                    shift = 4

            if shift in [1, 2]:
                fgi.set_shift(shift)
                if codecell_output:
                    default_config.header(f'Shift: {shift}')
                    default_config.header('Labor allocation', '-')

                for team in fgi.queues['labor']:
                    worked_lns, btg_completed, btg_remaining = fgi.assign_labor(team, date=today)
                    trace.record_labor(today, team, worked_lns)
                    if btg_remaining > 0 and codecell_output:
                        print(f"Idle Time for {team}, with {btg_remaining} possible BTG completions")
                shift += 1

            if shift == 3 and today not in planned_buffer_days:
                fgi.set_shift(shift)
                fgi.schedule_paint_moves(today)
                fgi.schedule_compass_moves(today)
                fgi.assign_exit_destinations()
                fgi.mark_dc_arrivals_pending()
                fgi.reorder_move_queue()
                fgi.execute_move_requests(date=today)
                fgi.mark_dc_arrivals_pending()
                if fgi.movetime_remaining <= 0:
                    break

        fgi.refresh_ap_states()
        fgi.record_day(today)
        fgi.complete_pending_exits(date=today)
        today += pd.Timedelta(days=1)

    delivery_df = fgi.get_delivery_summary_df()
    active_status_df = fgi.get_active_ap_status_df()
    kpi_summary_df = fgi.get_kpi_summary_df(trace=trace)
    team_kpi_df = fgi.get_team_kpi_df(trace=trace)

    output_files = []
    if export:
        output_files.append(export_scheduler_trace(fgi, trace, output_dir=output_dir))

    return {
        "fgi": fgi,
        "trace": trace,
        "delivery_df": delivery_df,
        "active_status_df": active_status_df,
        "kpi_summary_df": kpi_summary_df,
        "team_kpi_df": team_kpi_df,
        "output_files": output_files,
    }


if __name__ == "__main__":
    result = run_scheduler(export=True)
    for output_file in result["output_files"]:
        print(output_file)
