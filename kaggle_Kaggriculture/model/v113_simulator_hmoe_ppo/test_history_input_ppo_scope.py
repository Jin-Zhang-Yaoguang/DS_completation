"""Unit tests for the history-only PPO residual parameter contract."""

import jax.numpy as jnp
import numpy as np

from train_sequence_action_ppo import (
    HIDDEN,
    NUM_EXPERTS,
    audit_expert_slot_scope,
    audit_history_input_scope,
    audit_market_memory_expert_scope,
    audit_market_memory_coordinated_scope,
    mask_expert_slot_gradients,
    mask_history_input_gradients,
    mask_market_memory_expert_gradients,
    mask_market_memory_coordinated_gradients,
)


def _tree():
    return {
        "own_global_dense": {
            "kernel": jnp.arange(12, dtype=jnp.float32).reshape(6, 2),
            "bias": jnp.ones((2,), dtype=jnp.float32),
        },
        "unit_head": {"kernel": jnp.ones((2, 3), dtype=jnp.float32)},
    }


def test_gradient_mask_keeps_only_appended_rows():
    masked = mask_history_input_gradients(_tree(), history_features=2)
    kernel = np.asarray(masked["own_global_dense"]["kernel"])
    assert np.array_equal(kernel[:4], np.zeros((4, 2), dtype=np.float32))
    assert np.array_equal(kernel[4:], np.arange(12, dtype=np.float32).reshape(6, 2)[4:])
    assert not np.any(np.asarray(masked["own_global_dense"]["bias"]))
    assert not np.any(np.asarray(masked["unit_head"]["kernel"]))


def test_scope_audit_accepts_only_history_row_change():
    before = _tree()
    after = _tree()
    after["own_global_dense"]["kernel"] = after["own_global_dense"]["kernel"].at[4:, :].add(0.5)
    report = audit_history_input_scope(before, after, history_features=2)
    assert report["passed"]
    assert report["base_input_rows_bitwise_equal"]
    assert report["non_target_parameters_bitwise_equal"]


def test_scope_audit_rejects_base_row_change():
    before = _tree()
    after = _tree()
    after["own_global_dense"]["kernel"] = after["own_global_dense"]["kernel"].at[0, 0].add(0.5)
    report = audit_history_input_scope(before, after, history_features=2)
    assert not report["passed"]
    assert not report["base_input_rows_bitwise_equal"]


def _projection_tree():
    width = NUM_EXPERTS * HIDDEN
    return {
        "unit_expert_projection": {
            "kernel": jnp.ones((4, width), dtype=jnp.float32),
            "bias": jnp.ones((width,), dtype=jnp.float32),
        },
        "market_expert_projection": {
            "kernel": jnp.arange(4 * width, dtype=jnp.float32).reshape(4, width),
            "bias": jnp.arange(width, dtype=jnp.float32),
        },
        "market_memory_dense": {
            "kernel": jnp.ones((36, 256), dtype=jnp.float32),
            "bias": jnp.ones((256,), dtype=jnp.float32),
        },
        "unit_head": {"kernel": jnp.ones((4, 3), dtype=jnp.float32)},
    }


def test_expert_slot_gradient_mask_keeps_only_market_slot():
    slot = 5
    masked = mask_expert_slot_gradients(_projection_tree(), "market", slot)
    start, stop = slot * HIDDEN, (slot + 1) * HIDDEN
    market_kernel = np.asarray(masked["market_expert_projection"]["kernel"])
    assert not np.any(market_kernel[..., :start])
    assert not np.any(market_kernel[..., stop:])
    assert np.array_equal(
        market_kernel[..., start:stop],
        np.asarray(_projection_tree()["market_expert_projection"]["kernel"])[..., start:stop],
    )
    assert not np.any(np.asarray(masked["unit_expert_projection"]["kernel"]))


def test_expert_slot_audit_accepts_only_selected_market_slice():
    slot = 5
    before = _projection_tree()
    after = _projection_tree()
    start, stop = slot * HIDDEN, (slot + 1) * HIDDEN
    after["market_expert_projection"]["kernel"] = (
        after["market_expert_projection"]["kernel"].at[..., start:stop].add(0.25)
    )
    report = audit_expert_slot_scope(before, after, "market", slot)
    assert report["passed"]
    assert report["outside_target_slot_bitwise_equal"]


def test_expert_slot_audit_rejects_other_slot_change():
    before = _projection_tree()
    after = _projection_tree()
    after["market_expert_projection"]["bias"] = (
        after["market_expert_projection"]["bias"].at[0].add(0.25)
    )
    report = audit_expert_slot_scope(before, after, "market", 5)
    assert not report["passed"]
    assert not report["outside_target_slot_bitwise_equal"]


def test_market_memory_mask_keeps_encoder_and_one_market_slot():
    slot = 4
    masked = mask_market_memory_expert_gradients(_projection_tree(), slot)
    assert np.array_equal(
        np.asarray(masked["market_memory_dense"]["kernel"]),
        np.asarray(_projection_tree()["market_memory_dense"]["kernel"]),
    )
    start, stop = slot * HIDDEN, (slot + 1) * HIDDEN
    projection = np.asarray(masked["market_expert_projection"]["kernel"])
    assert not np.any(projection[..., :start])
    assert not np.any(projection[..., stop:])
    assert not np.any(np.asarray(masked["unit_expert_projection"]["kernel"]))


def test_market_memory_audit_accepts_exact_scope():
    slot = 4
    start, stop = slot * HIDDEN, (slot + 1) * HIDDEN
    before = _projection_tree()
    after = _projection_tree()
    after["market_memory_dense"]["kernel"] = (
        after["market_memory_dense"]["kernel"].at[0, 0].add(0.5)
    )
    after["market_expert_projection"]["bias"] = (
        after["market_expert_projection"]["bias"].at[start:stop].add(0.25)
    )
    report = audit_market_memory_expert_scope(before, after, slot)
    assert report["passed"]
    assert report["outside_market_memory_and_target_slot_bitwise_equal"]


def test_market_memory_audit_rejects_unit_change():
    before = _projection_tree()
    after = _projection_tree()
    after["market_memory_dense"]["bias"] = after["market_memory_dense"]["bias"].at[0].add(0.5)
    after["market_expert_projection"]["bias"] = after["market_expert_projection"]["bias"].at[4 * HIDDEN].add(0.5)
    after["unit_head"]["kernel"] = after["unit_head"]["kernel"].at[0, 0].add(0.5)
    report = audit_market_memory_expert_scope(before, after, 4)
    assert not report["passed"]


def test_coordinated_memory_mask_keeps_both_matching_slots():
    slot = 5
    masked = mask_market_memory_coordinated_gradients(_projection_tree(), slot)
    start, stop = slot * HIDDEN, (slot + 1) * HIDDEN
    for module in ("unit_expert_projection", "market_expert_projection"):
        value = np.asarray(masked[module]["kernel"])
        assert not np.any(value[..., :start])
        assert not np.any(value[..., stop:])
        assert np.any(value[..., start:stop])


def test_coordinated_memory_audit_accepts_exact_scope():
    slot = 5
    start = slot * HIDDEN
    before = _projection_tree()
    after = _projection_tree()
    after["market_memory_dense"]["kernel"] = after["market_memory_dense"]["kernel"].at[0, 0].add(0.1)
    after["unit_expert_projection"]["bias"] = after["unit_expert_projection"]["bias"].at[start].add(0.1)
    after["market_expert_projection"]["bias"] = after["market_expert_projection"]["bias"].at[start].add(0.1)
    assert audit_market_memory_coordinated_scope(before, after, slot)["passed"]
