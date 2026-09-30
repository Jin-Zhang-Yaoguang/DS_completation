"""v7.38_finance7: yhay81's frontier-state shop router (kernel v7), verbatim, plus our mirror front-run and chained financing of the first hire.

CHASSIS (external, credited): "three-day-shop-router" version 7 by Yusuke Hayashi
(yhay81), https://www.kaggle.com/code/yhay81/three-day-shop-router (Apache-2.0,
SPDX in sources). Native C++ policy hybrid_shopforge_3day_frontier_state_router_r5:
two tapes differing ONLY in the 72-turn block t360-431, decision at t=360 on
public frontier state (BAKERY & market fertilizer inventory <= 10232.5, or
PET_CAFE & rival plant tiles <= 64.5), six-day budget guard at 72-turn
boundaries, behind this ctypes bridge, byte-identical below except the relocated
future-import. policy.cpp sha256 abdb6b13cb91504409de0cf53679c5443f309f1fe937f676e68707830744392b,
submission_bridge.cpp sha256 a92ca5b78cae850987a7262122eb83ec9f9a313430e906e1ac08bfe1fd887ff1,
tape.inc sha256 30b724c3c905d0c03e4ef38d36f96fb7acbd6abef5371abbedee36ea3717e09f. agent.so is built from those sources
unmodified ON THE KAGGLE IMAGE (private kernel destbreso/v733-build-private,
g++ -O3 -std=c++17, ELF x86-64, 927424 bytes, sha256 d3b4e19dfd20f1d9b229d1d15cab9ee20068d100fb99fcf4c44051d59fb174ea;
dlopen and ABI version validated there). Registered as donor yhay81-threeday-router (v7_frontier/).

THIS AGENT CARRIES TWO LAYERS OF OURS, L_MFR and L_FINANCE. Its sibling
v7.37_finance carries a third, L_EDIT, a sell-schedule refinement measured on
the OTHER chassis; it is deliberately not in this one.

OUR FIRST LAYER (destbreso), lineage 7.D: the mirror front-run of v7.29-v7.32 (S16),
adapted to this chassis: the tapes reconverge at t432, so route identification
only matters inside the block window. MEASURED ON THIS CHASSIS 2026-09-03 at the
full-panel standard (64 shop worlds x both seats = 128): detector fired 126/128
and where it fired the layer wins 126/126, mean +3,129, median +3,173, min
+1,105, max +4,759; route identified 126/126 (90 r0, 36 r1). The 2 unfired
games are seed 74 from both seats, byte-identical play with margins -8,655 and
+8,655: the world's own seat asymmetry, the fail-closed control. Parity gate:
L_MFR=0 is byte-identical to the bare chassis, 12/12 games 0 diffs; false-positive
gate: L_MFR=1 vs three non-mirror donors, 12/12 games 0 diffs. Fail-closed
everywhere: no mirror -> byte-identical to the bare chassis; unknown route +
divergent next-sells -> no append.

OUR SECOND LAYER (destbreso, 2026-09-04), L_FINANCE: chained financing of the
HIRE order. On any turn whose market list contains a HIRE this farm cannot
fund, it PREPENDS a SELL at index 0 covering the shortfall from the shed. The
engine settles the market list by index, so the sell pays for the hires behind
it in the SAME turn. It adds no purchase and removes none.

THE DEFECT IT REPAIRS, measured on real ladder episodes rather than supposed.
The v<=6 opening buys 53 wheat and sells 48 to fund two cows, two sheep, five
hires and its seed, and lands within a few dollars of nothing. Whether it ends
day 0 on $29 or on $0 depends on the price the OPPONENT leaves: the dead games
are the ones against rivals who sell hard in days 0-2, 16 opening sell orders
against 6, banking a median of 158,152 against 84,184. Hands do not persist
overnight, so at t24, day 1 hour 0, the tape emits three HIREs costing $4 while
holding $0 and 3 WHEAT worth $28 each. It cannot pay four dollars with
eighty-four in the shed. No hand is ever taken on, nothing is worked, and the
season ends at exactly zero with an empty shed.

WHY NOT A CASH RESERVE, which was measured and rejected: reserves of 5, 10, 20
and 40, over windows of the first 24 and 72 turns, all remove the zeros and
take wins from 52 of 77 to 15. A reserve changes WHAT the tape buys, and a tape
is a fixed sequence whose later turns assume the earlier purchases happened, so
cancelling one detaches the rest of the season. Financing changes only the
ORDER, which the engine settles by index, so it cannot desynchronise the tape.

MEASURED, on the 179 episodes of the broken submission's own uncapped pool
(captured 2026-09-04), replayed at the recorded seed and seat with the
identity check passing 178 of 179 recorded banks to the dollar and the
recorded 49.7 % win rate reproduced exactly:
  zero banks   50 of 179  ->  0 of 179
  wins         89         ->  91
  in those 50 games the bank goes from a median of 0 to 76,976
Read the honest limit with it: the failure fires against rivals banking
158,152, so the recovered bank flips only 1 of those 50 games into a win. The
repair is worth about two wins in 179 and the removal of a failure mode that
was worsening, 18 % of games in the oldest quarter of the live record and
47.7 % in the newest.

CONTROL: with L_FINANCE = 0 the action dict is identical to the parent every
turn over three episodes, 0 differing turns of 2,157.

FAIL-CLOSED in three places, because the engine has no error channel: a missing
observation field, a market list already at the ten-order cap (never displace
an order, which is the reserve's failure mode), and a shed with nothing priced
above zero all return the action untouched.

ON THIS CHASSIS L_FINANCE IS INSURANCE, NOT A REPAIR: v7.33 has 0 zero-bank
games in 105 recorded episodes and 0 of 203 live, and the layer changes no
outcome on its own pool (0 discordant games of 204). It is carried so that the
two agents of a published pair differ in the CHASSIS and not in the layers.
"""

