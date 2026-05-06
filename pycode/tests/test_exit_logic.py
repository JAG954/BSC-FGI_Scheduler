from conftest import make_ap, make_fgi, make_location, place_ap


def test_mark_dc_arrivals_pending_only_marks_exit_pending_aps_in_dc():
    fgi = make_fgi()
    a1 = make_location("A1", owner="DC", priority=1)
    a2 = make_location("A2", owner="DC", priority=2)
    fgi.add_Location("A1", a1)
    fgi.add_Location("A2", a2)
    exit_ap = place_ap(fgi, make_ap(1), a1)
    non_exit_ap = place_ap(fgi, make_ap(2), a2)
    exit_ap.exitPending = True
    non_exit_ap.exitPending = False

    marked = fgi.mark_dc_arrivals_pending()

    assert marked == ["1"]
    assert fgi.pendingExitLNs == ["1"]


def test_dc_ap_without_exit_pending_is_not_delivered():
    fgi = make_fgi()
    a1 = make_location("A1", owner="DC", priority=1)
    fgi.add_Location("A1", a1)
    ap = place_ap(fgi, make_ap(1), a1)
    ap.exitPending = False

    fgi.mark_dc_arrivals_pending()
    completed = fgi.complete_pending_exits(date="2024-01-02")

    assert completed == []
    assert "1" in fgi.APs

