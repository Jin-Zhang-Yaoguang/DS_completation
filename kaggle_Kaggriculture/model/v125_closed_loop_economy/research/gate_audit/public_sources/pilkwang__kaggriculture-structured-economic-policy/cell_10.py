import base64
from io import BytesIO

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from PIL import Image as PILImage
from IPython.display import HTML, display
from kaggle_environments import make
from kaggle_environments.envs.kaggriculture.kaggriculture import MARKET_PARAMS

SEASON_SEED = 217
SEASON_FRAME_MS = 1500
SEASON_DPI = 82

season_env = make(
    "kaggriculture",
    configuration={"episodeSteps": 720, "seed": SEASON_SEED},
    debug=True,
)
season_env.run([str(MAIN_PATH), "starter"])
season_steps = season_env.steps
assert len(season_steps) == 720
assert all(str(player.status) == "DONE" for player in season_steps[-1])

turns_per_day = int(season_env.configuration.turnsPerDay)
frame_indices = [
    min(turns_per_day * day - 1, len(season_steps) - 1)
    for day in range(1, 31)
]
assert len(frame_indices) == len(set(frame_indices)) == 30

daily_observations = [
    season_steps[index][0]["observation"] for index in frame_indices
]
day_axis = list(range(1, len(daily_observations) + 1))

CROP_COLORS = {
    "WHEAT": "#C99700",
    "CARROT": "#B84A00",
    "TOMATO": "#9E2B72",
    "STRAWBERRY": "#DB6FA9",
    "MELON": "#00795F",
}
PRODUCT_COLORS = {
    **CROP_COLORS,
    "EGG": "#56A8D8",
    "MILK": "#0059A1",
    "WOOL": "#A8641A",
    "FERTILIZER": "#6B4F9E",
}
CROP_LABELS = {
    "WHEAT": "Wh",
    "CARROT": "Ca",
    "TOMATO": "To",
    "STRAWBERRY": "St",
    "MELON": "Me",
}
ANIMAL_LABELS = {"CHICKEN": "Ch", "COW": "Co", "SHEEP": "Sh", "GOOSE": "Go"}
ANIMAL_PRODUCTS = {"CHICKEN": "EGG", "COW": "MILK", "SHEEP": "WOOL", "GOOSE": "EGG"}
SOIL = "#EFE7CE"
TILLED = "#E8D2A6"
WILD = "#C2CAA4"
WOOD = "#8B6F44"
WOOD_DARK = "#3A2412"
INK = "#3C3B37"
SCHEDULE_COLOR = "#0072B2"
STARTER_COLOR = "#D55E00"


