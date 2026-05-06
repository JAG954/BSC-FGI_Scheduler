from __future__ import annotations

from pathlib import Path

import pytest

from bsc_fgi_scheduler.ap import AP
from bsc_fgi_scheduler.fgi import FGI
from bsc_fgi_scheduler.location import Location


@pytest.fixture(autouse=True)
def quiet_notebook_output(monkeypatch):
    import bsc_fgi_scheduler.ap as ap_mod
    import bsc_fgi_scheduler.config as config_mod
    import bsc_fgi_scheduler.fgi as fgi_mod
    import bsc_fgi_scheduler.location as location_mod

    for module in [ap_mod, config_mod, fgi_mod, location_mod]:
        monkeypatch.setattr(module, "CODECELL_OUTPUT", False, raising=False)


@pytest.fixture
def repo_root() -> Path:
    current = Path(__file__).resolve()
    for path in current.parents:
        if (path / "pycode").is_dir() and (path / "data").is_dir():
            return path
    raise RuntimeError("Could not locate repository root containing pycode/ and data/.")


def make_ap(ln=1, btg=None):
    return AP(
        LN=ln,
        faro="2024-01-01",
        toB1R=10,
        counters=0,
        btg=btg
        or {
            "tot": 10,
            "p0": 0,
            "p1": 0,
            "p2": 5,
            "p3": 0,
            "engines": 0,
            "doors": 0,
            "test": 0,
        },
    )


def make_location(name, owner="FGI", priority=0, date_online="Now"):
    return Location(priority=priority, dateOnline=date_online, name=name, owner=owner)


def make_fgi(paint_schedule=None):
    labor = {
        1: {"structure": 16, "systems": 60, "declam": 16, "test": 18},
        2: {"structure": 6, "systems": 14, "declam": 4, "test": 0},
        3: {"structure": 0, "systems": 0, "declam": 0, "test": 0},
    }
    cpj = {"structure": 6, "systems": 3.5, "declam": 3, "test": 8}
    return FGI(labor=labor, CPJ=cpj, paint_schedule=paint_schedule)


def place_ap(fgi, ap, location):
    fgi.APs[ap.get_LN()] = ap
    if location.name not in fgi.Locations:
        fgi.add_Location(location.name, location)
    location.assign(ap)
    ap.Location = location
    fgi.chickenTracks[location.name] = ap.get_LN()
    return ap
