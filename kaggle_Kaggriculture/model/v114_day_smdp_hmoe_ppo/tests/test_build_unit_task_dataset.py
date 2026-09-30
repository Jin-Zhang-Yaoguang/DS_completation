from build_unit_task_dataset import infer_task, quantity_tier, role_for


def test_infer_task_holds_move_sequence_until_operation():
    positions = [[(0, 0)], [(1, 0)], [(2, 0)], [(2, 0)]]
    orders = [[["EAST"]], [["EAST"]], [["PLANT", "WHEAT"]], [["PASS"]]]
    assert infer_task(0, 0, positions, orders, 24) == (2, 0, "PLANT", "WHEAT", 0, 2)


def test_infer_task_falls_back_to_bounded_rest():
    positions = [[(3, 4)] for _ in range(5)]
    orders = [[["PASS"]] for _ in range(5)]
    assert infer_task(0, 0, positions, orders, 3) == (3, 4, "REST", "NONE", 0, 3)


def test_roles_and_quantity_tiers_are_deterministic():
    assert role_for("HARVEST") == 0
    assert role_for("CARE") == 1
    assert role_for("DROP") == 2
    assert role_for("REST") == 3
    assert quantity_tier(8) == 5
