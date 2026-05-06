"""Static scheduler constants extracted from the active notebooks."""

import math

FGI_STAFFING_BYSHIFT = {
    1: {"structure": 16, "systems": 60, "declam": 16, "test": 18},
    2: {"structure": 6, "systems": 14, "declam": 4, "test": 0},
    3: {"structure": 0, "systems": 0, "declam": 0, "test": 0},
}

FGI_CPJ = {"structure": 6, "systems": 3.5, "declam": 3, "test": 8}

CENTERLINES = {
    "A1": None,
    "A2": None,
    "A3": None,
    "A4": None,
    "A5": None,
    "A6": None,
    "A7": None,
    "A8": None,
    "A9": ["C1"],
    "A10": ["C1", "C2"],
    "BSC1": ["C1", "C2", "C3", "C3.5", "C4"],
    "BSC2": ["C1", "C2", "C3", "C3.5", "C4", "C5"],
    "C1": None,
    "C2": ["C1"],
    "C3": ["C1", "C2"],
    "C3.5": ["C1", "C2", "C3"],
    "C4": ["C1", "C2", "C3", "C3.5"],
    "C5": ["C1", "C2", "C3", "C3.5", "C4"],
    "CR1": ["CR3", "CR2"],
    "CR2": ["CR3"],
    "CR3": None,
    "D1": None,
    "D2": None,
    "F1": ["C1", "C2"],
    "F2": ["C1", "C2"],
    "L4": None,
    "L5": ["L4"],
    "Spur": None,
    "T1": None,
    "T2": None,
    "T3": None,
    "T4": None,
}

FGI_TEAMS = ["structure", "systems", "declam", "test"]
BTG_TYPES = ["tot", "p0", "p1", "p2", "p3", "engines", "doors", "test"]

BTG_TYPES_BY_LABOR = {
    "structure": ["tot"],
    "systems": ["p2"],
    "declam": ["p3", "engines"],
    "test": ["test"],
}
FGI_TEAMS_BY_BTG_TYPE = {
    "tot": ["structure", "systems", "declam", "test"],
    "FGI_tot": ["structure"],
    "p2": ["systems"],
    "p3": ["declam"],
    "engines": ["declam"],
    "test": ["test"],
}
for btg_type in BTG_TYPES:
    if btg_type not in FGI_TEAMS_BY_BTG_TYPE:
        FGI_TEAMS_BY_BTG_TYPE[btg_type] = None

AP_TASK_STATES = [
    "FA",
    "RO",
    "idle",
    "paint",
    "compass",
    "shake",
    "btg_completion",
    "tankClosure",
    "toDC",
    "exit",
    "delivered",
]

DEFAULT_LOCATION_GROUPS = {
    "FA": [],
    "FGI": [],
    "DC": ["A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9", "A10", "D1", "D2"],
    "temp": [],
}
PREFERRED_DC_PREFIXES = ("A",)
DC_OVERFLOW_PREFIXES = ("D",)


def get_FGI_BTG(faro_btg):
    FGI_btg = {
        "FGI_tot": faro_btg["tot"] - faro_btg["p0"] - faro_btg["p1"],
        "structure": math.ceil(0.1 * (faro_btg["tot"] - faro_btg["p0"] - faro_btg["p1"])),
        "systems": math.ceil(faro_btg["p2"]),
        "declam": math.ceil(faro_btg["engines"]),
        "test": faro_btg["test"],
    }
    return FGI_btg
