import pandas as pd

from bsc_fgi_scheduler.data_import import build_live_state_workbook


def test_simulated_rate_workbook_builds_expected_live_state(repo_root, tmp_path):
    output_path = tmp_path / "FGI_liveState.xlsx"

    ap_df, location_df, labor_df = build_live_state_workbook(
        fa_status_path=repo_root / "data" / "simulated" / "FA_Status_FGI_Handoff_R10.xlsx",
        locations_path=repo_root / "data" / "raw" / "FGI_Locations_wPriority.xlsx",
        move_times_path=repo_root / "data" / "staged" / "move_times" / "move_time_estimation.xlsx",
        paint_schedule_path=repo_root / "data" / "raw" / "paint_schedules.xlsx",
        output_path=output_path,
        simulated=True,
    )

    assert output_path.exists()
    assert {"LN", "FA RO", "BTG_tot"}.issubset(ap_df.columns)
    assert {"Location", "Future State Priority", "Owner"}.issubset(location_df.columns)
    assert {"category", "shift", "team", "value"}.issubset(labor_df.columns)
    assert {"ap_data", "location_data", "labor_data"}.issubset(set(pd.ExcelFile(output_path).sheet_names))
