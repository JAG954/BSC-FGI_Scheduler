"""Trace logger extracted from BSC_FGI_Scheduler.ipynb."""

import numpy as np
import pandas as pd

from bsc_fgi_scheduler.constants import FGI_TEAMS

# =============================================================================
# FGI TRACE CLASS
# =============================================================================
# Run-time event log used by the workbook export. Records daily location
# occupancy, labor allocation, moves, and BTG completion. to_dataframes()
# returns the four sheets consumed by the export cell.

class FGITrace:
    def __init__(self):
        self.chickentracks = {}
        self.labor_allocation = {}
        self.moves = {}
        self.btg_completion = {}

    @staticmethod
    def _date_key(date):
        return pd.Timestamp(date).normalize()

    @staticmethod
    def _ln_key(LN):
        if LN is None or pd.isna(LN):
            return None

        if isinstance(LN, (int, np.integer)):
            return str(int(LN))

        if isinstance(LN, (float, np.floating)) and float(LN).is_integer():
            return str(int(LN))

        return str(LN)

    def record_day_start(self, date, fgi):
        date = self._date_key(date)

        self.chickentracks[date] = {
            loc_name: self._ln_key(loc.AP.get_LN()) if loc.AP is not None else None
            for loc_name, loc in fgi.Locations.items()
        }

    def record_labor(self, date, team, LNs):
        date = self._date_key(date)
        team = str(team)

        if date not in self.labor_allocation:
            self.labor_allocation[date] = {}

        if isinstance(LNs, (list, tuple, set, pd.Series, np.ndarray)):
            normalized_lns = [self._ln_key(LN) for LN in LNs]
            normalized_lns = [LN for LN in normalized_lns if LN is not None]
            self.labor_allocation[date][team] = ', '.join(normalized_lns)
        elif LNs is None:
            self.labor_allocation[date][team] = None
        else:
            self.labor_allocation[date][team] = self._ln_key(LNs)

    def record_move(self, date, LN, target_location):
        date = self._date_key(date)
        LN = self._ln_key(LN)

        if LN is None:
            return

        if date not in self.moves:
            self.moves[date] = {}

        self.moves[date][LN] = None if target_location is None else str(target_location)

    def record_btg(self, date, LN, skill, btg_completed):
        date = self._date_key(date)
        LN = self._ln_key(LN)
        skill = str(skill)
        btg_completed = pd.to_numeric(btg_completed, errors='coerce')

        if LN is None or pd.isna(btg_completed):
            return

        if skill not in self.btg_completion:
            self.btg_completion[skill] = {}

        if date not in self.btg_completion[skill]:
            self.btg_completion[skill][date] = {}

        current = self.btg_completion[skill][date].get(LN, 0)
        self.btg_completion[skill][date][LN] = current + float(btg_completed)

    @staticmethod
    def _sorted_trace_df(data):
        df = pd.DataFrame.from_dict(data, orient='index')
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        df.index.name = 'Date'
        return df

    def to_dataframes(self):
        chickentracks_df = self._sorted_trace_df(self.chickentracks)

        labor_df = self._sorted_trace_df(self.labor_allocation)
        for team in FGI_TEAMS:
            if team not in labor_df.columns:
                labor_df[team] = None
        labor_df = labor_df[FGI_TEAMS]

        moves_df = self._sorted_trace_df(self.moves)

        btg_dfs = {}
        for team in FGI_TEAMS:
            data = self.btg_completion.get(team, {})
            btg_dfs[team] = self._sorted_trace_df(data)

        return chickentracks_df, labor_df, moves_df, btg_dfs