from __future__ import annotations

import ctypes
import sys
from collections.abc import Mapping
from pathlib import Path

_ITEMS = (
    "WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG",
    "MILK", "WOOL", "FERTILIZER", "GOOSE", "COW", "SHEEP",
)
_PRODUCTS = _ITEMS[:9]
_SHOPS = (
    "BAKERY", "BRUNCH_SPOT", "FARMERS_MARKET", "ICE_CREAM_SHOP",
    "PET_CAFE", "PIZZA_SHOP", "SMOOTHIE_SHOP", "YARN_STORE",
)
_SHOP_ID = {name: index for index, name in enumerate(_SHOPS)}
_KIND_ID = {
    None: 0, "EMPTY": 0, "SOIL": 0, "LOCKED": 1, "WEED": 2,
    "COOP": 3, "PASTURE": 4, "PLANT": 5,
}
_UNIT_OPS = (
    "PASS", "NORTH", "SOUTH", "EAST", "WEST", "PICKUP", "DROP",
    "PLACE", "PLANT", "WATER", "HARVEST", "FERTILIZE", "DIG",
    "BUILD_COOP", "BUILD_PASTURE", "FEED", "COLLECT_FERTILIZER", "CARE",
)
_MARKET_OPS = ("PASS", "HIRE", "BUY_LAND", "BUY_SEED", "BUY_PRODUCT", "BUY_ANIMAL", "SELL")
_BOARD = 10
_MAX_UNITS = 40
_MAX_SHOPS = 8
_LIBRARY = None


def _read(value, key, default=None):
    if isinstance(value, Mapping):
        return value.get(key, default)
    getter = getattr(value, "get", None)
    if callable(getter):
        return getter(key, default)
    return getattr(value, key, default)


class _PackedTile(ctypes.Structure):
    _pack_ = 1
    _fields_ = [("kind", ctypes.c_uint8)]


class _PackedFarm(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("money", ctypes.c_double),
        ("tiles", _PackedTile * _BOARD * _BOARD),
        ("n_units", ctypes.c_int32),
        ("n_quadrants", ctypes.c_int32),
        ("hires_today", ctypes.c_int32),
        ("shed", ctypes.c_int16 * len(_ITEMS)),
        ("inv", ctypes.c_int16 * len(_ITEMS) * _MAX_UNITS),
    ]


class _PackedObservation(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("step", ctypes.c_int32),
        ("n_shops", ctypes.c_int32),
        ("market_inventory", ctypes.c_int32 * len(_PRODUCTS)),
        ("market_prices", ctypes.c_int32 * len(_PRODUCTS)),
        ("shops", ctypes.c_uint8 * _MAX_SHOPS),
        ("farms", _PackedFarm * 2),
    ]


class _PackedAction(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("unit_ops", ctypes.c_uint8 * _MAX_UNITS),
        ("unit_args", ctypes.c_uint8 * _MAX_UNITS),
        ("unit_ns", ctypes.c_int16 * _MAX_UNITS),
        ("n_units", ctypes.c_int32),
        ("order_ops", ctypes.c_uint8 * 16),
        ("order_items", ctypes.c_uint8 * 16),
        ("order_ns", ctypes.c_int32 * 16),
        ("n_orders", ctypes.c_int32),
    ]


def _library():
    global _LIBRARY
    if _LIBRARY is None:
        extension = "dylib" if sys.platform == "darwin" else "so"
        # Kaggle's source loader does not define ``__file__``.  The compiled
        # function filename still points at the extracted top-level main.py.
        path = Path(_library.__code__.co_filename).resolve().parent / f"agent.{extension}"
        library = ctypes.CDLL(str(path))
        library.kag_submission_abi_version.restype = ctypes.c_uint32
        library.kag_submission_act.argtypes = [
            ctypes.POINTER(_PackedObservation),
            ctypes.c_int,
            ctypes.c_int,
            ctypes.POINTER(_PackedAction),
        ]
        library.kag_submission_act.restype = ctypes.c_int
        if int(library.kag_submission_abi_version()) != 1:
            raise RuntimeError("ShopForge SixDay Guard submission ABI mismatch")
        _LIBRARY = library
    return _LIBRARY


def _fill_counts(target, mapping, names):
    for index, name in enumerate(names):
        target[index] = int(_read(mapping, name, 0) or 0) if mapping else 0


def _fill_tile(dst, tile):
    if tile is None:
        return
    if isinstance(tile, str):
        dst.kind = _KIND_ID.get(tile, 0)
        return
    kind = _read(tile, "kind")
    if kind == "PLANT" or _read(tile, "crop"):
        dst.kind = _KIND_ID["PLANT"]
        return
    dst.kind = _KIND_ID.get(kind, 0)


