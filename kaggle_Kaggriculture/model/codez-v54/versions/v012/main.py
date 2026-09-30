import json
# Strategy: Use the inspected Pipe-16 HybridOpening controller. Reassign idle workers during the first three days to plant, water and harvest one temporary wheat crop, then restore the planned pasture and deliver the wheat. Preserve the public Metav4 production and market controller. This is attributed reuse, and its stronger public source still needs live confirmation. Disable optional environment-dependent external library loading so the archive is self-contained.
# Local packaging modifications, 2026-09-20. Original attribution retained.
# Kaggriculture submission v9/3: public V39 (Apache-2.0, notices below) plus the v9 layers
# RACEPX gate, RACE (reservation from step 192, horizon 40 / margin 12), COURIER, CARROT and HERD
# appended at the end of this file.
# EXP-173 isolate opening market sequence inspired by yhay81/shop-router-0911-simple (Apache-2.0).
# Kaggriculture EXP-167 candidate. Not submitted automatically.
# Attribution: thomastschinkel, yhay81, destbreso, aurax7, tetsutani,
# prvsiyan and Dmitrii Gluzdov. Apache-2.0 derivations; notices retained below.
# Kaggriculture v31 / EXP-157, Ahmed Berat Ozer, September 9 2026.
# Selected mechanism: crop_public_order. New independent confirmation is required.
# Public V221B/V224C production/timing lineage: prvsiyan, Apache-2.0.
# Original economics and integration; retained upstream licenses follow.
# Kaggriculture v28 / EXP-154, Ahmed Berat Ozer, September 9 2026.
# Changes: aurax7 day-end storage guard; Dmitrii Gluzdov physical terminal rescue
# adapted to v27, with 64 deterministic simulations. Apache-2.0.
# New action tapes and ordered shop-pair map: yhay81/shop-router-0909, Apache-2.0.
# Kaggriculture v25, EXP-149: Shop0908 production, sale lead, terminal cargo rescue.
# Runtime chassis: Apache-2.0; thomastschinkel, yhay81, tetsutani.
# Routing and public action data: yhay81/shop-router-0908, frozen September 8, 2026.
# 
#                                  Apache License
#                            Version 2.0, January 2004
#                         http://www.apache.org/licenses/
# 
#    TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION
# 
#    1. Definitions.
# 
#       "License" shall mean the terms and conditions for use, reproduction,
#       and distribution as defined by Sections 1 through 9 of this document.
# 
#       "Licensor" shall mean the copyright owner or entity authorized by
#       the copyright owner that is granting the License.
# 
#       "Legal Entity" shall mean the union of the acting entity and all
#       other entities that control, are controlled by, or are under common
#       control with that entity. For the purposes of this definition,
#       "control" means (i) the power, direct or indirect, to cause the
#       direction or management of such entity, whether by contract or
#       otherwise, or (ii) ownership of fifty percent (50%) or more of the
#       outstanding shares, or (iii) beneficial ownership of such entity.
# 
#       "You" (or "Your") shall mean an individual or Legal Entity
#       exercising permissions granted by this License.
# 
#       "Source" form shall mean the preferred form for making modifications,
#       including but not limited to software source code, documentation
#       source, and configuration files.
# 
#       "Object" form shall mean any form resulting from mechanical
#       transformation or translation of a Source form, including but
#       not limited to compiled object code, generated documentation,
#       and conversions to other media types.
# 
#       "Work" shall mean the work of authorship, whether in Source or
#       Object form, made available under the License, as indicated by a
#       copyright notice that is included in or attached to the work
#       (an example is provided in the Appendix below).
# 
#       "Derivative Works" shall mean any work, whether in Source or Object
#       form, that is based on (or derived from) the Work and for which the
#       editorial revisions, annotations, elaborations, or other modifications
#       represent, as a whole, an original work of authorship. For the purposes
#       of this License, Derivative Works shall not include works that remain
#       separable from, or merely link (or bind by name) to the interfaces of,
#       the Work and Derivative Works thereof.
# 
#       "Contribution" shall mean any work of authorship, including
#       the original version of the Work and any modifications or additions
#       to that Work or Derivative Works thereof, that is intentionally
#       submitted to Licensor for inclusion in the Work by the copyright owner
#       or by an individual or Legal Entity authorized to submit on behalf of
#       the copyright owner. For the purposes of this definition, "submitted"
#       means any form of electronic, verbal, or written communication sent
#       to the Licensor or its representatives, including but not limited to
#       communication on electronic mailing lists, source code control systems,
#       and issue tracking systems that are managed by, or on behalf of, the
#       Licensor for the purpose of discussing and improving the Work, but
#       excluding communication that is conspicuously marked or otherwise
#       designated in writing by the copyright owner as "Not a Contribution."
# 
#       "Contributor" shall mean Licensor and any individual or Legal Entity
#       on behalf of whom a Contribution has been received by Licensor and
#       subsequently incorporated within the Work.
# 
#    2. Grant of Copyright License. Subject to the terms and conditions of
#       this License, each Contributor hereby grants to You a perpetual,
#       worldwide, non-exclusive, no-charge, royalty-free, irrevocable
#       copyright license to reproduce, prepare Derivative Works of,
#       publicly display, publicly perform, sublicense, and distribute the
#       Work and such Derivative Works in Source or Object form.
# 
#    3. Grant of Patent License. Subject to the terms and conditions of
#       this License, each Contributor hereby grants to You a perpetual,
#       worldwide, non-exclusive, no-charge, royalty-free, irrevocable
#       (except as stated in this section) patent license to make, have made,
#       use, offer to sell, sell, import, and otherwise transfer the Work,
#       where such license applies only to those patent claims licensable
#       by such Contributor that are necessarily infringed by their
#       Contribution(s) alone or by combination of their Contribution(s)
#       with the Work to which such Contribution(s) was submitted. If You
#       institute patent litigation against any entity (including a
#       cross-claim or counterclaim in a lawsuit) alleging that the Work
#       or a Contribution incorporated within the Work constitutes direct
#       or contributory patent infringement, then any patent licenses
#       granted to You under this License for that Work shall terminate
#       as of the date such litigation is filed.
# 
#    4. Redistribution. You may reproduce and distribute copies of the
#       Work or Derivative Works thereof in any medium, with or without
#       modifications, and in Source or Object form, provided that You
#       meet the following conditions:
# 
#       (a) You must give any other recipients of the Work or
#           Derivative Works a copy of this License; and
# 
#       (b) You must cause any modified files to carry prominent notices
#           stating that You changed the files; and
# 
#       (c) You must retain, in the Source form of any Derivative Works
#           that You distribute, all copyright, patent, trademark, and
#           attribution notices from the Source form of the Work,
#           excluding those notices that do not pertain to any part of
#           the Derivative Works; and
# 
#       (d) If the Work includes a "NOTICE" text file as part of its
#           distribution, then any Derivative Works that You distribute must
#           include a readable copy of the attribution notices contained
#           within such NOTICE file, excluding those notices that do not
#           pertain to any part of the Derivative Works, in at least one
#           of the following places: within a NOTICE text file distributed
#           as part of the Derivative Works; within the Source form or
#           documentation, if provided along with the Derivative Works; or,
#           within a display generated by the Derivative Works, if and
#           wherever such third-party notices normally appear. The contents
#           of the NOTICE file are for informational purposes only and
#           do not modify the License. You may add Your own attribution
#           notices within Derivative Works that You distribute, alongside
#           or as an addendum to the NOTICE text from the Work, provided
#           that such additional attribution notices cannot be construed
#           as modifying the License.
# 
#       You may add Your own copyright statement to Your modifications and
#       may provide additional or different license terms and conditions
#       for use, reproduction, or distribution of Your modifications, or
#       for any such Derivative Works as a whole, provided Your use,
#       reproduction, and distribution of the Work otherwise complies with
#       the conditions stated in this License.
# 
#    5. Submission of Contributions. Unless You explicitly state otherwise,
#       any Contribution intentionally submitted for inclusion in the Work
#       by You to the Licensor shall be under the terms and conditions of
#       this License, without any additional terms or conditions.
#       Notwithstanding the above, nothing herein shall supersede or modify
#       the terms of any separate license agreement you may have executed
#       with Licensor regarding such Contributions.
# 
#    6. Trademarks. This License does not grant permission to use the trade
#       names, trademarks, service marks, or product names of the Licensor,
#       except as required for reasonable and customary use in describing the
#       origin of the Work and reproducing the content of the NOTICE file.
# 
#    7. Disclaimer of Warranty. Unless required by applicable law or
#       agreed to in writing, Licensor provides the Work (and each
#       Contributor provides its Contributions) on an "AS IS" BASIS,
#       WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
#       implied, including, without limitation, any warranties or conditions
#       of TITLE, NON-INFRINGEMENT, MERCHANTABILITY, or FITNESS FOR A
#       PARTICULAR PURPOSE. You are solely responsible for determining the
#       appropriateness of using or redistributing the Work and assume any
#       risks associated with Your exercise of permissions under this License.
# 
#    8. Limitation of Liability. In no event and under no legal theory,
#       whether in tort (including negligence), contract, or otherwise,
#       unless required by applicable law (such as deliberate and grossly
#       negligent acts) or agreed to in writing, shall any Contributor be
#       liable to You for damages, including any direct, indirect, special,
#       incidental, or consequential damages of any character arising as a
#       result of this License or out of the use or inability to use the
#       Work (including but not limited to damages for loss of goodwill,
#       work stoppage, computer failure or malfunction, or any and all
#       other commercial damages or losses), even if such Contributor
#       has been advised of the possibility of such damages.
# 
#    9. Accepting Warranty or Additional Liability. While redistributing
#       the Work or Derivative Works thereof, You may choose to offer,
#       and charge a fee for, acceptance of support, warranty, indemnity,
#       or other liability obligations and/or rights consistent with this
#       License. However, in accepting such obligations, You may act only
#       on Your own behalf and on Your sole responsibility, not on behalf
#       of any other Contributor, and only if You agree to indemnify,
#       defend, and hold each Contributor harmless for any liability
#       incurred by, or claims asserted against, such Contributor by reason
#       of your accepting any such warranty or additional liability.
# 
#    END OF TERMS AND CONDITIONS
# 
#    APPENDIX: How to apply the Apache License to your work.
# 
#       To apply the Apache License to your work, attach the following
#       boilerplate notice, with the fields enclosed by brackets "[]"
#       replaced with your own identifying information. (Don't include
#       the brackets!)  The text should be enclosed in the appropriate
#       comment syntax for the file format. We also recommend that a
#       file or class name and description of purpose be included on the
#       same "printed page" as the copyright notice for easier
#       identification within third-party archives.
# 
#    Copyright [yyyy] [name of copyright owner]
# 
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
# 
#        http://www.apache.org/licenses/LICENSE-2.0
# 
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.
"""Kaggriculture route-replay chassis (pure Python, stdlib only).

A *route* is a pre-computed tape of 719 Kaggle-format actions
``{"farmer": [op, ...], "hands": [[op, ...], ...], "market": [[order, item, qty], ...]}``.
The chassis replays the tape chosen by a caller-supplied ``router`` and wraps it
in small reactive layers (each independently switchable via ``settings``):

    hand_align            pad/truncate hands to the real hand count      (fieldbook_logic)
    weed_repair           DIG a weed that blocks PLANT/BUILD, replay      (tetsutani + task spec)
    sell_lead             sell next step's lots one step early            (fieldbook _lead_sale)
    front_run             sell before the opponent's scheduled SELL       (hook; opponent_plan)
    budget_guard          fund each 72-step block's purchases             (six_day_budget_guard.hpp)
    room_guard            keep shed <= 99 at hour 23                      (tetsutani)
    clamp_sells           trim SELL orders to the projected shed          (tetsutani)
    dead_stock            sell stock the route will never sell            (tetsutani)
    terminal_liquidation  step >= 718: sell the whole projected shed      (fieldbook _terminal_sale)

Engine facts (verified against kaggle_environments 1.32.7, env_1_32_7.py):
  observation["farms"][p] = {"money", "tiles"[y][x], "farmer"[x,y], "hands"[[x,y]..],
                             "unlocked_quadrants", "hires_today"}
  tiles: None (empty) | "LOCKED" | {"kind": WEED|COOP|PASTURE|PLANT, "crop"/"animal", ...}
  observation["private"] = {"shed": {item: n}, "seeds": {crop: n}, "inventories": [{}...]}
  observation["market"] = {"inventory": {...}, "prices": {...}}
  observation["town"] = {"unlocked_shops": [...]}
  Agents act on steps 0..718 (interpreter marks DONE once step >= episodeSteps-2).
"""
from __future__ import annotations

