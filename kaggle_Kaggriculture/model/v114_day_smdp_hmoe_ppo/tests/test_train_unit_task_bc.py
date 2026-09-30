import jax
import jax.numpy as jnp
import numpy as np

from model_unit_task_hmoe import UnitTaskHMoE
from train_unit_task_bc import class_weights, make_loss


def test_unit_task_model_and_loss_are_finite():
    batch_size = 3
    model = UnitTaskHMoE()
    inputs = {
        "global": jnp.zeros((batch_size, 60)),
        "board": jnp.zeros((batch_size, 2, 10, 10, 21)),
        "unit": jnp.zeros((batch_size, 121)),
    }
    params = model.init(jax.random.key(1), inputs["global"], inputs["board"], inputs["unit"])["params"]
    labels = {
        "role": jnp.asarray([0, 1, 2]),
        "operation": jnp.asarray([1, 8, 11]),
        "item": jnp.asarray([1, 0, 2]),
        "quantity_tier": jnp.asarray([0, 0, 2]),
        "target_x": jnp.asarray([1, 2, 3]),
        "target_y": jnp.asarray([4, 5, 6]),
        "duration": jnp.asarray([1, 2, 3]),
    }
    loss, metrics = make_loss(np.ones(4), np.ones(14))(
        params, model.apply, {**inputs, **labels}
    )
    assert np.isfinite(float(loss))
    assert set(metrics) >= {"loss", "role_accuracy", "operation_accuracy"}


def test_class_weights_ignore_missing_classes():
    weights = class_weights([100, 25, 0])
    assert weights[2] == 0
    assert weights[1] > weights[0]
