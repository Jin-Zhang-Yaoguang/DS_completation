from collect_scale_curriculum import move_toward


def test_move_toward_is_deterministic_and_reaches_each_axis():
    assert move_toward((5, 4), (3, 2)) == ["WEST"]
    assert move_toward((3, 4), (3, 2)) == ["NORTH"]
    assert move_toward((3, 2), (3, 2)) == ["PASS"]
