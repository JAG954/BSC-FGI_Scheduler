from conftest import make_ap, make_location


def test_fa_owned_locations_cannot_place_aps():
    loc = make_location("P1", owner="FA")

    assert loc.canPlace() is False


def test_occupied_locations_cannot_place_aps():
    loc = make_location("L1")
    loc.assign(make_ap())

    assert loc.canPlace() is False

