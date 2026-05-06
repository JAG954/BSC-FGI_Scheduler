def test_package_imports():
    from bsc_fgi_scheduler import AP, FGI, Location

    assert AP is not None
    assert Location is not None
    assert FGI is not None