import copy

PRODUCTS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER")
SEED_PRICE = {"WHEAT": 10, "CARROT": 20, "TOMATO": 50, "STRAWBERRY": 100, "MELON": 80}
ANIMAL_COST = {"GOOSE": 300, "COW": 400, "SHEEP": 500}
ANIMAL_STRUCTURE = {"GOOSE": "COOP", "COW": "PASTURE", "SHEEP": "PASTURE"}
LAND_PRICES = (1000, 2000, 4000)
MOVES = {"NORTH": (0, -1), "SOUTH": (0, 1), "EAST": (1, 0), "WEST": (-1, 0)}
FRONT_RUN_ITEMS = ("MILK", "WOOL", "STRAWBERRY", "MELON")
LAST_ACT_STEP = 718
PASS_ACTION = {"farmer": ["PASS"], "hands": [], "market": []}

DEFAULT_SETTINGS = {
    "hand_align": True,
    "weed_repair": True,
    "sell_lead": True,
    "front_run": True,
    "budget_guard": True,
    "room_guard": True,
    "clamp_sells": True,
    "dead_stock": True,
    "terminal_liquidation": True,
    # tunables
    "block_turns": 72,
    "shed_capacity": 100,
    "board_size": 10,
    "max_orders": 10,
    "turns_per_day": 24,
    "min_sell_price": 2,
}