# ---------------------------------------------------------------------------
# The turn, derived so that NO SINGLE FIELD can freeze the agent (destbreso,
# 2026-09-03). The bridge used to read `observation["step"]` with an `or 0`
# fallback; where that field did not arrive, the fallback replayed turn 0 for
# all 719 turns, and 19 of v7.32's 122 recorded ladder episodes banked exactly
# 0 with status DONE and no exception anywhere. Deriving from day*24+hour
# instead only MOVES the single point of failure: the same probe then collapses
# when `day` is the field that is missing.
#
# So take every reading the observation offers, and carry our own count as the
# floor. `step` and `day*24+hour` agree wherever both exist (1,438 checks, 0
# mismatches); where one is missing the other answers; where both are missing
# the count answers, because this function is called exactly once per turn.
# The max is safe in every combination: a partial reading (an `hour` with no
# `day`) is always an UNDER-estimate, and the count overrides it.

_TURN_COUNT = {}


def _derive_turn(observation):
    seat = _read(observation, "player", 0)
    try:
        seat = int(seat)
    except (TypeError, ValueError):
        seat = 0
    readings = []
    raw = _read(observation, "step", None)
    if raw is not None:
        try:
            readings.append(int(raw))
        except (TypeError, ValueError):
            pass
    day, hour = _read(observation, "day", None), _read(observation, "hour", None)
    if day is not None or hour is not None:
        try:
            readings.append(int(day or 0) * 24 + int(hour or 0))
        except (TypeError, ValueError):
            pass
    prev = _TURN_COUNT.get(seat)
    counted = 0 if prev is None else prev + 1
    # A genuinely fresh episode in a reused process: every reading says 0 AND
    # the farm has not been touched. Without this the count would never reset.
    if readings and max(readings) == 0:
        farm = None
        farms = _read(observation, "farms", None) or []
        if len(farms) > seat:
            farm = farms[seat]
        if farm is None or not (_read(farm, "hands", []) or []):
            _TURN_COUNT[seat] = 0
            return 0
    turn = max(readings + [counted])
    turn = max(0, min(turn, 718))
    _TURN_COUNT[seat] = turn
    return turn


def _pack_observation(observation, seat):
    packed = _PackedObservation()
    step = _derive_turn(observation)
    packed.step = step
    market = _read(observation, "market", {}) or {}
    _fill_counts(packed.market_inventory, _read(market, "inventory", {}) or {}, _PRODUCTS)
    _fill_counts(packed.market_prices, _read(market, "prices", {}) or {}, _PRODUCTS)
    shops = list(_read(_read(observation, "town", {}) or {}, "unlocked_shops", []) or [])
    packed.n_shops = min(len(shops), _MAX_SHOPS)
    for index, shop in enumerate(shops[:_MAX_SHOPS]):
        packed.shops[index] = _SHOP_ID[str(shop)]

    farms = list(_read(observation, "farms", []) or [])
    if len(farms) != 2:
        raise ValueError("ShopForge needs exactly two public farms")
    for player, farm in enumerate(farms):
        dest = packed.farms[player]
        dest.money = float(_read(farm, "money", 0) or 0)
        positions = [_read(farm, "farmer", [0, 0]), *list(_read(farm, "hands", []) or [])]
        dest.n_units = max(1, min(len(positions), _MAX_UNITS))
        dest.n_quadrants = len(list(_read(farm, "unlocked_quadrants", []) or []))
        dest.hires_today = int(_read(farm, "hires_today", 0) or 0)
        tiles = list(_read(farm, "tiles", []) or [])
        for y, row in enumerate(tiles[:_BOARD]):
            for x, tile in enumerate(list(row or [])[:_BOARD]):
                _fill_tile(dest.tiles[y][x], tile)

    private = _read(observation, "private", {}) or {}
    own = packed.farms[seat]
    _fill_counts(own.shed, _read(private, "shed", {}) or {}, _ITEMS)
    inventories = list(_read(private, "inventories", []) or [])
    for unit, carried in enumerate(inventories[:_MAX_UNITS]):
        _fill_counts(own.inv[unit], carried or {}, _ITEMS)
    return packed


def _unit_order(op, arg, quantity):
    name = _UNIT_OPS[op] if 0 <= op < len(_UNIT_OPS) else "PASS"
    if name in {"PLANT", "PICKUP", "PLACE"}:
        item = _ITEMS[arg] if 0 <= arg < len(_ITEMS) else _ITEMS[0]
        return [name, item] if quantity == 1 else [name, item, int(quantity)]
    return [name]


def _market_order(op, item, quantity):
    name = _MARKET_OPS[op] if 0 <= op < len(_MARKET_OPS) else "PASS"
    if name == "PASS":
        return None
    if name in {"HIRE", "BUY_LAND"}:
        return [name]
    item_name = _ITEMS[item] if 0 <= item < len(_ITEMS) else _ITEMS[0]
    return [name, item_name, int(quantity)]


def _unpack_action(packed):
    n_units = max(1, min(int(packed.n_units), _MAX_UNITS))
    farmer = _unit_order(packed.unit_ops[0], packed.unit_args[0], packed.unit_ns[0])
    hands = [
        _unit_order(packed.unit_ops[index], packed.unit_args[index], packed.unit_ns[index])
        for index in range(1, n_units)
    ]
    market = []
    for index in range(max(0, min(int(packed.n_orders), 16))):
        order = _market_order(packed.order_ops[index], packed.order_items[index], packed.order_ns[index])
        if order is not None:
            market.append(order)
    return {"farmer": farmer, "hands": hands, "market": market}


