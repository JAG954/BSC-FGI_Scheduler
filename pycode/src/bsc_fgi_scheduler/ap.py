"""Aircraft-program model extracted from BSC_FGI_Scheduler.ipynb."""

import copy

import numpy as np
import pandas as pd

from bsc_fgi_scheduler.config import CODECELL_OUTPUT, header, line
from bsc_fgi_scheduler.constants import BTG_TYPES_BY_LABOR, FGI_TEAMS_BY_BTG_TYPE, get_FGI_BTG

class AP:
    # =========================================================================
    # AP CLASS
    # =========================================================================
    # Aircraft-program object. Owns FA rollout state, FGI workload, scheduling
    # state, and production status flags. Instances are constructed once from
    # the live-state ap_df and reset between runs via reset_state().

    def __init__(self, LN, faro, toB1R, counters, btg=None, tankClosed=False,
                 ceilings=0, testsRun=0, p3_milestones=None, shakes=None):

        # --- FA rollout attributes (from liveState) ---
        self.LN = LN
        self.faro = faro
        self.toB1R = toB1R
        self.counters = counters
        self.btg = btg if btg is not None else {
            "tot": 0, "p0": 0, "p1": 0, "p2": 0, "p3": 0,
            "engines": 0, "doors": 0, "test": 0
        }
        # Imported from liveState; reserved for tank-closure / shake / P3 work.
        self.tankClosed = tankClosed
        self.ceilings = ceilings
        self.testsRun = testsRun
        self.p3milestones = p3_milestones if p3_milestones is not None else {'tot': 6, 'complete': 0}
        self.shakes = shakes if shakes is not None else {'complete': 0, 'req': 4}

        # --- Scheduling attributes ---
        self.schedule = {}
        self.moveReq = False
        self.path = []
        self.Location = None
        self.destination = None
        self.compassStartDate = None
        self.paintStartDate = None
        self.exitPending = False

        # --- FGI workload ---
        self.taskState = 'FA'
        self.FGI_btg = get_FGI_BTG(self.btg)

        # --- Production status flags ---
        # compassCalibrated and painted flip from move_ap / schedule_compass_moves.
        # structure/systems/declam/test flip from update_labor_status() based on remaining BTG.
        self.status = {
            'compassCalibrated': False,
            'painted': False,
            'structure': self.FGI_btg['structure'] <= 0,
            'systems': self.FGI_btg['systems'] <= 0,
            'declam': self.FGI_btg['declam'] <= 0,
            'test': self.FGI_btg['test'] <= 0
        }
        self.movePriority = 'normal'

        # --- Initial state snapshot (used by reset_state) ---
        self.initial_toB1R = toB1R
        self.initial_btg = copy.deepcopy(self.btg)
        self.initial_FGI_btg = copy.deepcopy(self.FGI_btg)
        self.initial_status = copy.deepcopy(self.status)

    # -------------------------------------------------------------------------
    # Get methods
    # -------------------------------------------------------------------------
    def get_LN(self): return str(self.LN)
    def get_FAROdate(self): return pd.to_datetime(self.faro)
    def get_daystoB1R(self): return pd.Timedelta(days=self.toB1R)
    def get_fgi_btg(self, team):
        return pd.to_numeric(self.FGI_btg[team]) if team in self.FGI_btg.keys() else False

    # -------------------------------------------------------------------------
    # Scheduling methods
    # -------------------------------------------------------------------------
    def reset_state(self):
        # Restore FA / FGI workload state.
        self.toB1R = self.initial_toB1R
        self.btg = copy.deepcopy(self.initial_btg)
        self.FGI_btg = copy.deepcopy(self.initial_FGI_btg)
        self.status = copy.deepcopy(self.initial_status)

        # Restore scheduling state.
        self.schedule = {}
        self.moveReq = False
        self.path = []
        self.Location = None
        self.taskState = 'FA'
        self.destination = None
        self.exitPending = False
        self.compassStartDate = None
        self.paintStartDate = None

    def update_labor_status(self):
        # Refresh FGI team completion flags from remaining FGI BTG.
        self.status['structure'] = self.get_fgi_btg('structure') <= 0
        self.status['systems'] = self.get_fgi_btg('systems') <= 0
        self.status['declam'] = self.get_fgi_btg('declam') <= 0
        self.status['test'] = self.get_fgi_btg('test') <= 0
        return self.status

    def is_exit_ready(self):
        # Returns True only when all production gates are clear and no move is pending.
        # This mirrors update_labor_status() using current BTG without mutating status.
        labor_complete = {
            'structure': self.get_fgi_btg('structure') <= 0,
            'systems': self.get_fgi_btg('systems') <= 0,
            'declam': self.get_fgi_btg('declam') <= 0,
            'test': self.get_fgi_btg('test') <= 0,
        }

        return (
            self.status['compassCalibrated']
            and self.status['painted']
            and labor_complete['structure']
            and labor_complete['systems']
            and labor_complete['declam']
            and labor_complete['test']
            and not self.isMoveReq()
            and self.destination is None
        )

    def set_taskState(self, state):
        AP_TASK_STATES = ['FA', 'RO', 'idle', 'paint', 'compass', 'shake',
                          'btg_completion', 'tankClosure', 'toDC', 'exit', 'delivered']
        if state in AP_TASK_STATES:
            self.taskState = state
        else:
            if CODECELL_OUTPUT:
                header('INVALID METHOD CALL')
                print(f'LN: {self.LN} taskState set to {state}')
                line()
            return False

    # -------------------------------------------------------------------------
    # Move methods
    # -------------------------------------------------------------------------
    def get_move_candidates(self, fgi, allow_temp_locations=False):
        origin = self.Location
        candidates = []

        for loc_name, loc in fgi.Locations.items():
            if origin is not None and loc.name == origin.name:
                continue

            if loc.is_temp and not allow_temp_locations:
                continue

            if not loc.canPlace():
                continue

            if origin is None:
                move_time = 0
            else:
                move_time = origin.time_to.get(loc_name, np.inf)

                if not np.isfinite(move_time):
                    continue

            candidates.append({
                'destination': loc,
                'destination_name': loc.name,
                'priority': loc.priority,
                'move_time': move_time
            })

        return sorted(candidates, key=lambda c: (c['priority'], c['move_time']))

    def isMoveReq(self): return self.moveReq

    def requireMove(self, destination=None):
        # Internal AP-side state mutation. Callers must go through FGI.request_move()
        # so the move queue stays in sync with ap.moveReq.
        self.moveReq = True
        self.destination = destination
        if CODECELL_OUTPUT:
            header('MOVE REQUIRED')
            current_loc = self.Location.name if self.Location is not None else None
            print(f'LN: {self.LN} requires move from {current_loc}\nTask State: {self.taskState}')
            line()

    def get_move_rank(self, fgi):
        # Tuple ranks: (tier, destination priority, move time).
        # Tier 0: mandatory destination already set (paint, compass, exit).
        # Tier 1: AP picks its best candidate location.
        # Tier 2: no feasible destination right now.
        if self.destination is not None:
            return (0, 0, 0)

        candidates = self.get_move_candidates(fgi)
        if not candidates:
            return (2, 999, 999)

        top = candidates[0]
        return (1, top['priority'], top['move_time'])

    # -------------------------------------------------------------------------
    # BTG / task completion
    # -------------------------------------------------------------------------
    def complete_BTG(self, category, btg_budget=0, byLabor=False):
        # Complete BTG using either a direct BTG category or an FGI labor bucket.
        # Returns (btg_consumed, ap_complete_for_that_bucket).
        if btg_budget is None or btg_budget <= 0:
            if CODECELL_OUTPUT:
                header('METHOD ERROR: complete_BTG')
                print('tried to complete BTG with no available BTG budget')
                print(f'LN: {self.LN} | category: {category} | btg_budget: {btg_budget}')
                line()
            return 0, False

        if not byLabor and category not in self.btg:
            if CODECELL_OUTPUT:
                header('METHOD ERROR: complete_BTG')
                print(f'invalid BTG category when byLabor=False: {category}')
                print(f'valid categories: {list(self.btg.keys())}')
                line()
            return 0, False

        if byLabor and category not in self.FGI_btg:
            if CODECELL_OUTPUT:
                header('METHOD ERROR: complete_BTG')
                print(f'invalid labor category when byLabor=True: {category}')
                print(f'valid categories: {list(self.FGI_btg.keys())}')
                line()
            return 0, False

        # --- Direct BTG category completion ---
        if not byLabor:
            available_btg = max(self.btg[category], 0)
            btg_consumed = min(available_btg, btg_budget)

            self.btg[category] = max(self.btg[category] - btg_consumed, 0)
            self.btg['tot'] = max(self.btg['tot'] - btg_consumed, 0)

            if category in FGI_TEAMS_BY_BTG_TYPE and FGI_TEAMS_BY_BTG_TYPE[category] is not None:
                for team in FGI_TEAMS_BY_BTG_TYPE[category]:
                    if team in self.FGI_btg:
                        self.FGI_btg[team] = max(self.FGI_btg[team] - btg_consumed, 0)

            ap_complete = self.btg[category] <= 0

        # --- Labor bucket completion ---
        else:
            available_btg = max(self.FGI_btg[category], 0)
            btg_consumed = min(available_btg, btg_budget)

            self.FGI_btg[category] = max(self.FGI_btg[category] - btg_consumed, 0)

            if category in BTG_TYPES_BY_LABOR:
                for btg_type in BTG_TYPES_BY_LABOR[category]:
                    if btg_type in self.btg:
                        self.btg[btg_type] = max(self.btg[btg_type] - btg_consumed, 0)

            self.btg['tot'] = max(self.btg['tot'] - btg_consumed, 0)

            ap_complete = self.FGI_btg[category] <= 0

        # Refresh team status flags after every BTG completion.
        self.update_labor_status()

        return btg_consumed, ap_complete
