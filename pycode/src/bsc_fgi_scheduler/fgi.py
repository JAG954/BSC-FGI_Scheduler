"""FGI scheduler object extracted from BSC_FGI_Scheduler.ipynb."""

import copy

import numpy as np
import pandas as pd

from bsc_fgi_scheduler.config import CODECELL_OUTPUT, header, line
from bsc_fgi_scheduler.constants import FGI_TEAMS

# =============================================================================
# FGI SCHEDULER CLASS
# =============================================================================
# Owns all APs and locations active in FGI, plus the move / FGI-task / labor
# queues. Drives the daily simulation: rollout, labor allocation, paint and
# compass scheduling, move-queue processing, exit routing, and end-of-day
# pending-exit cleanup.

class FGI:
    def __init__(self, labor, CPJ, paint_schedule=None):
        self.labor = labor
        self.CPJ = CPJ
        self.paint_schedule = paint_schedule if paint_schedule is not None else None
        self.APs = {}
        self.Locations = {}
        self.sortedLocations = {
            'FA': {},
            'FGI': {},
            'DC': {},
            'temp': {}
        }
        self.queues = {
            'move': [],
            'FGI task': {
                'compass': [],
                'paint': [],
                'shake': []
            },
            'labor': {
                'structure': [],
                'systems': [],
                'declam': [],
                'test': []
            }
        }
        self.schedule = {}
        self.chickenTracks = {}
        self.apStateRows = []
        self.deliveryRows = []
        self.shift = None
        self.btg_budget = {team: 0 for team in FGI_TEAMS}
        self.movetime_remaining = 0
        self.pendingExitLNs = []

    # -------------------------------------------------------------------------
    # AP HANDLING METHODS
    # -------------------------------------------------------------------------
    def add_ap(self, ap):
        LN = ap.get_LN()

        if LN in self.APs:
            if CODECELL_OUTPUT:
                header('AP ALREADY IN FGI', '~')
                print(f'LN {LN} was already active in FGI; add_ap skipped')
                line('~')
            return False

        self.APs[LN] = ap
        ap.set_taskState('RO')

        if LN not in self.queues['FGI task']['paint']:
            self.queues['FGI task']['paint'].append(LN)

        if LN not in self.queues['FGI task']['compass']:
            self.queues['FGI task']['compass'].append(LN)

        for team in self.queues['labor']:
            remaining_btg = ap.get_fgi_btg(team)

            if remaining_btg > 0:
                ap.status[team] = False
                if LN not in self.queues['labor'][team]:
                    self.queues['labor'][team].append(LN)
            else:
                ap.status[team] = True

        if CODECELL_OUTPUT:
            header('AP ADDED TO FGI')
            print(f'LN {LN} added to FGI')
            print(f"Paint queue length: {len(self.queues['FGI task']['paint'])}")
            print(f"Compass queue length: {len(self.queues['FGI task']['compass'])}")
            for team in self.queues['labor']:
                print(f"{team} queue length: {len(self.queues['labor'][team])}")
            line()

        return True
    
    def get_active_ap_status_df(self):
        columns = [
            'LN',
            'Location',
            'Task_State',
            'Move_Req',
            'Destination',
            'Queues',
            'Queue_Count',
            'FGI_structure',
            'FGI_systems',
            'FGI_declam',
            'FGI_test',
            'Compass_Complete',
            'Paint_Complete'
        ]

        rows = []

        for LN, AP in self.APs.items():
            queue_membership = self.get_queue_membership(LN)

            rows.append({
                'LN': LN,
                'Location': None if AP.Location is None else AP.Location.name,
                'Task_State': AP.taskState,
                'Move_Req': AP.isMoveReq(),
                'Destination': AP.destination,
                'Queues': ', '.join(queue_membership),
                'Queue_Count': len(queue_membership),
                'FGI_structure': AP.get_fgi_btg('structure'),
                'FGI_systems': AP.get_fgi_btg('systems'),
                'FGI_declam': AP.get_fgi_btg('declam'),
                'FGI_test': AP.get_fgi_btg('test'),
                'Compass_Complete': AP.status.get('compassCalibrated', False),
                'Paint_Complete': AP.status.get('painted', False)
            })

        return pd.DataFrame(rows, columns=columns)

    def get_queue_membership(self, LN):
        memberships = []

        if LN in self.queues['move']:
            memberships.append('move')

        for task, queue in self.queues['FGI task'].items():
            if LN in queue:
                memberships.append(task)

        for team, queue in self.queues['labor'].items():
            if LN in queue:
                memberships.append(team)

        if LN in self.pendingExitLNs:
            memberships.append('pending_exit')

        return memberships

    def refresh_ap_states(self):
        # Active labor LNs (head, plus second when head won't exhaust budget).
        btg_active = set()
        for team in FGI_TEAMS:
            q = self.queues['labor'][team]
            budget = self.btg_budget[team]
            if not q or budget <= 0:
                continue
            head = q[0]
            btg_active.add(head)
            if self.APs[head].get_fgi_btg(team) < budget and len(q) >= 2:
                btg_active.add(q[1])

        compass_q = self.queues['FGI task']['compass']
        compass_head = compass_q[0] if compass_q else None

        for LN, ap in self.APs.items():
            if ap.taskState in ('exit', 'delivered'):
                continue
            loc = ap.Location.name if ap.Location else None

            if loc in ('BSC1', 'BSC2'):
                ap.taskState = 'paint'
            elif LN == compass_head and loc == 'CR3':
                ap.taskState = 'compass'
            elif LN in btg_active:
                ap.taskState = 'btg_completion'
            else:
                ap.taskState = 'idle'

    # -------------------------------------------------------------------------
    # LOCATION HANDLING METHODS
    # -------------------------------------------------------------------------
    def add_Location(self, name, location_obj):
        self.Locations[name] = location_obj

        # --- SORT LOCATION BY FUNCTIONAL GROUP ---
        # Group locations for later move selection, exit logic, and reporting.
        if str(name).startswith('N'):
            self.sortedLocations['temp'][name] = location_obj

        elif location_obj.owner == 'DC':
            self.sortedLocations['DC'][name] = location_obj

        elif str(name).startswith('P'):
            self.sortedLocations['FA'][name] = location_obj

        else:
            self.sortedLocations['FGI'][name] = location_obj

        self.chickenTracks[name] = None

        if CODECELL_OUTPUT:
            line()
            print(f'Location {name} added to FGI')
            print(f'Current locations in FGI: {list(self.Locations.keys())}')
            line()

    # -------------------------------------------------------------------------
    # LABOR HANDLING METHODS
    # -------------------------------------------------------------------------
        
    def assign_labor(self, team, date=None):

        btg_completed = 0
        worked_lns = []
        queue = self.queues['labor'][team]

        while self.btg_budget[team] > 0 and len(queue) > 0:
            LN = queue[0]
            ap = self.APs[LN]

            btg_consumed, ap_complete = ap.complete_BTG(
                team,
                btg_budget=self.btg_budget[team],
                byLabor=True
            )

            self.btg_budget[team] -= btg_consumed
            btg_completed += btg_consumed

            if btg_consumed > 0:
                worked_lns.append(LN)

                if hasattr(self, 'trace'):
                    self.trace.record_btg(date, LN, team, btg_consumed)

            if ap_complete:
                queue.pop(0)
            else:
                break

        btg_remaining = self.btg_budget[team]

        if hasattr(self, 'trace'):
            self.trace.record_labor(date, team, worked_lns)

        return worked_lns, btg_completed, btg_remaining
    
    # -------------------------------------------------------------------------
    # SCHEDULING / STATUS UPDATE METHODS
    # -------------------------------------------------------------------------
    def set_shift(self, shift):
        if shift not in [0, 1, 2, 3]:
            if CODECELL_OUTPUT:
                header('INVALID SHIFT')
                print(f'Shift {shift} is not valid. Shift must be 0, 1, 2, or 3.')
                line()
        
        if shift in [1, 2]:
            self.shift_labor = self.labor[shift]
            self.shift = shift
            self.btg_budget = {team: pd.to_numeric(self.shift_labor[team] / self.CPJ[team]) for team in FGI_TEAMS}
        
        if shift == 3:
            self.movetime_remaining = 8
            self.shift = shift

    def get_daily_status_df(self):
        if len(self.apStateRows) == 0:
            return pd.DataFrame(columns=[
                'Date',
                'LN',
                'Location',
                'FGI_tot',
                'structure',
                'systems',
                'declam',
                'test',
                'moveReq'
            ])

        return pd.DataFrame(self.apStateRows)
    
    def schedule_paint_moves(self, today):
        # --- SCHEDULED MOVES FOR PAINT ---
        # Paint scheduling creates move requests only. Paint completion occurs when AP leaves BSC.

        scheduled = []
        displaced = []

        tomorrow = today + pd.Timedelta(days=1)

        if self.paint_schedule is None:
            return {
                'scheduled': scheduled,
                'displaced': displaced
            }

        if tomorrow not in self.paint_schedule:
            return {
                'scheduled': scheduled,
                'displaced': displaced
            }

        for bay_name, scheduled_LN in self.paint_schedule[tomorrow].items():

            if bay_name not in self.Locations:
                continue

            bay = self.Locations[bay_name]
            current_ap = bay.AP
            current_LN = None if current_ap is None else current_ap.get_LN()

            # Move current bay occupant out if a different AP is scheduled for that bay.
            if current_LN is not None and current_LN != scheduled_LN:
                current_ap.taskState = 'btg_completion'
                self.request_move(
                    current_LN,
                    priority='clear_bay',
                    override=True
                )
                displaced.append(current_LN)

            # Move tomorrow's scheduled AP into the bay.
            if scheduled_LN is not None and scheduled_LN in self.APs:
                scheduled_ap = self.APs[scheduled_LN]
                scheduled_ap.taskState = 'paint'
                self.request_move(
                    scheduled_LN,
                    destination=bay_name,
                    priority='paint',
                    override=True
                )
                scheduled.append(scheduled_LN)

        return {
            'scheduled': scheduled,
            'displaced': displaced
        }
    
    def schedule_compass_moves(self, today):
        # --- SCHEDULED MOVES FOR COMPASS ---
        # Compass queue order is source-of-truth; only the head can complete.

        completed = None
        requested = None
        blocked_by = None

        compass_queue = self.queues['FGI task']['compass']
        if len(compass_queue) == 0:
            return {
                'completed': completed,
                'requested': requested,
                'blocked_by': blocked_by
            }

        head_LN = compass_queue[0]
        cr1 = self.Locations.get('CR1')
        cr2 = self.Locations.get('CR2')
        cr3 = self.Locations.get('CR3')

        cr1_clear = cr1 is None or cr1.AP is None
        cr2_clear = cr2 is None or cr2.AP is None

        if cr3 is None:
            blocked_by = 'missing_CR3'

        elif cr3.AP is not None:
            cr3_LN = cr3.AP.get_LN()

            if cr3_LN == head_LN and head_LN in self.APs:
                ap = self.APs[head_LN]
                has_start = ap.compassStartDate is not None
                waited_one_workday = (
                    has_start
                    and pd.Timestamp(today).normalize() > pd.Timestamp(ap.compassStartDate).normalize()
                )

                if cr1_clear and cr2_clear and waited_one_workday:
                    ap.status['compassCalibrated'] = True
                    ap.taskState = 'btg_completion'
                    self.dequeue('compass', head_LN)
                    self.request_move(
                        head_LN,
                        priority='compass_clear',
                        override=False
                    )
                    completed = head_LN
                else:
                    blocked_by = head_LN

            else:
                blocked_by = cr3_LN
                if cr3_LN in self.APs:
                    self.request_move(
                        cr3_LN,
                        priority='compass_clear',
                        override=False
                    )

        if cr3 is not None and cr3.AP is None and head_LN in self.APs:
            next_ap = self.APs[head_LN]
            next_ap.taskState = 'compass'
            if self.request_move(
                head_LN,
                destination='CR3',
                priority='compass',
                override=False
            ):
                requested = head_LN

        return {
            'completed': completed,
            'requested': requested,
            'blocked_by': blocked_by
        }


    def dequeue(self, queue_name, LN):
        removed = False

        if queue_name == 'all':
            removed_any = False

            for q_name in ['move']:
                removed_any = self.dequeue(q_name, LN) or removed_any

            for q_name in self.queues['FGI task']:
                removed_any = self.dequeue(q_name, LN) or removed_any

            for q_name in self.queues['labor']:
                removed_any = self.dequeue(q_name, LN) or removed_any

            return removed_any

        if queue_name == 'move':
            queue = self.queues['move']

            while LN in queue:
                queue.remove(LN)
                removed = True

            return removed

        if queue_name in self.queues['FGI task']:
            queue = self.queues['FGI task'][queue_name]

            while LN in queue:
                queue.remove(LN)
                removed = True

            return removed

        if queue_name in self.queues['labor']:
            queue = self.queues['labor'][queue_name]

            while LN in queue:
                queue.remove(LN)
                removed = True

            return removed

        return False

    # -------------------------------------------------------------------------
    # MOVE METHODS
    # -------------------------------------------------------------------------
    
    def get_req_centerline_moves(self, origin):
        blockers = []

        if origin is None:
            return None

        if origin.centerlines is None:
            return None

        for blocker_loc_name in origin.centerlines:
            blocker_loc_name = str(blocker_loc_name).strip()

            if blocker_loc_name not in self.Locations:
                continue

            blocker_loc = self.Locations[blocker_loc_name]

            if blocker_loc.AP is not None:
                blockers.append(blocker_loc.AP)

        if len(blockers) == 0:
            return None

        return blockers

    def centerline_blockers(self, blockers):
        centerline_nodes = ['N32', 'N31', 'N30', 'N29', 'N28']
        centerline_move_time = 0
        if blockers is None:
            return 0
        for blocker in blockers:
            centerline_move_time += blocker.Location.time_to[centerline_nodes.pop(0)] 
        centerline_move_time *= 2 # account for move out and return
        return centerline_move_time

    def move_ap(self, LN, destination, date=None):
        # --- FEASIBILITY CHECK ---
        if destination is None:
            return False, 0

        if destination.canPlace() is False:
            return False, 0
                
        ap = self.APs[LN]
        origin = ap.Location

        if origin is not None and origin.name == 'CR3' and not ap.status.get('compassCalibrated', False):
            ap.compassStartDate = None

        move_time = 0

        # --- APPLY CENTERLINES ---
        req_centerline_moves = self.get_req_centerline_moves(origin)
        
        if req_centerline_moves is not None:
            move_time += self.centerline_blockers(req_centerline_moves)
        
        # --- REMOVE FROM CURRENT LOCATION ---
        if origin is not None:
            direct_move_time = origin.time_to.get(destination.name, np.inf)
            if not np.isfinite(direct_move_time):
                if CODECELL_OUTPUT:
                    header('METHOD ERROR: move_ap', '~')
                    print(f'No move time defined from {origin.name} to {destination.name}')
                    line('~')
                return False, move_time
            move_time += direct_move_time

            if origin.name in ['BSC1', 'BSC2']:
                ap.status['painted'] = True
                self.dequeue('paint', LN)

        else:
            move_time = 0
            
        # --- MOVE TO DESTINATION ---
        if move_time <= self.movetime_remaining:
            if origin is not None:
                ap.path.append(origin.name)
                origin.unassign(date=date)
                self.chickenTracks[origin.name] = None


            destination.assign(ap, date=date)
            if destination.name in ['BSC1', 'BSC2']:
                ap.paintStartDate = pd.Timestamp(date).normalize() if date is not None else None
                ap.taskState = 'paint'
            ap.Location = destination
            self.chickenTracks[destination.name] = LN

            if destination.name == 'CR3' and self.queues['FGI task']['compass'] and self.queues['FGI task']['compass'][0] == LN:
                ap.compassStartDate = pd.Timestamp(date).normalize() if date is not None else None

            self.movetime_remaining -= move_time
        else:
            if CODECELL_OUTPUT:
                header('METHOD ERROR: move_ap', '~')
                print(f'Move time from {origin.name if origin else "None"} to {destination.name} is {move_time} hours, which exceeds the 8 hour limit')
                line('~')
            return False, move_time

        # --- MOVE COMPLETION STATE ---
        # Clear move request state only after the target AP has moved.
        ap.moveReq = False
        ap.destination = None
        ap.movePriority = 'normal'

        if hasattr(self, 'trace'):
            self.trace.record_move(date, LN, destination.name)

        return True, move_time
    
    def request_move(self, LN, destination=None, priority='normal', override=False):
        # --- ENQUEUE A MOVE REQUEST ---
        if LN not in self.APs:
            return False

        ap = self.APs[LN]

        if destination is not None and ap.Location is not None and ap.Location.name == destination:
            ap.moveReq = False
            ap.destination = None
            ap.movePriority = 'normal'
            return False

        if ap.isMoveReq() and not override:
            return False

        ap.requireMove(destination=destination)
        ap.movePriority = priority

        if LN not in self.queues['move']:
            self.queues['move'].append(LN)

        return True
    
    def execute_move_requests(self, date=None):
        # --- EXECUTE MOVES IN QUEUE ORDER ---
        # self.queues['move'] is the source of truth for movement order.
        results = []
        progress = True

        while progress:
            progress = False

            if self.movetime_remaining <= 0:
                break

            i = 0

            while i < len(self.queues['move']):
                if self.movetime_remaining <= 0:
                    break

                LN = self.queues['move'][i]

                if LN not in self.APs:
                    self.queues['move'].pop(i)
                    continue

                ap = self.APs[LN]

                if not ap.isMoveReq():
                    self.queues['move'].pop(i)
                    continue

                if ap.destination is not None:
                    destination = self.Locations.get(ap.destination)
                else:
                    candidates = ap.get_move_candidates(self)
                    destination = candidates[0]['destination'] if candidates else None

                if destination is None:
                    results.append({
                        'LN': LN,
                        'destination': None,
                        'moved': False,
                        'move_time': 0,
                        'reason': 'no_destination'
                    })
                    i += 1
                    continue

                moved, move_time = self.move_ap(LN, destination, date=date)

                results.append({
                    'LN': LN,
                    'destination': destination.name,
                    'moved': moved,
                    'move_time': move_time,
                    'reason': 'moved' if moved else 'move_failed'
                })

                if moved:
                    self.queues['move'].pop(i)
                    progress = True
                else:
                    i += 1

            if progress and self.movetime_remaining > 0:
                self.assign_exit_destinations()
                self.reorder_move_queue()

        return results
    
    def complete_AP(self, LN, date=None):
        if LN not in self.APs:
            return False

        AP = self.APs[LN]
        AP.exitPending = False
        AP.taskState = 'delivered'

        actual_exit_date = pd.Timestamp(date) if date is not None else None
        fa_ro_date = AP.get_FAROdate()

        planned_b1r_date = None
        days_late = None
        time_in_system_days = None

        if hasattr(AP, 'initial_toB1R'):
            planned_b1r_date = fa_ro_date + pd.Timedelta(days=AP.initial_toB1R)

        if actual_exit_date is not None:
            time_in_system_days = (actual_exit_date - fa_ro_date).days

            if planned_b1r_date is not None:
                days_late = (actual_exit_date - planned_b1r_date).days

        self.deliveryRows.append({
            'LN': LN,
            'FA_RO_Date': fa_ro_date,
            'Planned_B1R_Date': planned_b1r_date,
            'Actual_Exit_Date': actual_exit_date,
            'Time_In_System_Days': time_in_system_days,
            'Days_Late': days_late,
            'Final_Location': None if AP.Location is None else AP.Location.name
        })

        self.dequeue('all', LN)

        if AP.Location is not None:
            loc_name = AP.Location.name
            AP.Location.unassign()
            self.chickenTracks[loc_name] = None

        AP.Location = None
        self.APs.pop(LN)

        if CODECELL_OUTPUT:
            header('AP DELIVERED')
            print(f'LN {LN} has been delivered and removed from FGI')
            print(f'Time in system: {time_in_system_days}')
            print(f'Days late: {days_late}')
            line()

        return True
 
    def get_open_dc_stall(self, exclude=None):
        exclude = exclude or set()
        dc_locations = self.sortedLocations.get('DC', {})

        candidates = []

        for stall_name, stall in dc_locations.items():
            if stall_name in exclude:
                continue

            if stall is None:
                continue

            if not stall.canPlace():
                continue

            if any(ap.destination == stall_name for ap in self.APs.values()):
                continue

            candidates.append(stall)

        if len(candidates) == 0:
            return None

        def dc_rank(loc):
            # Prefer A1-A10. Allow D1/D2 only as overflow.
            is_d_location = str(loc.name).startswith('D')
            return (
                1 if is_d_location else 0,
                loc.priority
            )

        return sorted(candidates, key=dc_rank)[0]
    
    def reorder_move_queue(self):
        priority_rank = {
            'paint': 0,
            'clear_bay': 1,
            'exit': 2,
            'compass_clear': 3,
            'compass': 4,
            'normal': 5
        }

        def rank(LN):
            if LN not in self.APs:
                return (99, 99, np.inf)

            ap = self.APs[LN]
            priority = getattr(ap, 'movePriority', 'normal')
            priority_value = priority_rank.get(priority, 5)

            if ap.destination is not None:
                destination = self.Locations.get(ap.destination)

                if destination is None:
                    return (priority_value, 99, np.inf)

                origin = ap.Location
                move_time = 0 if origin is None else origin.time_to.get(destination.name, np.inf)

                return (priority_value, destination.priority, move_time)

            candidates = ap.get_move_candidates(self)
            if len(candidates) == 0:
                return (priority_value, 99, np.inf)

            best = candidates[0]

            return (priority_value, best['priority'], best['move_time'])

        self.queues['move'].sort(key=rank)
    
    # -------------------------------------------------------------------------
    # EXIT METHODS
    # -------------------------------------------------------------------------
    def assign_exit_destinations(self):
        # --- ASSIGN DC STALLS TO EXIT-READY APs ---
        # Reserves stalls inline so concurrent exit-ready APs don't collide.
        claimed = set()

        for LN, ap in self.APs.items():
            if not ap.is_exit_ready():
                continue

            if ap.Location is not None and ap.Location.name in self.sortedLocations['DC']:
                ap.taskState = 'exit'
                ap.exitPending = True
                continue

            if ap.destination is not None:
                continue

            stall = self.get_open_dc_stall(exclude=claimed)
            if stall is None:
                break

            ap.taskState = 'exit'
            ap.exitPending = True
            self.request_move(LN, destination=stall.name, priority='exit')
            claimed.add(stall.name)


    def mark_dc_arrivals_pending(self):
        # --- FLAG EXIT-ROUTED APs AT DC FOR END-OF-DAY EXIT ---
        marked = []

        for LN, ap in self.APs.items():
            if not getattr(ap, 'exitPending', False):
                continue

            if ap.Location is None:
                continue

            if ap.Location.name not in self.sortedLocations['DC']:
                continue

            if LN in self.pendingExitLNs:
                continue

            self.pendingExitLNs.append(LN)
            marked.append(LN)

        return marked


    def complete_pending_exits(self, date=None):
        # --- FINALIZE EXITS RECORDED THIS DAY ---
        # Called after record_day so today's CT row already shows the AP at DC.
        completed = []

        for LN in list(self.pendingExitLNs):
            if LN not in self.APs:
                continue

            if self.complete_AP(LN, date=date):
                completed.append(LN)

        self.pendingExitLNs = []
        return completed


    # -------------------------------------------------------------------------
    # KPI METHODS
    # -------------------------------------------------------------------------
    def record_day(self, date):
        date = pd.Timestamp(date)

        self.apStateRows = [
            row for row in self.apStateRows
            if pd.Timestamp(row['Date']) != date
        ]

        self.schedule[date] = {}

        for loc_name, loc in self.Locations.items():
            self.schedule[date][loc_name] = None if loc.AP is None else loc.AP.get_LN()

        for LN, ap in self.APs.items():
            self.apStateRows.append({
                'Date': date,
                'LN': LN,
                'Location': None if ap.Location is None else ap.Location.name,
                'FGI_tot': ap.get_fgi_btg('FGI_tot'),
                'structure': ap.get_fgi_btg('structure'),
                'systems': ap.get_fgi_btg('systems'),
                'declam': ap.get_fgi_btg('declam'),
                'test': ap.get_fgi_btg('test'),
                'moveReq': ap.isMoveReq()
            })
   
    def get_kpi_summary_df(self, trace=None):
        rows = []

        delivery_df = self.get_delivery_summary_df()
        daily_status_df = self.get_daily_status_df()

        active_status_df = pd.DataFrame([
            {
                'LN': LN,
                'Location': None if AP.Location is None else AP.Location.name,
                'Task_State': AP.taskState,
                'Move_Req': AP.isMoveReq(),
                'Destination': AP.destination,
                'FGI_structure': AP.get_fgi_btg('structure'),
                'FGI_systems': AP.get_fgi_btg('systems'),
                'FGI_declam': AP.get_fgi_btg('declam'),
                'FGI_test': AP.get_fgi_btg('test'),
                'Compass_Complete': AP.status.get('compassCalibrated', False),
                'Paint_Complete': AP.status.get('painted', False),
                'Exit_Ready': AP.is_exit_ready() if hasattr(AP, 'is_exit_ready') else False
            }
            for LN, AP in self.APs.items()
        ])

        delivered_count = len(delivery_df)
        active_count = len(active_status_df)

        avg_time_in_system = None
        if delivered_count > 0 and 'Time_In_System_Days' in delivery_df.columns:
            avg_time_in_system = delivery_df['Time_In_System_Days'].mean()

        avg_days_late = None
        if delivered_count > 0 and 'Days_Late' in delivery_df.columns:
            avg_days_late = delivery_df['Days_Late'].mean()

        rows.append({
            'KPI': 'Delivered AP Count',
            'Value': delivered_count,
            'Definition': 'Number of APs delivered through complete_AP()'
        })

        rows.append({
            'KPI': 'Active AP Count at Termination',
            'Value': active_count,
            'Definition': 'Number of APs still active in FGI at the time this KPI table was generated'
        })

        rows.append({
            'KPI': 'Average Days in System',
            'Value': avg_time_in_system,
            'Definition': 'Average Actual_Exit_Date - FA_RO_Date for delivered APs'
        })

        rows.append({
            'KPI': 'Average Days Late',
            'Value': avg_days_late,
            'Definition': 'Average Actual_Exit_Date - Planned_B1R_Date for delivered APs'
        })

        if len(active_status_df) > 0:
            rows.append({
                'KPI': 'Active Exit-Ready AP Count',
                'Value': int(active_status_df['Exit_Ready'].sum()),
                'Definition': 'Active APs whose AP.is_exit_ready() returned True'
            })

            rows.append({
                'KPI': 'Active APs With Pending Move Request',
                'Value': int(active_status_df['Move_Req'].sum()),
                'Definition': 'Active APs with moveReq currently set to True'
            })

            rows.append({
                'KPI': 'Active APs With Destination Assigned',
                'Value': int(active_status_df['Destination'].notna().sum()),
                'Definition': 'Active APs with a non-null destination field'
            })

            for status_col in ['Compass_Complete', 'Paint_Complete']:
                rows.append({
                    'KPI': f'Active APs - {status_col}',
                    'Value': int(active_status_df[status_col].sum()),
                    'Definition': f'Number of active APs where {status_col} is True'
                })

        if len(daily_status_df) > 0 and 'Date' in daily_status_df.columns and 'LN' in daily_status_df.columns:
            located_daily = daily_status_df.dropna(subset=['Location']) if 'Location' in daily_status_df.columns else pd.DataFrame()

            avg_located_aps = None
            if len(located_daily) > 0:
                avg_located_aps = located_daily.groupby('Date')['LN'].nunique().mean()

            rows.append({
                'KPI': 'Average Located APs Per Day',
                'Value': avg_located_aps,
                'Definition': 'Average number of APs assigned to a physical location per recorded day'
            })

        if trace is not None:
            try:
                trace_outputs = trace.to_dataframes()

                if len(trace_outputs) == 4:
                    chickentracks_df, labor_df, moves_df, btg_dfs = trace_outputs
                else:
                    chickentracks_df, labor_df, moves_df, btg_dfs = None, None, pd.DataFrame(), {}

                if moves_df is not None and len(moves_df) > 0:
                    move_count = moves_df.notna().sum().sum()
                else:
                    move_count = 0

                rows.append({
                    'KPI': 'Total Successful Moves Recorded',
                    'Value': move_count,
                    'Definition': 'Count of nonblank LN destination records in Moves Per Day trace output'
                })

                if isinstance(btg_dfs, dict):
                    for team, btg_df in btg_dfs.items():
                        if btg_df is None or len(btg_df) == 0:
                            avg_days_worked = None
                            total_btg = 0
                        else:
                            df = btg_df.copy().reset_index()
                            date_col = 'Date' if 'Date' in df.columns else df.columns[0]
                            value_cols = [c for c in df.columns if c != date_col]

                            if len(value_cols) == 0:
                                avg_days_worked = None
                                total_btg = 0
                            else:
                                long_df = df.melt(
                                    id_vars=[date_col],
                                    value_vars=value_cols,
                                    var_name='LN',
                                    value_name='BTG_Completed'
                                )

                                long_df = long_df[pd.notna(long_df['BTG_Completed'])]
                                long_df = long_df[long_df['BTG_Completed'] > 0]

                                if len(long_df) > 0:
                                    days_by_ln = long_df.groupby('LN')[date_col].nunique()
                                    avg_days_worked = days_by_ln.mean()
                                    total_btg = long_df['BTG_Completed'].sum()
                                else:
                                    avg_days_worked = None
                                    total_btg = 0

                        rows.append({
                            'KPI': f'Average Days Worked - {team}',
                            'Value': avg_days_worked,
                            'Definition': f'Average number of unique workdays with positive BTG completion per AP for {team}'
                        })

                        rows.append({
                            'KPI': f'Total BTG Completed - {team}',
                            'Value': total_btg,
                            'Definition': f'Total positive BTG completed by {team}'
                        })

            except Exception as e:
                rows.append({
                    'KPI': 'KPI Trace Error',
                    'Value': str(e),
                    'Definition': 'Trace-based KPI calculation failed'
                })

        return pd.DataFrame(rows)
    
    def get_delivery_summary_df(self):
        if len(self.deliveryRows) == 0:
            return pd.DataFrame(columns=[
                'LN',
                'FA_RO_Date',
                'Planned_B1R_Date',
                'Actual_Exit_Date',
                'Time_In_System_Days',
                'Days_Late',
                'Final_Location'
            ])

        return pd.DataFrame(self.deliveryRows)

    def get_team_kpi_df(self, trace=None):
        rows = []

        default_columns = [
            'Team',
            'AP_Count_Worked',
            'Total_BTG_Completed',
            'Average_Days_Worked_Per_AP',
            'Max_Days_Worked_On_One_AP',
            'Average_BTG_Per_Workday'
        ]

        if trace is None:
            return pd.DataFrame(columns=default_columns)

        try:
            trace_outputs = trace.to_dataframes()

            if len(trace_outputs) == 4:
                chickentracks_df, labor_df, moves_df, btg_dfs = trace_outputs
            else:
                return pd.DataFrame(columns=default_columns)

            if not isinstance(btg_dfs, dict):
                return pd.DataFrame(columns=default_columns)

            for team, btg_df in btg_dfs.items():
                if btg_df is None or len(btg_df) == 0:
                    rows.append({
                        'Team': team,
                        'AP_Count_Worked': 0,
                        'Total_BTG_Completed': 0,
                        'Average_Days_Worked_Per_AP': None,
                        'Max_Days_Worked_On_One_AP': None,
                        'Average_BTG_Per_Workday': None
                    })
                    continue

                df = btg_df.copy().reset_index()
                date_col = 'Date' if 'Date' in df.columns else df.columns[0]
                value_cols = [c for c in df.columns if c != date_col]

                if len(value_cols) == 0:
                    rows.append({
                        'Team': team,
                        'AP_Count_Worked': 0,
                        'Total_BTG_Completed': 0,
                        'Average_Days_Worked_Per_AP': None,
                        'Max_Days_Worked_On_One_AP': None,
                        'Average_BTG_Per_Workday': None
                    })
                    continue

                long_df = df.melt(
                    id_vars=[date_col],
                    value_vars=value_cols,
                    var_name='LN',
                    value_name='BTG_Completed'
                )

                long_df = long_df[pd.notna(long_df['BTG_Completed'])]
                long_df = long_df[long_df['BTG_Completed'] > 0]

                if len(long_df) == 0:
                    rows.append({
                        'Team': team,
                        'AP_Count_Worked': 0,
                        'Total_BTG_Completed': 0,
                        'Average_Days_Worked_Per_AP': None,
                        'Max_Days_Worked_On_One_AP': None,
                        'Average_BTG_Per_Workday': None
                    })
                    continue

                days_by_ln = long_df.groupby('LN')[date_col].nunique()
                btg_by_day = long_df.groupby(date_col)['BTG_Completed'].sum()

                rows.append({
                    'Team': team,
                    'AP_Count_Worked': long_df['LN'].nunique(),
                    'Total_BTG_Completed': long_df['BTG_Completed'].sum(),
                    'Average_Days_Worked_Per_AP': days_by_ln.mean(),
                    'Max_Days_Worked_On_One_AP': days_by_ln.max(),
                    'Average_BTG_Per_Workday': btg_by_day.mean()
                })

            return pd.DataFrame(rows, columns=default_columns)

        except Exception:
            return pd.DataFrame(columns=default_columns)