def agent(observation, configuration=None):
    seat = int(_read(observation, "player", 0) or 0)
    packed = _pack_observation(observation, seat)
    episode_steps = int(_read(configuration or {}, "episodeSteps", 720) or 720)
    output = _PackedAction()
    status = _library().kag_submission_act(
        ctypes.byref(packed), seat, episode_steps, ctypes.byref(output)
    )
    if status != 0:
        raise RuntimeError("ShopForge native policy failed")
    return _unpack_action(output)


# ---------------------------------------------------------------------------
# OUR LAYER (destbreso). Everything above is yhay81's three-day router bridge
# verbatim (Apache-2.0, https://www.kaggle.com/code/yhay81/three-day-shop-router).
# L_MFR, the mirror front-run of our v7.29-v7.32 line (S16): detect a
# mirror by public farm-signature streak in t100-143, then from t144 append
# MY tape's next-turn non-WHEAT sells one turn early. The tape lives in the
# native tape.inc; its non-WHEAT sells are embedded below (generated from
# tape.inc, 2 routes x 719 turns; the two tapes are IDENTICAL outside the
# t=360 block decision and reconverge at t432, so outside the block the
# common tape serves and identification is needed only inside it).
# Inside the block the active route is identified by matching my own emitted
# market orders against both tapes at divergent turns, tolerant to the
# budget guard's edits (score per tape, lock on first strict lead).
# Fail-closed everywhere: unknown route + divergent next-sells -> no append.

import json as _json

L_MFR = 1                      # measured on THIS chassis (see docstring)
MFR_STREAK = 20
MFR_CAP = 10