# --------------------------------------------------------------------------- helpers
def _get(value, key, default=None):
    """Field access that works for dicts and Kaggle Struct/attribute objects."""
    if isinstance(value, dict):
        return value.get(key, default)
    getter = getattr(value, "get", None)
    if callable(getter):
        return getter(key, default)
    return getattr(value, key, default)


def _int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _fib(n):
    a, b = 1, 1
    for _ in range(n):
        a, b = b, a + b
    return a


def _step_of(observation):
    raw = _get(observation, "step")
    if raw is not None:
        return _int(raw)
    return _int(_get(observation, "day", 0)) * 24 + _int(_get(observation, "hour", 0))


def _shed_adjacent(pos, board):
    if not isinstance(pos, (list, tuple)) or len(pos) < 2:
        return False
    half = board // 2
    return pos[0] in (half - 1, half) and pos[1] in (half - 1, half)


def _tile_at(tiles, pos):
    try:
        x, y = int(pos[0]), int(pos[1])
        return tiles[y][x]
    except (TypeError, ValueError, IndexError):
        return "LOCKED"


def _is_noop(act, tile, inv, seeds, pos, board):
    """True when the engine will certainly ignore ``act`` (mirrors _apply_unit_action)."""
    if not act:
        return True
    op = act[0]
    x, y = pos[0], pos[1]
    if op in MOVES:
        dx, dy = MOVES[op]
        return not (0 <= x + dx < board and 0 <= y + dy < board)
    if op == "PASS":
        return True
    adjacent = _shed_adjacent(pos, board)
    if op == "DROP":
        return (not adjacent) or (not inv)
    if op == "PICKUP":
        return not adjacent
    if op == "PLACE":
        item = act[1] if len(act) > 1 else None
        if item in ANIMAL_STRUCTURE and isinstance(tile, dict) \
                and _get(tile, "kind") == ANIMAL_STRUCTURE[item] and _get(tile, "animal") is None:
            return _int(_get(inv, item, 0)) <= 0
        return (not adjacent) or _int(_get(inv, item, 0)) <= 0
    if tile == "LOCKED":
        return True
    is_dict = isinstance(tile, dict)
    kind = _get(tile, "kind") if is_dict else None
    animal = is_dict and _get(tile, "animal") is not None
    if op == "PLANT":
        return tile is not None or _int(_get(seeds, act[1] if len(act) > 1 else None, 0)) <= 0
    if op == "WATER":
        return kind != "PLANT" or bool(_get(tile, "watered_today"))
    if op == "HARVEST":
        return (not is_dict) or _int(_get(tile, "yield_units", 0)) <= 0
    if op == "FERTILIZE":
        return kind != "PLANT" or _int(_get(inv, "FERTILIZER", 0)) <= 0
    if op == "DIG":
        return tile is None or animal
    if op in ("BUILD_COOP", "BUILD_PASTURE"):
        return tile is not None
    if op == "FEED":
        return (not animal) or bool(_get(tile, "fed_today")) or _int(_get(inv, "WHEAT", 0)) <= 0
    if op == "COLLECT_FERTILIZER":
        return (not animal) or (not _get(tile, "fertilizer_available"))
    if op == "CARE":
        return (not animal) or bool(_get(tile, "cared_today"))
    return True


