"""Run-condition configuration extracted from the scheduler notebook."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from bsc_fgi_scheduler.paths import OUTPUT_DIR, get_default_filepaths

filepaths = get_default_filepaths()
rootpath = Path(__file__).resolve().parents[2]

STARTDATE = "2024-08-13"
ENDDATE = "2026-3-10"
FORECAST_UNTIL_COMPLETION = True
FORECAST_CAP_DAYS = 365

NEW_FA_ONLINE = True
NEW_FA_LOCATIONS = ["F1", "F2", "T1", "T2", "T3", "T4"]
DISCONTINUED_LOCATIONS = ["S1", "S2", "S3", "Spur"]
INCLUDE_FA_LOCATIONS = False

PLANNED_BUFFER_DAYS = []
IMPORT_PAINT_SCHEDULE = False

methods = ["FIFO", "SPT", "LPT", "Critical Path", "Shortest Queue"]
SELECTED_METHOD = "FIFO"

EXPORT_TO_EXCEL = True
EXPORT_PATH = OUTPUT_DIR
EXPORT_TO_FGI_LIVESTATE = True

CODECELL_OUTPUT = True


@dataclass
class SchedulerConfig:
    STARTDATE: str = STARTDATE
    ENDDATE: str = ENDDATE
    FORECAST_UNTIL_COMPLETION: bool = FORECAST_UNTIL_COMPLETION
    FORECAST_CAP_DAYS: int = FORECAST_CAP_DAYS
    PLANNED_BUFFER_DAYS: list = None
    EXPORT_TO_EXCEL: bool = EXPORT_TO_EXCEL
    EXPORT_TO_FGI_LIVESTATE: bool = EXPORT_TO_FGI_LIVESTATE
    CODECELL_OUTPUT: bool = CODECELL_OUTPUT

    def __post_init__(self):
        if self.PLANNED_BUFFER_DAYS is None:
            self.PLANNED_BUFFER_DAYS = []


def line(char="—", length=100):
    if not CODECELL_OUTPUT:
        return

    text = char
    while len(text) < length:
        text += char
    print(text + "\n")


def header(text, char="_", length=100):
    if not CODECELL_OUTPUT:
        return

    padding = [f"{char}| ", f" |{char}"]
    line_text = f"{char}| {text} |{char}"
    while len(line_text) < length:
        padding = [char + padding[0], padding[1] + char]
        line_text = padding[0] + text + padding[1]

    print(line_text)