_SELLS = {int(r): {int(t): v for t, v in d.items()}
          for r, d in _json.loads(r'''{"0":{"30":[["FERTILIZER",1]],"31":[["FERTILIZER",1]],"32":[["FERTILIZER",1]],"48":[["FERTILIZER",1]],"65":[["FERTILIZER",4]],"88":[["FERTILIZER",3]],"90":[["FERTILIZER",1]],"99":[["FERTILIZER",1]],"111":[["FERTILIZER",1]],"118":[["FERTILIZER",4]],"120":[["FERTILIZER",1]],"131":[["FERTILIZER",1]],"141":[["FERTILIZER",4]],"145":[["FERTILIZER",1]],"150":[["WOOL",10],["FERTILIZER",1]],"151":[["FERTILIZER",1]],"152":[["FERTILIZER",1]],"156":[["FERTILIZER",1]],"157":[["FERTILIZER",1]],"166":[["FERTILIZER",2]],"167":[["FERTILIZER",1]],"168":[["WOOL",2]],"174":[["FERTILIZER",2]],"175":[["FERTILIZER",1]],"176":[["FERTILIZER",3]],"177":[["FERTILIZER",1]],"188":[["FERTILIZER",1]],"192":[["FERTILIZER",1]],"195":[["MILK",12]],"212":[["FERTILIZER",3]],"214":[["FERTILIZER",4]],"217":[["FERTILIZER",1]],"218":[["FERTILIZER",1]],"221":[["FERTILIZER",1]],"226":[["WOOL",8]],"233":[["FERTILIZER",3]],"237":[["FERTILIZER",3]],"238":[["FERTILIZER",5]],"242":[["FERTILIZER",3]],"249":[["MELON",6]],"250":[["MELON",24]],"251":[["MELON",12]],"252":[["MELON",6]],"253":[["MELON",6]],"255":[["MELON",6]],"258":[["MILK",12],["FERTILIZER",5]],"264":[["MELON",12],["FERTILIZER",13]],"266":[["FERTILIZER",1]],"269":[["MILK",6]],"289":[["FERTILIZER",14]],"293":[["WOOL",8]],"298":[["MILK",6]],"300":[["FERTILIZER",2]],"312":[["FERTILIZER",17]],"323":[["MILK",6]],"337":[["FERTILIZER",9]],"338":[["MILK",6],["FERTILIZER",1]],"339":[["MILK",3]],"340":[["MILK",6]],"341":[["MILK",3]],"342":[["WOOL",6]],"343":[["WOOL",6]],"360":[["MILK",3]],"362":[["FERTILIZER",7]],"372":[["FERTILIZER",11]],"375":[["MILK",15],["WOOL",14]],"381":[["STRAWBERRY",8]],"386":[["MILK",3],["FERTILIZER",10]],"396":[["STRAWBERRY",4],["FERTILIZER",4]],"400":[["WOOL",18]],"403":[["STRAWBERRY",12]],"407":[["MILK",9]],"409":[["MILK",3]],"413":[["FERTILIZER",10]],"417":[["MILK",6]],"423":[["WOOL",10]],"430":[["STRAWBERRY",10]],"431":[["STRAWBERRY",6]],"433":[["MILK",6],["WOOL",4]],"438":[["MILK",3]],"440":[["WOOL",6]],"446":[["FERTILIZER",10]],"451":[["STRAWBERRY",10]],"454":[["STRAWBERRY",14]],"457":[["WOOL",6]],"461":[["FERTILIZER",10]],"462":[["MILK",6]],"463":[["MILK",3]],"466":[["WOOL",4]],"472":[["MILK",9]],"475":[["STRAWBERRY",4]],"477":[["STRAWBERRY",6]],"478":[["STRAWBERRY",6]],"485":[["FERTILIZER",10]],"486":[["MILK",6],["WOOL",6]],"487":[["MILK",6],["WOOL",2]],"493":[["MILK",9],["WOOL",4]],"498":[["STRAWBERRY",10]],"502":[["STRAWBERRY",14]],"505":[["WOOL",10]],"509":[["FERTILIZER",10]],"510":[["MILK",6],["WOOL",2]],"511":[["MILK",6]],"517":[["MILK",9],["STRAWBERRY",8]],"522":[["FERTILIZER",14]],"523":[["STRAWBERRY",16]],"525":[["WOOL",6]],"529":[["WOOL",4]],"530":[["FERTILIZER",10]],"534":[["STRAWBERRY",6],["MILK",6],["WOOL",6]],"535":[["STRAWBERRY",6],["MILK",6],["WOOL",2]],"536":[["STRAWBERRY",6]],"540":[["FERTILIZER",6]],"541":[["STRAWBERRY",18],["MILK",9]],"546":[["STRAWBERRY",10]],"548":[["WOOL",8]],"550":[["STRAWBERRY",14]],"552":[["WOOL",11],["FERTILIZER",14]],"554":[["FERTILIZER",4]],"557":[["FERTILIZER",2]],"558":[["MILK",6]],"559":[["MILK",6]],"560":[["MILK",3]],"565":[["MILK",6]],"570":[["STRAWBERRY",14]],"576":[["MILK",27]],"582":[["STRAWBERRY",6],["WOOL",6],["FERTILIZER",9]],"583":[["STRAWBERRY",6],["WOOL",4]],"584":[["STRAWBERRY",6],["WOOL",6]],"585":[["STRAWBERRY",1],["WOOL",2]],"586":[["WOOL",18]],"589":[["STRAWBERRY",14]],"600":[["WOOL",3],["FERTILIZER",16]],"601":[["MILK",6]],"602":[["FERTILIZER",2]],"604":[["FERTILIZER",1]],"606":[["STRAWBERRY",6],["MILK",6]],"607":[["STRAWBERRY",3],["MILK",3]],"613":[["STRAWBERRY",14]],"614":[["MILK",9]],"620":[["WOOL",3]],"624":[["FERTILIZER",5]],"626":[["FERTILIZER",4]],"629":[["FERTILIZER",2]],"630":[["STRAWBERRY",6],["MILK",6],["WOOL",6]],"631":[["STRAWBERRY",6],["MILK",3],["WOOL",3],["FERTILIZER",2]],"632":[["STRAWBERRY",6]],"633":[["STRAWBERRY",6],["FERTILIZER",1]],"634":[["WOOL",9],["FERTILIZER",1]],"635":[["FERTILIZER",2]],"637":[["STRAWBERRY",14],["MILK",9],["FERTILIZER",1]],"640":[["WOOL",9]],"648":[["MILK",15]],"649":[["STRAWBERRY",10],["WOOL",3]],"654":[["STRAWBERRY",4],["FERTILIZER",13]],"656":[["WOOL",4]],"660":[["WOOL",8]],"669":[["MILK",3]],"673":[["MILK",9]],"674":[["CARROT",2],["FERTILIZER",15]],"678":[["STRAWBERRY",6],["MILK",3]],"679":[["STRAWBERRY",6]],"680":[["STRAWBERRY",6]],"681":[["STRAWBERRY",4]],"683":[["MILK",9]],"684":[["MILK",3]],"685":[["STRAWBERRY",22],["FERTILIZER",1]],"687":[["FERTILIZER",1]],"688":[["WOOL",12]],"689":[["FERTILIZER",1]],"690":[["FERTILIZER",1]],"691":[["CARROT",7],["FERTILIZER",2]],"693":[["FERTILIZER",1]],"698":[["FERTILIZER",14]],"704":[["CARROT",1]],"707":[["MILK",3]],"708":[["CARROT",4]],"711":[["WOOL",3]],"712":[["MILK",3]],"713":[["FERTILIZER",1]],"716":[["FERTILIZER",1]],"718":[["MILK",3]]},"1":{"30":[["FERTILIZER",1]],"31":[["FERTILIZER",1]],"32":[["FERTILIZER",1]],"48":[["FERTILIZER",1]],"65":[["FERTILIZER",4]],"88":[["FERTILIZER",3]],"90":[["FERTILIZER",1]],"99":[["FERTILIZER",1]],"111":[["FERTILIZER",1]],"118":[["FERTILIZER",4]],"120":[["FERTILIZER",1]],"131":[["FERTILIZER",1]],"141":[["FERTILIZER",4]],"145":[["FERTILIZER",1]],"150":[["WOOL",10],["FERTILIZER",1]],"151":[["FERTILIZER",1]],"152":[["FERTILIZER",1]],"156":[["FERTILIZER",1]],"157":[["FERTILIZER",1]],"166":[["FERTILIZER",2]],"167":[["FERTILIZER",1]],"168":[["WOOL",2]],"174":[["FERTILIZER",2]],"175":[["FERTILIZER",1]],"176":[["FERTILIZER",3]],"177":[["FERTILIZER",1]],"188":[["FERTILIZER",1]],"192":[["FERTILIZER",1]],"195":[["MILK",12]],"212":[["FERTILIZER",3]],"214":[["FERTILIZER",4]],"217":[["FERTILIZER",1]],"218":[["FERTILIZER",1]],"221":[["FERTILIZER",1]],"226":[["WOOL",8]],"233":[["FERTILIZER",3]],"237":[["FERTILIZER",3]],"238":[["FERTILIZER",5]],"242":[["FERTILIZER",3]],"249":[["MELON",6]],"250":[["MELON",24]],"251":[["MELON",12]],"252":[["MELON",6]],"253":[["MELON",6]],"255":[["MELON",6]],"258":[["MILK",12],["FERTILIZER",5]],"264":[["MELON",12],["FERTILIZER",13]],"266":[["FERTILIZER",1]],"269":[["MILK",6]],"289":[["FERTILIZER",14]],"293":[["WOOL",8]],"298":[["MILK",6]],"300":[["FERTILIZER",2]],"312":[["FERTILIZER",17]],"323":[["MILK",6]],"337":[["FERTILIZER",9]],"338":[["MILK",6],["FERTILIZER",1]],"339":[["MILK",3]],"340":[["MILK",6]],"341":[["MILK",3]],"342":[["WOOL",6]],"343":[["WOOL",6]],"361":[["WOOL",1]],"362":[["FERTILIZER",6]],"364":[["WOOL",3],["FERTILIZER",1]],"365":[["WOOL",2]],"366":[["WOOL",2]],"367":[["WOOL",4]],"369":[["WOOL",6]],"370":[["FERTILIZER",5]],"381":[["MILK",7]],"382":[["MILK",5]],"385":[["STRAWBERRY",8]],"386":[["FERTILIZER",10]],"389":[["WOOL",4]],"393":[["MILK",8]],"394":[["FERTILIZER",5]],"395":[["STRAWBERRY",4]],"397":[["MILK",7]],"403":[["STRAWBERRY",12]],"406":[["WOOL",14]],"407":[["MILK",3],["FERTILIZER",2]],"409":[["WOOL",4],["FERTILIZER",5]],"412":[["FERTILIZER",2]],"413":[["FERTILIZER",1]],"417":[["MILK",4]],"418":[["WOOL",6],["FERTILIZER",3]],"421":[["MILK",2]],"422":[["MILK",3]],"427":[["STRAWBERRY",6]],"429":[["STRAWBERRY",10]],"431":[["MILK",3]],"433":[["MILK",6],["WOOL",4]],"438":[["MILK",3]],"440":[["WOOL",6]],"446":[["FERTILIZER",10]],"451":[["STRAWBERRY",10]],"454":[["STRAWBERRY",14]],"457":[["WOOL",6]],"461":[["FERTILIZER",10]],"462":[["MILK",6]],"463":[["MILK",3]],"466":[["WOOL",4]],"472":[["MILK",9]],"475":[["STRAWBERRY",4]],"477":[["STRAWBERRY",6]],"478":[["STRAWBERRY",6]],"485":[["FERTILIZER",10]],"486":[["MILK",6],["WOOL",6]],"487":[["MILK",6],["WOOL",2]],"493":[["MILK",9],["WOOL",4]],"498":[["STRAWBERRY",10]],"502":[["STRAWBERRY",14]],"505":[["WOOL",10]],"509":[["FERTILIZER",10]],"510":[["MILK",6],["WOOL",2]],"511":[["MILK",6]],"517":[["MILK",9],["STRAWBERRY",8]],"522":[["FERTILIZER",14]],"523":[["STRAWBERRY",16]],"525":[["WOOL",6]],"529":[["WOOL",4]],"530":[["FERTILIZER",10]],"534":[["STRAWBERRY",6],["MILK",6],["WOOL",6]],"535":[["STRAWBERRY",6],["MILK",6],["WOOL",2]],"536":[["STRAWBERRY",6]],"540":[["FERTILIZER",6]],"541":[["STRAWBERRY",18],["MILK",9]],"546":[["STRAWBERRY",10]],"548":[["WOOL",8]],"550":[["STRAWBERRY",14]],"552":[["WOOL",11],["FERTILIZER",14]],"554":[["FERTILIZER",4]],"557":[["FERTILIZER",2]],"558":[["MILK",6]],"559":[["MILK",6]],"560":[["MILK",3]],"565":[["MILK",6]],"570":[["STRAWBERRY",14]],"576":[["MILK",27]],"582":[["STRAWBERRY",6],["WOOL",6],["FERTILIZER",9]],"583":[["STRAWBERRY",6],["WOOL",4]],"584":[["STRAWBERRY",6],["WOOL",6]],"585":[["STRAWBERRY",1],["WOOL",2]],"586":[["WOOL",18]],"589":[["STRAWBERRY",14]],"600":[["WOOL",3],["FERTILIZER",16]],"601":[["MILK",6]],"602":[["FERTILIZER",2]],"604":[["FERTILIZER",1]],"606":[["STRAWBERRY",6],["MILK",6]],"607":[["STRAWBERRY",3],["MILK",3]],"613":[["STRAWBERRY",14]],"614":[["MILK",9]],"620":[["WOOL",3]],"624":[["FERTILIZER",5]],"626":[["FERTILIZER",4]],"629":[["FERTILIZER",2]],"630":[["STRAWBERRY",6],["MILK",6],["WOOL",6]],"631":[["STRAWBERRY",6],["MILK",3],["WOOL",3],["FERTILIZER",2]],"632":[["STRAWBERRY",6]],"633":[["STRAWBERRY",6],["FERTILIZER",1]],"634":[["WOOL",9],["FERTILIZER",1]],"635":[["FERTILIZER",2]],"637":[["STRAWBERRY",14],["MILK",9],["FERTILIZER",1]],"640":[["WOOL",9]],"648":[["MILK",15]],"649":[["STRAWBERRY",10],["WOOL",3]],"654":[["STRAWBERRY",4],["FERTILIZER",13]],"656":[["WOOL",4]],"660":[["WOOL",8]],"669":[["MILK",3]],"673":[["MILK",9]],"674":[["CARROT",2],["FERTILIZER",15]],"678":[["STRAWBERRY",6],["MILK",3]],"679":[["STRAWBERRY",6]],"680":[["STRAWBERRY",6]],"681":[["STRAWBERRY",4]],"683":[["MILK",9]],"684":[["MILK",3]],"685":[["STRAWBERRY",22],["FERTILIZER",1]],"687":[["FERTILIZER",1]],"688":[["WOOL",12]],"689":[["FERTILIZER",1]],"690":[["FERTILIZER",1]],"691":[["CARROT",7],["FERTILIZER",2]],"693":[["FERTILIZER",1]],"698":[["FERTILIZER",14]],"704":[["CARROT",1]],"707":[["MILK",3]],"708":[["CARROT",4]],"711":[["WOOL",3]],"712":[["MILK",3]],"713":[["FERTILIZER",1]],"716":[["FERTILIZER",1]],"718":[["MILK",3]]}}''').items()}