class _View:
    """Cheap per-step snapshot of everything the layers read from the observation."""

    def __init__(self, observation, player, cfg):
        farms = list(_get(observation, "farms", []) or [])
        self.farm = farms[player] if player < len(farms) else {}
        self.rival = farms[1 - player] if len(farms) >= 2 and 1 - player < len(farms) else {}
        private = _get(observation, "private", {}) or {}
        self.shed = {k: max(0, _int(v)) for k, v in dict(_get(private, "shed", {}) or {}).items()}
        self.seeds = dict(_get(private, "seeds", {}) or {})
        self.invs = [dict(i or {}) for i in (_get(private, "inventories", []) or [])]
        market = _get(observation, "market", {}) or {}
        self.prices = {k: _int(v) for k, v in dict(_get(market, "prices", {}) or {}).items()}
        self.money = float(_get(self.farm, "money", 0.0) or 0.0)
        self.tiles = _get(self.farm, "tiles", []) or []
        self.board = len(self.tiles) or cfg["board_size"]
        self.positions = [_get(self.farm, "farmer", None)] + [list(p) for p in (_get(self.farm, "hands", []) or [])]
        self.hires_today = _int(_get(self.farm, "hires_today", 0))
        self.quadrants = len(list(_get(self.farm, "unlocked_quadrants", []) or []))

    def inv(self, idx):
        return self.invs[idx] if idx < len(self.invs) else {}

    def in_hands(self, item):
        return sum(max(0, _int(_get(inv, item, 0))) for inv in self.invs)


