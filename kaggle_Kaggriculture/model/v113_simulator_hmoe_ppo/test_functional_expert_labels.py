"""Tests for teacher-independent functional MoE labels."""

import action_space as space


def test_unit_roles_are_teacher_independent():
    assert space.functional_unit_expert_label(
        {"farmer": ["WATER", 0, 0], "hands": [], "market": []}, 120,
    ) == 0
    assert space.functional_unit_expert_label(
        {"farmer": ["CARE", 0, 0], "hands": [], "market": []}, 120,
    ) == 1
    assert space.functional_unit_expert_label(
        {"farmer": ["NORTH"], "hands": [], "market": []}, 120,
    ) == 2
    assert space.functional_unit_expert_label(
        {"farmer": ["PASS"], "hands": [], "market": []}, 120,
    ) == 4


def test_market_roles_separate_sell_and_procurement():
    assert space.functional_market_expert_label(
        {"farmer": ["PASS"], "hands": [], "market": [["SELL", "MILK", 2]]}, 120,
    ) == 3
    assert space.functional_market_expert_label(
        {"farmer": ["PASS"], "hands": [], "market": [["BUY_SEED", "WHEAT", 2]]}, 120,
    ) == 4


def test_last_48_decisions_use_terminal_role():
    action = {"farmer": ["WATER", 0, 0], "hands": [], "market": [["SELL", "MILK", 2]]}
    assert space.functional_unit_expert_label(action, 670) == 0
    assert space.functional_market_expert_label(action, 670) == 3
    assert space.functional_unit_expert_label(action, 671) == 5
    assert space.functional_market_expert_label(action, 671) == 5