_MFR = {"t0": -1, "streak": 0, "is_mirror": False,
        "route": None, "score": [0, 0]}


def _mfr_get(o, k, default=None):
    if isinstance(o, Mapping):
        return o.get(k, default)
    return getattr(o, k, default)


def _mfr_seat(obs):
    return int(_mfr_get(obs, "player", 0) or 0)


def _mfr_sig(farm):
    tiles = _mfr_get(farm, "tiles", []) or []
    planted = animals = 0
    for row in tiles:
        for c in row or []:
            if isinstance(c, dict):
                if c.get("kind") == "PLANT":
                    planted += 1
                if c.get("animal"):
                    animals += 1
    return (round(float(_mfr_get(farm, "money", 0) or 0), 2),
            len(_mfr_get(farm, "unlocked_quadrants", []) or []),
            len(_mfr_get(farm, "hands", []) or []), planted, animals)


def _mfr_track(obs, step):
    if step <= _MFR["t0"] or step == 0:
        _MFR.update(streak=0, is_mirror=False, route=None, score=[0, 0])
    _MFR["t0"] = step
    if _MFR["is_mirror"] or not (100 <= step <= 143):
        return
    farms = list(_mfr_get(obs, "farms", []) or [])
    if len(farms) < 2:
        return
    me = _mfr_seat(obs)
    if _mfr_sig(farms[me]) == _mfr_sig(farms[1 - me]):
        _MFR["streak"] += 1
        if _MFR["streak"] >= MFR_STREAK:
            _MFR["is_mirror"] = True
    else:
        _MFR["streak"] = 0


