import pandas as pd

from conftest import make_ap, make_fgi, make_location, place_ap


def add_compass_locations(fgi):
    for name in ["CR1", "CR2", "CR3"]:
        fgi.add_Location(name, make_location(name, priority=1))


def test_compass_completion_only_happens_for_queue_head_in_cr3():
    fgi = make_fgi()
    add_compass_locations(fgi)
    head = place_ap(fgi, make_ap(1), fgi.Locations["CR3"])
    other = make_ap(2)
    fgi.APs[other.get_LN()] = other
    fgi.queues["FGI task"]["compass"] = ["1", "2"]
    head.compassStartDate = pd.Timestamp("2024-01-01")

    result = fgi.schedule_compass_moves(pd.Timestamp("2024-01-02"))

    assert result["completed"] == "1"
    assert head.status["compassCalibrated"] is True
    assert other.status["compassCalibrated"] is False


def test_non_head_cr3_occupant_does_not_complete_compass():
    fgi = make_fgi()
    add_compass_locations(fgi)
    head = make_ap(1)
    non_head = place_ap(fgi, make_ap(2), fgi.Locations["CR3"])
    fgi.APs[head.get_LN()] = head
    fgi.queues["FGI task"]["compass"] = ["1", "2"]
    non_head.compassStartDate = pd.Timestamp("2024-01-01")

    result = fgi.schedule_compass_moves(pd.Timestamp("2024-01-02"))

    assert result["completed"] is None
    assert result["blocked_by"] == "2"
    assert non_head.status["compassCalibrated"] is False
    assert fgi.queues["FGI task"]["compass"][0] == "1"

