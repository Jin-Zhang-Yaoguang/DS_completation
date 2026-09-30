import base64
import io

import numpy as np
import matplotlib.pyplot as plt
from IPython.display import HTML, display
from kaggle_environments.envs.kaggriculture.kaggriculture import (
    MARKET_I0,
    MARKET_PARAMS,
    market_price,
)

POSITION_DPI = 100
_ink = "#3C3B37"
panel_products = tuple(MARKET_PARAMS)
assert len(panel_products) == 9

daily_inventory = {
    item: [
        int(observation["market"]["inventory"][item])
        for observation in daily_observations
    ]
    for item in panel_products
}

position_figure, position_axes = plt.subplots(
    3, 3, figsize=(11.5, 9.4), dpi=POSITION_DPI, constrained_layout=True
)
season_scatter = None
for axis, item in zip(position_axes.flat, panel_products):
    params = MARKET_PARAMS[item]
    inventory_path = daily_inventory[item]
    low = min(min(inventory_path), MARKET_I0 - int(1.2 * params["T"]))
    high = max(max(inventory_path), MARKET_I0 + 40)
    pad = max(40, (high - low) // 10)
    inventory_grid = np.arange(low - pad, high + pad + 1)
    curve = np.array(
        [market_price(item, int(value)) for value in inventory_grid],
        dtype=float,
    )
    axis.plot(
        inventory_grid - MARKET_I0,
        curve / params["base"],
        color="0.60",
        lw=1.3,
        zorder=1,
    )
    axis.axvline(0.0, color="0.35", lw=0.8, ls="--", zorder=2)
    if params["below_func"] == "hinge":
        axis.axvline(
            -float(params["T"]), color="#C44E52", lw=1.0, ls=":", zorder=2
        )
    day_quotes = np.array(
        [market_price(item, int(value)) for value in inventory_path],
        dtype=float,
    )
    season_scatter = axis.scatter(
        np.array(inventory_path, dtype=float) - MARKET_I0,
        day_quotes / params["base"],
        c=day_axis,
        cmap="viridis",
        vmin=1,
        vmax=30,
        s=22,
        zorder=3,
        edgecolor="white",
        linewidth=0.4,
    )
    knee_note = " (knee dotted)" if params["below_func"] == "hinge" else ""
    axis.set_title(item.title() + knee_note, fontsize=9.5, color=_ink)
    axis.grid(alpha=0.18)
    axis.tick_params(labelsize=7.5)
for axis in position_axes[-1]:
    axis.set_xlabel(r"$I_r-I_0$", fontsize=8.5)
for row in position_axes:
    row[0].set_ylabel(r"$p_r/b_r$", fontsize=8.5)
position_figure.colorbar(
    season_scatter, ax=position_axes, shrink=0.82, pad=0.02, label="day"
)
position_figure.suptitle(
    "Where each product's season sits on its own quote curve",
    fontsize=12.5,
    color=_ink,
    weight="bold",
)
position_buffer = io.BytesIO()
position_figure.savefig(
    position_buffer, format="png", dpi=POSITION_DPI, facecolor="white"
)
plt.close(position_figure)
png_bytes = position_buffer.getvalue()
assert png_bytes[:8] == b"\x89PNG\r\n\x1a\n"
display(HTML(
    '<img src="data:image/png;base64,'
    + base64.b64encode(png_bytes).decode("ascii")
    + '" alt="Per-product season path on its own quote curve." '
    + 'style="display:block;width:100%;max-width:1150px;height:auto;'
    + 'margin:0 auto;" />'
))