def _mfr_identify(action, step):
    """Score my emitted market orders against both tapes at divergent turns."""
    if _MFR["route"] is not None or step < 360:
        return
    mine = _json.dumps(action.get("market") or [], sort_keys=True)
    a = _json.dumps([["SELL", i, q] for i, q in _SELLS.get(0, {}).get(step, [])], sort_keys=True)
    b = _json.dumps([["SELL", i, q] for i, q in _SELLS.get(1, {}).get(step, [])], sort_keys=True)
    # only score turns where the tapes' sell views differ
    if a == b:
        return
    sells_mine = _json.dumps([o for o in (action.get("market") or [])
                              if o and o[0] == "SELL" and o[1] != "WHEAT"],
                             sort_keys=True)
    for r, ref in ((0, a), (1, b)):
        if sells_mine == ref:
            _MFR["score"][r] += 1
    if _MFR["score"][0] != _MFR["score"][1] and max(_MFR["score"]) >= 2:
        _MFR["route"] = 0 if _MFR["score"][0] > _MFR["score"][1] else 1


def _mfr_next_sells(step):
    n0 = _SELLS.get(0, {}).get(step + 1, [])
    n1 = _SELLS.get(1, {}).get(step + 1, [])
    if step + 1 < 360 or n0 == n1:
        return n0
    r = _MFR["route"]
    if r is None:
        return []                      # fail-closed while unidentified
    return _SELLS.get(r, {}).get(step + 1, [])


def _mfr_action(action, step):
    sells = _mfr_next_sells(step)
    if not sells:
        return action
    market = list(action.get("market") or [])
    for item, qty in sells:
        if len(market) >= MFR_CAP:
            break
        market.append(["SELL", item, int(qty)])
    action["market"] = market
    return action


_native_agent_mfr = agent


