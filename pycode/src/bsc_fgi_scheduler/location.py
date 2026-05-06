"""Location model extracted from BSC_FGI_Scheduler.ipynb."""

from bsc_fgi_scheduler.config import CODECELL_OUTPUT, DISCONTINUED_LOCATIONS, NEW_FA_LOCATIONS, NEW_FA_ONLINE, header, line

class Location:
    # =========================================================================
    # LOCATION CLASS
    # =========================================================================
    # Physical or temporary FGI/FA location. Tracks one assigned AP at a time,
    # carries tooling/centerline metadata, and exposes canPlace() which the
    # scheduler uses for every placement decision.

    def __init__(self, priority, dateOnline, name, owner=None, tooling=None, centerlines=None):
        self.priority = priority

        if dateOnline == 'Now':
            self.isOnline = True
        elif dateOnline == 'At R10' or name in NEW_FA_LOCATIONS:
            self.isOnline = NEW_FA_ONLINE
        else:
            self.isOnline = False

        self.name = name
        self.is_temp = str(self.name).startswith('N')
        self.owner = owner
        self.tooling = tooling if tooling is not None else {
            'jacking': False, 'wings': False, 'tankClosure': False
        }

        centerline_list = [
            centerline.strip()
            for centerline in str(centerlines).split(',')
            if centerline.strip() not in ['', 'None', 'nan', 'N/A']
        ]
        self.centerlines = centerline_list if len(centerline_list) > 0 else None

        self.schedule = {}
        self.time_to = {}
        self.AP = None

    def canUse(self, tool):
        if tool in self.tooling.keys():
            return self.tooling[tool]
        return False

    def isAvailable(self):
        return self.AP is None

    def canPlace(self):
        # FA-owned locations are not placeable through the scheduler;
        # discontinued locations are excluded from candidate generation.
        if self.owner == 'FA':
            return False
        if self.name in DISCONTINUED_LOCATIONS:
            return False
        return self.isOnline and self.isAvailable()

    def assign(self, AP, date=None):
        if self.AP is not None:
            if CODECELL_OUTPUT:
                header('ERROR', '~')
                print("AP assigned to unavailable location")
                line('~')
            return False

        self.AP = AP
        if date is not None:
            self.schedule[date] = AP.get_LN()
        return True

    def unassign(self, date=None):
        if CODECELL_OUTPUT and self.AP is not None:
            header('MOVE', ' - ')
            print(f'{self.AP.get_LN()} removed from location {self.name}')
            line(' - ')

        if date is not None:
            self.schedule[date] = None

        self.AP = None

    def clear_schedule(self):
        self.schedule = {}

    def set_time_to(self, other, move_time):
        self.time_to[other] = move_time
