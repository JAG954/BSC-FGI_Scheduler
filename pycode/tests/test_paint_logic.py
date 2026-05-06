import pandas as pd

from conftest import make_ap, make_fgi, make_location, place_ap


def test_entering_bsc_starts_paint_timing():
    fgi = make_fgi()
    origin = make_location("L1")
    bsc = make_location("BSC1")
    origin.set_time_to("BSC1", 1)
    fgi.add_Location("L1", origin)
    fgi.add_Location("BSC1", bsc)
    ap = place_ap(fgi, make_ap(1), origin)
    fgi.movetime_remaining = 8

    moved, _ = fgi.move_ap(ap.get_LN(), bsc, date=pd.Timestamp("2024-01-01"))

    assert moved is True
    assert ap.paintStartDate == pd.Timestamp("2024-01-01")
    assert ap.taskState == "paint"


def test_leaving_bsc_marks_painted_and_dequeues_paint():
    fgi = make_fgi()
    bsc = make_location("BSC1")
    dest = make_location("L1")
    bsc.set_time_to("L1", 1)
    fgi.add_Location("BSC1", bsc)
    fgi.add_Location("L1", dest)
    ap = place_ap(fgi, make_ap(1), bsc)
    fgi.queues["FGI task"]["paint"].append(ap.get_LN())
    fgi.movetime_remaining = 8

    moved, _ = fgi.move_ap(ap.get_LN(), dest, date=pd.Timestamp("2024-01-02"))

    assert moved is True
    assert ap.status["painted"] is True
    assert ap.get_LN() not in fgi.queues["FGI task"]["paint"]


def test_paint_schedule_requests_use_priority_and_override():
    today = pd.Timestamp("2024-01-01")
    fgi = make_fgi(paint_schedule={today + pd.Timedelta(days=1): {"BSC1": "1"}})
    fgi.add_Location("BSC1", make_location("BSC1"))
    ap = make_ap(1)
    fgi.APs[ap.get_LN()] = ap
    ap.moveReq = True
    ap.destination = "OLD"
    ap.movePriority = "normal"

    result = fgi.schedule_paint_moves(today)

    assert result["scheduled"] == ["1"]
    assert ap.moveReq is True
    assert ap.destination == "BSC1"
    assert ap.movePriority == "paint"
    assert fgi.queues["move"] == ["1"]