def agent_v733(obs, configuration=None):
    action = _native_agent_mfr(obs)
    if L_MFR:
        _seat = _mfr_seat(obs)
        step = _TURN_COUNT.get(_seat)
        if step is None:
            step = _derive_turn(obs)
        _mfr_track(obs, step)
        _mfr_identify(action, step)
        if _MFR["is_mirror"] and 144 <= step <= 716:
            action = _mfr_action(action, step)
    return action


# ---------------------------------------------------------------------------
# L_FINANCE (destbreso, 2026-09-04): chained financing for the HIRE order.
#
# THE DEFECT IT REPAIRS, measured on 77 real ladder episodes that replay to the
# dollar (12 of them banked exactly 0 on the live board). The v<=6 opening buys
# 53 wheat and sells 48 to fund two cows, two sheep, five hires and its seed,
# and lands within a few dollars of nothing. Whether it lands on 29 or on 0
# depends on the price the OPPONENT leaves, and the dead games are the ones
# played against rivals who sell hard in days 0-2 (16 opening sells against 6).
# Hands do not persist overnight, so at t24, day 1 hour 0, the tape emits three
# HIREs costing $4 while holding $0 and 3 WHEAT worth $28 each. It cannot pay
# four dollars with eighty-four in the shed. No hand is ever taken on, nothing
# is worked, and the season ends at zero.
#
# WHY THIS AND NOT A CASH RESERVE, which was measured and rejected (log 203qm:
# reserves of 5, 10, 20 and 40 remove every zero and take wins from 52 of 77 to
# 15). A reserve changes WHAT the tape buys, and a tape is a fixed sequence
# whose later turns assume the earlier purchases happened, so cancelling one
# detaches the rest of the season. This layer adds no purchase and removes
# none: the engine settles the market list by index, so a SELL at a lower index
# pays for the HIREs behind it in the SAME turn.
#
# It is finance() in core, which is marked [CORE], documents exactly this and
# has zero call sites (docs/FINDINGS.md O4). The king does it on 2,280 of his
# 3,624 buy-turns, 62.9 %; this chassis does it on 0 of 5,457.
#
# FAIL-CLOSED in three places, because the engine has no error channel: an
# observation missing any field it needs, a market list already at the ten-order
# cap (never displace an order, that is the reserve's failure mode), or a shed
# with nothing priced above zero, all return the action untouched.
#
# ON THIS CHASSIS it is INSURANCE, not a repair: v7.33 has 0 zero-bank games
# in 105 recorded episodes and 0 of 203 live. It is carried so the two agents
# of a published PAIR differ in the chassis and not in the layers, and its
# firing rate is reported rather than assumed.
#
# MEASURED on the 77 v7.36 rows of sparring/pool_zerobank_20260904.json.zz,
# replayed in kagsim at the recorded seed and seat, entry point resolved the way
# Kaggle resolves it (the LAST module-level callable):
#   as shipped     zeros 12/77   wins 52/77   median bank 87,109
#   L_FINANCE=1    zeros  0/77   wins 52/77   median bank 88,912
# It fires 0.5 turns a game. Log 203qr.

L_FINANCE = 1
FIN_CAP = 10                   # maxMarketOrdersPerTurn; extras are dropped


def _fin_fib(n):
    """The engine prices the nth hire of the day at fib(n): 1, 1, 2, 3, 5, 8."""
    a, b = 1, 1
    for _ in range(n):
        a, b = b, a + b
    return a


def _finance_action(action, obs, seat):
    market = action.get("market") or []
    if not market or len(market) >= FIN_CAP:
        return action
    if not any(o and o[0] == "HIRE" for o in market):
        return action
    farms = _mfr_get(obs, "farms") or []
    if seat is None or seat < 0 or seat >= len(farms):
        return action
    farm = farms[seat] or {}
    money = _mfr_get(farm, "money")
    if money is None:
        return action
    hires = int(_mfr_get(farm, "hires_today", 0) or 0)
    cost = 0
    for o in market:
        if o and o[0] == "HIRE":
            cost += _fin_fib(hires)
            hires += 1
    short = cost - money
    if short <= 0:
        return action
    private = _mfr_get(obs, "private") or {}
    shed = _mfr_get(private, "shed") or {}
    prices = _mfr_get(_mfr_get(obs, "market") or {}, "prices") or {}
    best = None
    # sorted so the choice is deterministic under any dict ordering
    for good in sorted(shed):
        held = int(shed.get(good) or 0)
        price = int(prices.get(good) or 0)
        if held > 0 and price > 0 and (best is None or price > best[1]):
            best = (good, price, held)
    if best is None:
        return action
    good, price, held = best
    units = min(held, int(short // price) + 1)
    if units < 1:
        return action
    action["market"] = [["SELL", good, int(units)]] + list(market)
    return action


def agent_v738(obs, configuration=None):
    action = _native_agent_mfr(obs)
    _seat = _mfr_seat(obs)
    step = _TURN_COUNT.get(_seat)
    if step is None:
        step = _derive_turn(obs)
    if L_MFR:
        _mfr_track(obs, step)
        _mfr_identify(action, step)
        if _MFR["is_mirror"] and 144 <= step <= 716:
            action = _mfr_action(action, step)
    if L_FINANCE:
        action = _finance_action(action, obs, _seat)
    return action
