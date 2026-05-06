import pandas as pd

from bsc_fgi_scheduler.export import SCHEDULER_TRACE_SHEETS, export_scheduler_trace
from bsc_fgi_scheduler.validation import validate_required_sheets


class FakeTrace:
    def to_dataframes(self):
        index = pd.DatetimeIndex([pd.Timestamp("2024-01-01")], name="Date")
        chickentracks_df = pd.DataFrame({"A1": ["1"]}, index=index)
        labor_df = pd.DataFrame({"structure": ["1"], "systems": [None], "declam": [None], "test": [None]}, index=index)
        moves_df = pd.DataFrame({"1": ["A1"]}, index=index)
        btg_dfs = {
            "structure": pd.DataFrame({"1": [1.0]}, index=index),
            "systems": pd.DataFrame(index=index),
            "declam": pd.DataFrame(index=index),
            "test": pd.DataFrame(index=index),
        }
        return chickentracks_df, labor_df, moves_df, btg_dfs


class FakeFGI:
    def get_daily_status_df(self):
        return pd.DataFrame(
            {
                "Date": [pd.Timestamp("2024-01-01")],
                "LN": ["1"],
                "Location": ["A1"],
                "FGI_tot": [0],
                "structure": [0],
                "systems": [0],
                "declam": [0],
                "test": [0],
                "moveReq": [False],
            }
        )

    def get_delivery_summary_df(self):
        return pd.DataFrame(
            {
                "LN": ["1"],
                "FA_RO_Date": [pd.Timestamp("2024-01-01")],
                "Planned_B1R_Date": [pd.Timestamp("2024-01-02")],
                "Actual_Exit_Date": [pd.Timestamp("2024-01-03")],
                "Time_In_System_Days": [2],
                "Days_Late": [1],
                "Final_Location": ["A1"],
            }
        )

    def get_active_ap_status_df(self):
        return pd.DataFrame()

    def get_kpi_summary_df(self, trace=None):
        return pd.DataFrame({"KPI": ["Delivered AP Count"], "Value": [1], "Definition": ["Number delivered"]})

    def get_team_kpi_df(self, trace=None):
        return pd.DataFrame({"Team": ["structure"], "AP_Count_Worked": [1]})


def test_export_scheduler_trace_writes_expected_sheets(tmp_path):
    output_file = export_scheduler_trace(FakeFGI(), FakeTrace(), output_dir=tmp_path)

    validation = validate_required_sheets(output_file, SCHEDULER_TRACE_SHEETS)

    assert validation["passed"] is True
