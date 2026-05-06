from conftest import make_ap, make_fgi


def test_request_move_sets_ap_state_and_move_queue():
    fgi = make_fgi()
    ap = make_ap()
    fgi.APs[ap.get_LN()] = ap

    assert fgi.request_move(ap.get_LN(), destination="A1", priority="exit") is True
    assert ap.moveReq is True
    assert ap.destination == "A1"
    assert ap.movePriority == "exit"
    assert ap.get_LN() in fgi.queues["move"]


def test_dequeue_all_removes_ln_from_move_task_and_labor_queues():
    fgi = make_fgi()
    ln = "1"
    fgi.queues["move"].extend([ln, ln])
    fgi.queues["FGI task"]["paint"].append(ln)
    fgi.queues["FGI task"]["compass"].append(ln)
    fgi.queues["labor"]["systems"].append(ln)

    assert fgi.dequeue("all", ln) is True
    assert ln not in fgi.queues["move"]
    assert ln not in fgi.queues["FGI task"]["paint"]
    assert ln not in fgi.queues["FGI task"]["compass"]
    assert ln not in fgi.queues["labor"]["systems"]