# --------------------------------------------------------------------------- chassis
class Chassis:
    """Replays ``routes[router(...)]`` with reactive safety/market layers.

    routes         : {route_id: list of >= 719 Kaggle action dicts}
    router         : callable(observation, step, state_dict) -> route_id, called every
                     step; ``state_dict`` is per-player and persists across the game.
    settings       : overrides for DEFAULT_SETTINGS (layer switches + tunables)
    opponent_plan  : optional list of the opponent's expected actions (front_run hook)
    """

    def __init__(self, routes, router=None, settings=None, opponent_plan=None):
        self.routes = {rid: list(tape) for rid, tape in routes.items()}
        self.router = router or (lambda observation, step, state: next(iter(self.routes)))
        self.cfg = dict(DEFAULT_SETTINGS)
        self.cfg.update(settings or {})
        self.opponent_plan = opponent_plan
        self.players = {}
        self.diagnostics = {"layer_fallbacks": 0, "entry_fallbacks": 0}
        self._future_sells = {}   # route id -> {item: [remaining planned SELL qty from step t]}

    # ---- state -----------------------------------------------------------------
    def _state(self, player, step):
        st = self.players.get(player)
        if st is None or step == 0 or step <= st["last_step"]:
            st = {"last_step": -1, "route": None, "router_state": {},
                  "pending": {}, "sell_state": {"due_step": -1, "suppress": {}}}
            self.players[player] = st
        st["last_step"] = step
        return st

    def _route_action(self, route, step):
        tape = self.routes[route]
        if 0 <= step < len(tape) and isinstance(tape[step], dict):
            return copy.deepcopy(tape[step])
        return copy.deepcopy(PASS_ACTION)

    def future_sells(self, route, item, step):
        """Planned SELL quantity of ``item`` in route steps >= ``step`` (suffix sums)."""
        table = self._future_sells.get(route)
        if table is None:
            tape = self.routes[route]
            n = len(tape)
            table = {p: [0] * (n + 1) for p in PRODUCTS}
            for t in range(n - 1, -1, -1):
                for p in PRODUCTS:
                    table[p][t] = table[p][t + 1]
                for o in (tape[t].get("market") or []) if isinstance(tape[t], dict) else []:
                    if o and o[0] == "SELL" and len(o) >= 3 and o[1] in table:
                        table[o[1]][t] += max(0, _int(o[2]))
            self._future_sells[route] = table
        col = table.get(item)
        return col[step] if col and 0 <= step < len(col) else 0

    # ---- main entry -----------------------------------------------------------
    def act(self, observation, configuration=None):
        if len(_get(observation, "farms", []) or []) < 2:
            raise ValueError("incomplete observation")  # factory falls back to tape
        step = _step_of(observation)
        player = _int(_get(observation, "player", 0))
        st = self._state(player, step)
        cfg = self.cfg
        view = _View(observation, player, cfg)

        route = self.router(observation, step, st["router_state"])
        if route not in self.routes:
            route = st["route"] if st["route"] in self.routes else next(iter(self.routes))
        st["route"] = route
        action = self._route_action(route, step)
        raw = copy.deepcopy(action)
        try:
            if cfg["hand_align"]:
                self._hand_align(action, view)
            if cfg["weed_repair"]:
                self._weed_repair(action, view, st, route, step)
            if cfg["sell_lead"] or cfg["front_run"]:
                self._apply_suppression(action, st["sell_state"], step)
            projected = self._projected_shed(action, view)
            lead_available = dict(projected)
            next_sup = {"due_step": -1, "suppress": {}, "r36_debts": st["sell_state"].get("r36_debts", {})}
            if cfg["sell_lead"]:
                self._sell_lead(action, view, lead_available, route, step, next_sup)
            if cfg["front_run"] and self.opponent_plan:
                self._front_run(action, view, lead_available, route, step, next_sup)
            st["sell_state"] = next_sup
            if cfg["budget_guard"]:
                self._budget_guard(action, view, route, step)
            if cfg["room_guard"]:
                self._room_guard(action, view, route, step)
            if cfg["clamp_sells"]:
                self._clamp_sells(action, projected)
            if cfg["dead_stock"]:
                self._dead_stock(action, view, projected, route, step)
            if cfg["terminal_liquidation"]:
                self._terminal_liquidation(action, projected, step)
            action["market"] = action["market"][: cfg["max_orders"]]
            return action
        except Exception:
            self.diagnostics["layer_fallbacks"] += 1
            return raw

    # ---- layer: hand_align ----------------------------------------------------
    def _hand_align(self, action, view):
        """Pad with PASS / truncate the tape's hand list to the real number of hands
        (fieldbook_logic.act). Extra hands would be ignored by the engine anyway;
        missing ones just idle, so alignment only tidies the action."""
        expected = max(0, len(view.positions) - 1)
        hands = list(action.get("hands") or [])
        hands.extend([["PASS"] for _ in range(max(0, expected - len(hands)))])
        action["hands"] = hands[:expected]

    # ---- layer: weed_repair ---------------------------------------------------
    def _weed_repair(self, action, view, st, route, step):
        """If a PLANT/BUILD_* target tile is a WEED, DIG now and queue the intended
        action for that unit; the queue replays on a later step when the unit still
        stands there and its tape action would be a no-op (the displaced no-op is
        queued behind it, so PLANT -> WATER chains survive). A PLANT is only replayed
        when the unit's next tape action is not a move, so the mandatory same-day
        WATER can follow; otherwise the seed is kept. A no-op turn spent on a weed
        is also converted to DIG (tetsutani weed_dig)."""
        units = [action.get("farmer") or ["PASS"]] + list(action.get("hands") or [])
        pending = st["pending"]
        tape = self.routes[route]
        nxt = tape[step + 1] if step + 1 < len(tape) and isinstance(tape[step + 1], dict) else {}
        next_units = [nxt.get("farmer") or ["PASS"]] + list(nxt.get("hands") or [])
        for i in range(min(len(units), len(view.positions))):
            pos = view.positions[i]
            if not isinstance(pos, (list, tuple)):
                continue
            pos = (int(pos[0]), int(pos[1]))
            tile = _tile_at(view.tiles, pos)
            act = list(units[i])
            queue = pending.get(i)
            if queue and queue[0][0] != pos:
                pending.pop(i, None)
                queue = None
            is_weed = isinstance(tile, dict) and _get(tile, "kind") == "WEED"
            noop = _is_noop(act, tile, view.inv(i), view.seeds, pos, view.board)
            next_op = next_units[i][0] if i < len(next_units) and next_units[i] else "PASS"
            if act and act[0] in ("PLANT", "BUILD_COOP", "BUILD_PASTURE") and is_weed:
                pending.setdefault(i, []).append((pos, act))
                act = ["DIG"]
            elif queue and noop:
                _, replay = queue[0]
                if replay[0] == "PLANT" and next_op in MOVES:
                    pending.pop(i, None)          # WATER could never follow: keep the seed
                else:
                    queue.pop(0)
                    if act and act[0] != "PASS" and act[0] not in MOVES:
                        queue.append((pos, act))
                    act = replay
                    if not queue:
                        pending.pop(i, None)
            elif is_weed and noop:
                act = ["DIG"]
            units[i] = act
        action["farmer"] = units[0]
        action["hands"] = units[1:]

    # ---- projected shed -------------------------------------------------------
    def _projected_shed(self, action, view):
        """Shed contents after this step's unit actions but before the market runs:
        PICKUP removes, DROP/PLACE(non-animal) near the shed adds up to capacity
        (fieldbook _projected_shed / tetsutani projected shed)."""
        cap = self.cfg["shed_capacity"]
        proj = {p: view.shed.get(p, 0) for p in PRODUCTS}
        for k, v in view.shed.items():
            proj.setdefault(k, v)
        total = sum(proj.values())
        units = [action.get("farmer") or ["PASS"]] + list(action.get("hands") or [])
        for i in range(min(len(units), len(view.positions))):
            if not _shed_adjacent(view.positions[i], view.board):
                continue
            act = units[i]
            op = act[0] if act else "PASS"
            inv = view.inv(i)
            if op == "PICKUP" and len(act) >= 2 and act[1] in proj:
                qty = min(proj[act[1]], max(0, _int(act[2]) if len(act) >= 3 else 1))
                proj[act[1]] -= qty
                total -= qty
            elif op == "DROP":
                for item, held in inv.items():
                    take = min(max(0, _int(held)), max(0, cap - total))
                    if take > 0:
                        proj[item] = proj.get(item, 0) + take
                        total += take
            elif op == "PLACE" and len(act) >= 2 and act[1] not in ANIMAL_STRUCTURE:
                item = act[1]
                take = min(max(0, _int(act[2]) if len(act) >= 3 else 1),
                           max(0, _int(_get(inv, item, 0))), max(0, cap - total))
                if take > 0:
                    proj[item] = proj.get(item, 0) + take
                    total += take
        return proj

    # ---- layer: sell_lead / front_run suppression ------------------------------
    @staticmethod
    def _apply_suppression(action, sell_state, step):
        """Remove from this step's SELLs the quantities already sold a step early."""
        if sell_state.get("due_step") != step:
            return
        remaining = dict(sell_state.get("suppress", {}))
        kept = []
        for order in action.get("market") or []:
            order = list(order)
            if order and order[0] == "SELL" and len(order) >= 3 and remaining.get(order[1], 0) > 0:
                removed = min(max(0, _int(order[2])), remaining[order[1]])
                order[2] = _int(order[2]) - removed
                remaining[order[1]] -= removed
                # A zero-quantity order keeps later market race slots intact.
            kept.append(order)
        action["market"] = kept

    @staticmethod
    def _add_sell(action, item, qty, max_orders, merge=True):
        market = action.setdefault("market", [])
        if merge:
            for order in market:
                if order and order[0] == "SELL" and order[1] == item:
                    order[2] = _int(order[2]) + qty
                    return True
        if len(market) >= max_orders:
            return False
        market.append(["SELL", item, qty])
        return True

    def _sell_lead(self, action, view, projected, route, step, next_sup):
        """fieldbook _lead_sale: when step % 4 != 0 (no town consumption between the
        two steps) sell the lots the tape plans to SELL next step now, for products
        other than WHEAT/FERTILIZER we already hold, and suppress them next step.
        Skipped at the last step, at shop-unlock boundaries and if a SELL for that
        product is already queued this step."""
        cfg = self.cfg
        nxt = step + 1
        unlock_period = 3 * cfg["turns_per_day"]
        if nxt > LAST_ACT_STEP or nxt % unlock_period == 0 or step % 4 == 0:
            return
        tape = self.routes[route]
        future = tape[nxt] if nxt < len(tape) and isinstance(tape[nxt], dict) else {}
        planned = {}
        for o in future.get("market") or []:
            if o and o[0] == "SELL" and len(o) >= 3 and o[1] in PRODUCTS:
                planned[o[1]] = planned.get(o[1], 0) + max(0, _int(o[2]))
        already = {o[1] for o in action.get("market") or [] if o and o[0] == "SELL" and len(o) > 1}
        for item in PRODUCTS:
            if item in ("WHEAT", "FERTILIZER") or planned.get(item, 0) <= 0 or item in already:
                continue
            qty = min(projected.get(item, 0), planned[item])
            if qty <= 0 or view.prices.get(item, 0) < cfg["min_sell_price"]:
                continue
            if not self._add_sell(action, item, qty, cfg["max_orders"], merge=False):
                break
            projected[item] -= qty
            next_sup["suppress"][item] = next_sup["suppress"].get(item, 0) + qty
        if next_sup["suppress"]:
            next_sup["due_step"] = nxt

    def _front_run(self, action, view, projected, route, step, next_sup):
        """Hook: if ``opponent_plan`` (their expected tape) schedules a SELL of
        MILK/WOOL/STRAWBERRY/MELON next step, sell what we hold of it now (before
        their supply depresses the price) and suppress our own SELL of that quantity
        next step. Bounded by our own remaining planned sales so it never dumps."""
        cfg = self.cfg
        nxt = step + 1
        plan = self.opponent_plan
        if nxt > LAST_ACT_STEP or nxt >= len(plan) or not isinstance(plan[nxt], dict):
            return
        already = {o[1] for o in action.get("market") or [] if o and o[0] == "SELL" and len(o) > 1}
        for o in plan[nxt].get("market") or []:
            if not (o and o[0] == "SELL" and len(o) >= 3 and o[1] in FRONT_RUN_ITEMS):
                continue
            item = o[1]
            if item in already or view.prices.get(item, 0) < cfg["min_sell_price"]:
                continue
            own_next = sum(max(0, _int(x[2])) for x in self.routes[route][nxt].get("market", [])
                           if len(x) >= 3 and x[0] == "SELL" and x[1] == item)
            qty = min(projected.get(item, 0), max(0, _int(o[2])), own_next)
            if qty <= 0:
                continue
            if not self._add_sell(action, item, qty, cfg["max_orders"], merge=False):
                break
            projected[item] -= qty
            already.add(item)
            next_sup["suppress"][item] = next_sup["suppress"].get(item, 0) + qty
        if next_sup["suppress"]:
            next_sup["due_step"] = nxt

    # ---- layer: budget_guard --------------------------------------------------
    def _block_requirements(self, view, route, start, end):
        """Planned purchase cost and item reserves for tape steps [start, end)
        (six_day_budget_guard.hpp calculate_six_day_requirements)."""
        tape = self.routes[route]
        budget = 0.0
        seed_bal, item_bal = {}, {}
        seed_need, item_need = {}, {}
        hires_by_day = {}
        quadrants = view.quadrants
        for t in range(start, min(end, len(tape))):
            a = tape[t] if isinstance(tape[t], dict) else {}
            for u in [a.get("farmer") or ["PASS"]] + list(a.get("hands") or []):
                if not u:
                    continue
                op = u[0]
                arg = u[1] if len(u) > 1 else None
                qty = max(1, _int(u[2]) if len(u) > 2 else 1)
                if op == "PLANT" and arg in SEED_PRICE:
                    seed_bal[arg] = seed_bal.get(arg, 0) - 1
                    seed_need[arg] = max(seed_need.get(arg, 0), -seed_bal[arg])
                elif op == "FEED":
                    item_bal["WHEAT"] = item_bal.get("WHEAT", 0) - 1
                    item_need["WHEAT"] = max(item_need.get("WHEAT", 0), -item_bal["WHEAT"])
                elif op == "FERTILIZE":
                    item_bal["FERTILIZER"] = item_bal.get("FERTILIZER", 0) - 1
                    item_need["FERTILIZER"] = max(item_need.get("FERTILIZER", 0), -item_bal["FERTILIZER"])
                elif op == "PLACE" and arg is not None:
                    item_bal[arg] = item_bal.get(arg, 0) - qty
                    item_need[arg] = max(item_need.get(arg, 0), -item_bal[arg])
            for o in a.get("market") or []:
                if not o:
                    continue
                op = o[0]
                item = o[1] if len(o) > 1 else None
                qty = max(1, _int(o[2]) if len(o) > 2 else 1)
                if op == "HIRE":
                    day = (t - start) // self.cfg["turns_per_day"]
                    hires_by_day[day] = hires_by_day.get(day, 0) + 1
                elif op == "BUY_LAND":
                    extra = quadrants - 1
                    if 0 <= extra < len(LAND_PRICES):
                        budget += LAND_PRICES[extra]
                        quadrants += 1
                elif op == "BUY_SEED" and item in SEED_PRICE:
                    budget += SEED_PRICE[item] * qty
                    seed_bal[item] = seed_bal.get(item, 0) + qty
                elif op == "BUY_PRODUCT" and item in ("WHEAT", "FERTILIZER"):
                    budget += view.prices.get(item, 0) * qty
                    item_bal[item] = item_bal.get(item, 0) + qty
                elif op == "BUY_ANIMAL" and item in ANIMAL_COST:
                    budget += ANIMAL_COST[item] * qty
                    item_bal[item] = item_bal.get(item, 0) + qty
        for day, n in hires_by_day.items():
            first = view.hires_today if day == 0 else 0
            for k in range(n):
                budget += _fib(first + k)
        return budget, item_need

    def _budget_guard(self, action, view, route, step):
        """At every block boundary (step % 72 == 0) make sure cash + the value of
        stock the block already plans to sell covers the block's purchases (hires,
        land, seeds, animals, products). A shortfall is covered by extra SELLs of
        unprotected shed stock, highest price first; SELLs are moved in front of
        the buys so the money is there when they execute."""
        cfg = self.cfg
        block = cfg["block_turns"]
        if block <= 0 or step % block != 0:
            return
        budget, item_need = self._block_requirements(view, route, step, step + block)
        market = action.setdefault("market", [])
        existing = {}
        for o in market:
            if o and o[0] == "SELL" and len(o) >= 3:
                existing[o[1]] = existing.get(o[1], 0) + max(0, _int(o[2]))
        cash = view.money
        for item in PRODUCTS:
            planned = max(existing.get(item, 0), self.future_sells(route, item, step)
                          - self.future_sells(route, item, step + block))
            cash += min(view.shed.get(item, 0), planned) * view.prices.get(item, 0)
        shortfall = budget - cash
        if shortfall <= 0:
            return
        candidates = []
        for item in PRODUCTS:
            price = view.prices.get(item, 0)
            if price < cfg["min_sell_price"]:
                continue
            protected = max(0, item_need.get(item, 0) - view.in_hands(item))
            avail = view.shed.get(item, 0) - protected - existing.get(item, 0)
            if avail > 0:
                candidates.append((-price, item, avail, price))
        candidates.sort()
        added = False
        for _, item, avail, price in candidates:
            if shortfall <= 0:
                break
            qty = min(avail, -(-int(shortfall) // price))
            if self._add_sell(action, item, qty, cfg["max_orders"]):
                shortfall -= qty * price
                added = True
        if added:
            sells = [o for o in market if o and o[0] == "SELL"]
            others = [o for o in market if not (o and o[0] == "SELL")]
            action["market"] = sells + others

    # ---- layer: room_guard ----------------------------------------------------
    def _room_guard(self, action, view, route, step):
        """tetsutani room_guard: at hour 23 the end-of-day drop pushes every unit's
        inventory into the shed and overflow is destroyed. Estimate the shed after
        this step (stock + carried + harvest/collect - feed/fertilize/place + buys -
        sells) and, if it exceeds capacity-1, add SELLs preferring products with no
        future planned sale, then highest price."""
        cfg = self.cfg
        if step % cfg["turns_per_day"] != cfg["turns_per_day"] - 1:
            return
        cap = cfg["shed_capacity"]
        units = [action.get("farmer") or ["PASS"]] + list(action.get("hands") or [])
        carried = sum(max(0, _int(n)) for inv in view.invs for n in inv.values())
        produced = consumed = 0
        for i in range(min(len(units), len(view.positions))):
            tile = _tile_at(view.tiles, view.positions[i])
            a = units[i]
            if not a:
                continue
            op = a[0]
            if op == "HARVEST" and isinstance(tile, dict):
                produced += max(0, _int(_get(tile, "yield_units", 0)))
            elif op == "COLLECT_FERTILIZER" and isinstance(tile, dict) and _get(tile, "fertilizer_available"):
                produced += 1
            elif op in ("FEED", "FERTILIZE"):
                consumed += 1
            elif op == "PLACE" and len(a) > 1 and a[1] in ANIMAL_STRUCTURE:
                consumed += 1
        market = action.setdefault("market", [])
        planned_sells, planned_buys = {}, 0
        for o in market:
            if not o:
                continue
            if o[0] == "SELL" and len(o) >= 3:
                planned_sells[o[1]] = planned_sells.get(o[1], 0) + max(0, _int(o[2]))
            elif o[0] in ("BUY_PRODUCT", "BUY_ANIMAL") and len(o) >= 3:
                planned_buys += max(0, _int(o[2]))
        shed_total = sum(view.shed.values())
        fillable = sum(min(view.shed.get(it, 0), n) for it, n in planned_sells.items())
        needed = shed_total + carried + produced - consumed + planned_buys - fillable - (cap - 1)
        if needed <= 0:
            return
        priority = sorted(PRODUCTS, key=lambda it: (self.future_sells(route, it, step + 1) > 0,
                                                   -view.prices.get(it, 0), it))
        for item in priority:
            avail = max(0, view.shed.get(item, 0) - planned_sells.get(item, 0))
            qty = min(needed, avail)
            if qty <= 0 or view.prices.get(item, 0) < 1:
                continue
            if not self._add_sell(action, item, qty, cfg["max_orders"]):
                continue
            planned_sells[item] = planned_sells.get(item, 0) + qty
            needed -= qty
            if needed <= 0:
                break

    # ---- layer: clamp_sells ---------------------------------------------------
    @staticmethod
    def _clamp_sells(action, projected):
        """Clamp against a sequential stock upper bound, retaining market slots.

        Earlier BUY_PRODUCT orders can fund a wheat wash's sell leg. Their full
        quantity is an upper bound; the engine enforces actual cash/capacity.
        Removing empty orders would change the later lockstep market races.
        """
        avail = dict(projected)
        kept = []
        for o in action.get("market") or []:
            if o and o[0] == "SELL" and len(o) >= 3:
                have = avail.get(o[1], 0)
                n = min(_int(o[2]), have)
                n = max(0, n)
                avail[o[1]] = have - n
                kept.append(["SELL", o[1], n])
            else:
                kept.append(o)
                if o and o[0] in ("BUY_PRODUCT", "BUY_ANIMAL") and len(o) >= 3:
                    avail[o[1]] = avail.get(o[1], 0) + max(0, _int(o[2]))
        action["market"] = kept

    # ---- layer: dead_stock ----------------------------------------------------
    def _dead_stock(self, action, view, projected, route, step):
        """tetsutani dead_stock: stock beyond everything the rest of the route still
        plans to SELL is dead; sell it now when price > 1 (on day 29 everything not
        already in this step's orders is dead). Highest value lots first."""
        planned = {}
        for o in action.get("market") or []:
            if o and o[0] == "SELL" and len(o) >= 3:
                planned[o[1]] = planned.get(o[1], 0) + _int(o[2])
        day = step // self.cfg["turns_per_day"]
        extra = []
        for item in PRODUCTS:
            have = projected.get(item, 0) - planned.get(item, 0)
            if have <= 0:
                continue
            surplus = have if day >= 29 else have - self.future_sells(route, item, step + 1)
            if surplus > 0 and view.prices.get(item, 0) > 1:
                extra.append(["SELL", item, surplus])
        extra.sort(key=lambda o: -view.prices.get(o[1], 0) * o[2])
        action["market"] = (action.get("market") or []) + extra

    # ---- layer: terminal_liquidation -----------------------------------------
    def _terminal_liquidation(self, action, projected, step):
        """fieldbook _terminal_sale: on the final acting step (>= 718) replace the
        market orders with a SELL of the whole projected shed."""
        if step < LAST_ACT_STEP:
            return
        action["market"] = [["SELL", item, qty] for item, qty in projected.items()
                            if qty > 0 and item in PRODUCTS][: self.cfg["max_orders"]]


# --------------------------------------------------------------------------- factory
def make_agent(routes, router=None, opponent_plan=None, **settings):
    """Build a Kaggle ``agent(observation, configuration)`` closure that never raises:
    a failure inside a layer falls back to the raw tape action, and a failure even
    before that falls back to PASS (with hands padded when possible)."""
    chassis = Chassis(routes, router, settings, opponent_plan)

    def agent(observation, configuration=None):
        try:
            return chassis.act(observation, configuration)
        except Exception:
            chassis.diagnostics["entry_fallbacks"] += 1
            try:
                step = _step_of(observation)
                player = _int(_get(observation, "player", 0))
                tape = chassis.routes.get(chassis.players.get(player, {}).get("route"),
                                          next(iter(chassis.routes.values())))
                if 0 <= step < len(tape):
                    return copy.deepcopy(tape[step])
            except Exception:
                pass
            try:
                farms = _get(observation, "farms", []) or []
                hands = _get(farms[_int(_get(observation, "player", 0))], "hands", []) or []
                return {"farmer": ["PASS"], "hands": [["PASS"] for _ in hands], "market": []}
            except Exception:
                return copy.deepcopy(PASS_ACTION)

    agent.chassis = chassis
    return agent

# codez-v54 H009: learned production route from a public ra5anchor demonstration.
# This is an imitation-derived prototype, not the rival source program and not proof of generalization.
import base64 as _codezdonor_b64
import zlib as _codezdonor_zlib
_CODEZDONOR_ROUTE=json.loads(_codezdonor_zlib.decompress(_codezdonor_b64.b64decode('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')))
_CODEZDONOR_CONTROLLER=make_agent({0:_CODEZDONOR_ROUTE})
_CODEZ_STATS={}
def codez_donor_route_agent(observation,configuration=None):
    action=_CODEZDONOR_CONTROLLER(observation,configuration)
    _CODEZ_STATS.update(_CODEZDONOR_CONTROLLER.chassis.diagnostics)
    return action