def draw_schedule_farm(axis, farm, day=None):
    board_size = len(farm["tiles"])

    def rounded_tile(x, y, facecolor, edgecolor="white", linewidth=0.8, alpha=1.0):
        axis.add_patch(
            FancyBboxPatch(
                (x + 0.07, board_size - 1 - y + 0.07),
                0.86,
                0.86,
                boxstyle="round,pad=0,rounding_size=0.16",
                facecolor=facecolor,
                edgecolor=edgecolor,
                linewidth=linewidth,
                alpha=alpha,
            )
        )

    axis.add_patch(
        plt.Rectangle(
            (-0.15, -0.15),
            board_size + 0.30,
            board_size + 0.30,
            facecolor=SOIL,
            edgecolor="none",
            zorder=0,
        )
    )
    for y, row in enumerate(farm["tiles"]):
        for x, tile in enumerate(row):
            if tile == "LOCKED":
                rounded_tile(x, y, WILD, "#B3BD94")
                continue
            rounded_tile(x, y, TILLED, SOIL)
            if not isinstance(tile, dict):
                continue
            kind = tile.get("kind")
            center = (x + 0.50, board_size - 1 - y + 0.50)
            if kind == "PLANT":
                crop = tile["crop"]
                harvestable = tile.get("yield_units", 0) > 0
                rounded_tile(
                    x, y, CROP_COLORS[crop], alpha=1.0 if harvestable else 0.45
                )
                axis.text(
                    *center,
                    CROP_LABELS[crop],
                    ha="center",
                    va="center",
                    fontsize=5.5,
                    color="white" if harvestable else INK,
                    weight="bold",
                    zorder=6,
                )
                if harvestable:
                    axis.plot(
                        center[0] + 0.25,
                        center[1] + 0.25,
                        "o",
                        markersize=2.8,
                        markerfacecolor="white",
                        markeredgecolor="none",
                        zorder=7,
                    )
                fertilized_until = tile.get("fertilized_until_day", -1)
                if (
                    day is not None
                    and fertilized_until is not None
                    and int(fertilized_until) >= int(day)
                ):
                    axis.plot(
                        center[0] - 0.25,
                        center[1] + 0.25,
                        marker="D",
                        markersize=4.8,
                        markerfacecolor=PRODUCT_COLORS["FERTILIZER"],
                        markeredgecolor="white",
                        markeredgewidth=0.7,
                        zorder=7,
                    )
            elif kind == "WEED":
                rounded_tile(x, y, "#6E7351", alpha=0.60)
                axis.text(
                    *center,
                    "x",
                    ha="center",
                    va="center",
                    fontsize=7,
                    color="white",
                    weight="bold",
                    zorder=6,
                )
            elif "animal" in tile:
                animal = tile["animal"]
                rounded_tile(x, y, PRODUCT_COLORS[ANIMAL_PRODUCTS[animal]])
                axis.text(
                    *center,
                    ANIMAL_LABELS[animal],
                    ha="center",
                    va="center",
                    fontsize=5.5,
                    color="white",
                    weight="bold",
                    zorder=6,
                )
            elif kind in ("COOP", "PASTURE"):
                rounded_tile(x, y, WOOD, alpha=0.55)
                axis.text(
                    *center,
                    "Cp" if kind == "COOP" else "Pa",
                    ha="center",
                    va="center",
                    fontsize=5.5,
                    color="white",
                    weight="bold",
                    zorder=6,
                )

    half = board_size / 2
    axis.plot(
        [half, half], [0, board_size],
        color=WOOD_DARK, linewidth=2.1, alpha=0.82, zorder=4,
    )
    axis.plot(
        [0, board_size], [half, half],
        color=WOOD_DARK, linewidth=2.1, alpha=0.82, zorder=4,
    )
    axis.add_patch(
        FancyBboxPatch(
            (half - 0.62, half - 0.62),
            1.24,
            1.24,
            boxstyle="round,pad=0,rounding_size=0.18",
            facecolor=WOOD_DARK,
            edgecolor=SOIL,
            linewidth=1.5,
            zorder=7,
        )
    )
    axis.text(
        half, half, "shed",
        ha="center", va="center", fontsize=6.2, color=SOIL, zorder=8,
    )

    farmer_x, farmer_y = farm["farmer"]
    axis.plot(
        farmer_x + 0.50,
        board_size - 1 - farmer_y + 0.50,
        marker="*",
        markersize=10,
        markerfacecolor=SCHEDULE_COLOR,
        markeredgecolor="white",
        markeredgewidth=1.0,
        zorder=9,
    )
    for hand_x, hand_y in farm.get("hands", []):
        axis.plot(
            hand_x + 0.50,
            board_size - 1 - hand_y + 0.50,
            "o",
            markersize=5,
            markerfacecolor=SCHEDULE_COLOR,
            markeredgecolor="white",
            markeredgewidth=0.9,
            zorder=9,
        )

    axis.set_xlim(-0.20, board_size + 0.20)
    axis.set_ylim(-0.20, board_size + 0.20)
    axis.set_aspect("equal")
    axis.axis("off")
    axis.grid(False)


PRICE_PRODUCTS = tuple(MARKET_PARAMS)
bank_history = {
    "Schedule": [
        float(observation["farms"][0]["money"])
        for observation in daily_observations
    ],
    "Starter": [
        float(observation["farms"][1]["money"])
        for observation in daily_observations
    ],
}
price_history = {
    item: [
        float(observation["market"]["prices"][item])
        / MARKET_PARAMS[item]["base"]
        for observation in daily_observations
    ]
    for item in PRICE_PRODUCTS
}

bank_ceiling = 1.08 * max(max(values) for values in bank_history.values())
all_price_ratios = [
    value for values in price_history.values() for value in values
]
ratio_span = max(all_price_ratios) - min(all_price_ratios)
ratio_pad = max(0.05, 0.08 * ratio_span)
ratio_limits = (
    min(all_price_ratios) - ratio_pad,
    max(all_price_ratios) + ratio_pad,
)

figure = plt.figure(figsize=(11.5, 6.2), dpi=SEASON_DPI, facecolor="white")
grid = figure.add_gridspec(
    2, 2, width_ratios=(1.02, 1.30), height_ratios=(1, 1)
)
farm_axis = figure.add_subplot(grid[:, 0])
bank_axis = figure.add_subplot(grid[0, 1])
market_axis = figure.add_subplot(grid[1, 1])
figure.subplots_adjust(
    left=0.035, right=0.98, bottom=0.10, top=0.90, wspace=0.24, hspace=0.40
)


def style_series_axis(axis):
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    axis.grid(alpha=0.20, linewidth=0.7)
    axis.tick_params(labelsize=8)


