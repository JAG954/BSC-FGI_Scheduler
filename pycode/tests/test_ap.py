from conftest import make_ap


def test_is_exit_ready_is_side_effect_free():
    ap = make_ap()
    ap.status.update(
        {
            "compassCalibrated": True,
            "painted": True,
            "structure": True,
            "systems": True,
            "declam": True,
            "test": True,
        }
    )
    before = ap.status.copy()

    assert ap.is_exit_ready() is False
    assert ap.status == before


def test_complete_btg_consumes_budget_and_completion_flag():
    ap = make_ap()

    consumed, complete = ap.complete_BTG("systems", btg_budget=3, byLabor=True)

    assert consumed == 3
    assert complete is False
    assert ap.FGI_btg["systems"] == 2
    assert ap.btg["p2"] == 2
    assert ap.btg["tot"] == 7

