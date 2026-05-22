from embscript.phase1.stitch_budget import within_tolerance


def test_within_tolerance_inside_band():
    assert within_tolerance(5050, 5000)
    assert within_tolerance(4750, 5000)


def test_within_tolerance_outside_band():
    assert not within_tolerance(5500, 5000)
    assert not within_tolerance(4500, 5000)