def render_season_frame(frame_number):
    farm_axis.clear()
    bank_axis.clear()
    market_axis.clear()

    observation = daily_observations[frame_number]
    farm = observation["farms"][0]
    draw_schedule_farm(
        farm_axis, farm, day=int(observation.get("day", 0) or 0)
    )

    tiles = [tile for row in farm["tiles"] for tile in row]
    plant_count = sum(
        isinstance(tile, dict) and tile.get("kind") == "PLANT"
        for tile in tiles
    )
    animal_count = sum(
        isinstance(tile, dict) and "animal" in tile for tile in tiles
    )
    unlocked = len(farm.get("unlocked_quadrants", []))
    farm_axis.set_title(
        f"Schedule farm - ${farm['money']:,.0f}",
        fontsize=11.5,
        color=INK,
        weight="bold",
        pad=8,
    )
    farm_axis.text(
        0.5,
        -0.035,
        (
            "tile codes: crop, animal, pasture/coop - white dot: "
            "harvestable - purple diamond: active fertilizer"
        ),
        transform=farm_axis.transAxes,
        ha="center",
        va="top",
        fontsize=6.9,
        color="#6A6861",
        linespacing=1.35,
    )

    visible_days = day_axis[: frame_number + 1]
    bank_axis.plot(
        visible_days,
        bank_history["Schedule"][: frame_number + 1],
        color=SCHEDULE_COLOR,
        linewidth=2.4,
        label="Schedule",
    )
    bank_axis.plot(
        visible_days,
        bank_history["Starter"][: frame_number + 1],
        color=STARTER_COLOR,
        linewidth=2.2,
        label="Starter",
    )
    for label, color in (
        ("Schedule", SCHEDULE_COLOR),
        ("Starter", STARTER_COLOR),
    ):
        bank_axis.scatter(
            visible_days[-1],
            bank_history[label][frame_number],
            s=22,
            color=color,
            edgecolor="white",
            linewidth=0.7,
            zorder=5,
        )
    bank_axis.set_xlim(1, 30)
    bank_axis.set_ylim(0, bank_ceiling)
    bank_axis.set_title(
        "Terminal objective: coins in the bank",
        fontsize=11,
        color=INK,
        weight="bold",
    )
    bank_axis.set_xlabel("day", fontsize=8.5)
    bank_axis.set_ylabel("coins", fontsize=8.5)
    bank_axis.legend(loc="upper left", frameon=False, fontsize=7.5, ncol=2)
    style_series_axis(bank_axis)

    for item in PRICE_PRODUCTS:
        market_axis.plot(
            visible_days,
            price_history[item][: frame_number + 1],
            color=PRODUCT_COLORS[item],
            linewidth=1.6,
            label=item.title(),
        )
        market_axis.scatter(
            visible_days[-1],
            price_history[item][frame_number],
            s=12,
            color=PRODUCT_COLORS[item],
            edgecolor="white",
            linewidth=0.5,
            zorder=5,
        )
    market_axis.axhline(
        1.0, color="#7A7770", linewidth=0.9, linestyle="--", alpha=0.75
    )
    market_axis.set_xlim(1, 30)
    market_axis.set_ylim(*ratio_limits)
    market_axis.set_title(
        "Shared market: quote / base price",
        fontsize=11,
        color=INK,
        weight="bold",
    )
    market_axis.set_xlabel("day", fontsize=8.5)
    market_axis.set_ylabel("relative price", fontsize=8.5)
    market_axis.legend(loc="upper left", frameon=False, fontsize=6.4, ncol=3)
    style_series_axis(market_axis)

    figure.suptitle(
        (
            f"Deterministic season - day {frame_number + 1}/30 - "
            f"{unlocked} {'quadrant' if unlocked == 1 else 'quadrants'} - "
            f"{plant_count} crops - {animal_count} animals - "
            f"{len(farm.get('hands', []))} hands"
        ),
        fontsize=13,
        color=INK,
        weight="bold",
        y=0.965,
    )


rendered_frames = []
for frame_number in range(len(frame_indices)):
    render_season_frame(frame_number)
    frame_buffer = BytesIO()
    figure.savefig(
        frame_buffer, format="png", dpi=SEASON_DPI, facecolor="white"
    )
    frame_buffer.seek(0)
    with PILImage.open(frame_buffer) as frame_image:
        rendered_frames.append(frame_image.convert("RGBA"))

animation_buffer = BytesIO()
rendered_frames[0].save(
    animation_buffer,
    format="GIF",
    save_all=True,
    append_images=rendered_frames[1:],
    duration=SEASON_FRAME_MS,
    loop=0,
    disposal=2,
    optimize=True,
)
plt.close(figure)
for frame_image in rendered_frames:
    frame_image.close()
gif_bytes = animation_buffer.getvalue()

with PILImage.open(BytesIO(gif_bytes)) as rendered_gif:
    gif_dimensions = rendered_gif.size
    gif_frames = rendered_gif.n_frames
    gif_loop = rendered_gif.info.get("loop")

assert gif_frames == 30
assert gif_loop == 0
assert gif_bytes[:6] in (b"GIF87a", b"GIF89a")

animation_alt = (
    "Thirty-day deterministic farm, bank, and shared-market season "
    "under the committed program."
)
gif_base64 = base64.b64encode(gif_bytes).decode("ascii")
animation_html = (
    '<img src="data:image/gif;base64,'
    + gif_base64
    + '" alt="'
    + animation_alt
    + f'" width="{gif_dimensions[0]}" height="{gif_dimensions[1]}" '
    + 'style="display:block;width:100%;max-width:'
    + f'{gif_dimensions[0]}px;height:auto;margin:0 auto;" />'
)
display(HTML(animation_html))
