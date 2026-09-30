"""RC9 opponent-path overlay appended to the frozen RC8 executor.

This file is maintainable source.  ``packager.py`` appends it to the audited
RC8 candidate and emits the self-contained submission artifact ``main.py``.
It intentionally has no imports: the RC8 prelude provides stdlib imports and
all engine constants/helpers used below.
"""


RC9_SCHEMA = "v116-rc9-opponent-path-v1"
RC9_ROUTER_DEPTH = 2
RC9_MODES = (
    "base",
    "router_log_only",
    "target_only",
    "market_only",
    "full",
    "fixed_collision",
    "fixed_scarcity",
    "fixed_liquidator",
)
RC9_PATHS = ("collision", "scarcity", "liquidator")
RC9_FLOW_ALPHA = 0.5
RC9_FLOW_TRIGGER = 12.0
RC9_MARKET_BAND = 24
RC9_PREEMPT_CAP = 12
RC9_STAGE_DAYS = (5, 9)
ANIMAL_PRODUCT_TO_KIND = {facts["product"]: kind for kind, facts in ANIMALS.items()}


# Exact p0064_3f0eb3eec9 freeze.  The upstream ParamSpec validator and compiler
# remain authoritative; this overlay only changes the frozen default.
DEFAULT_PARAMS: dict[str, Any] = {
    "experts": {
        "wool": {"focus2": 2, "focus3": 4, "donor_template": 0, "animal_suffix": 0},
        "dairy_berry": {"focus2": 2, "focus3": 4, "donor_template": 0, "animal_suffix": 0},
        "tomato_market": {"focus2": 2, "focus3": 6, "donor_template": 0, "animal_suffix": 0},
        "root": {"focus2": 2, "focus3": 4, "donor_template": 0, "animal_suffix": 0},
        "grain_egg": {"focus2": 2, "focus3": 4, "donor_template": 0, "animal_suffix": 0},
    },
    "auction": {
        "harvest_priority": 3,
        "plant_priority": 2,
        "place_priority": 3,
        "sticky_bonus": 5,
        "role_penalty": 3,
        "replacement": "none",
    },
    "market": {
        "finance_stress": 48,
        "ordinary_stress": 8,
        "sale_floor": 0.45,
        "pressure": 88,
        "liquidation": 708,
        "regular_cap": 36,
    },
}


def _rc9_step(obs: dict[str, Any]) -> int:
    return int(obs.get("step", int(obs.get("day", 0)) * 24
                       + int(obs.get("hour", 0))) or 0)


def _rc9_shops(obs: dict[str, Any]) -> tuple[str, ...]:
    return tuple(str(value) for value in
                 list((obs.get("town") or {}).get("unlocked_shops", []) or []))


def _rc9_market_inventory(obs: dict[str, Any]) -> dict[str, int]:
    raw = (obs.get("market") or {}).get("inventory", {}) or {}
    return {item: int(raw.get(item, 10000) or 10000) for item in PRODUCTS}


def _rc9_market_prices(obs: dict[str, Any]) -> dict[str, int]:
    raw = (obs.get("market") or {}).get("prices", {}) or {}
    return {item: int(raw.get(item, BASE_PRICE[item]) or BASE_PRICE[item])
            for item in PRODUCTS}


def _rc9_demand(step: int, shops: tuple[str, ...]) -> Counter[str]:
    """Known public demand scheduled for *step* and its then-visible shops."""
    demand: Counter[str] = Counter()
    if int(step) % 4 == 0:
        for shop in shops:
            goods = SHOP_PRODUCTS.get(str(shop), ())
            multiplier = 2 if len(goods) == 1 else 1
            for good in goods:
                demand[good] += multiplier
    if int(step) % 24 == 0:
        for good in PRODUCTS:
            if good != "FERTILIZER":
                demand[good] += 1
    return demand


def _rc9_capacity(farm: dict[str, Any]) -> Counter[str]:
    grid = list((farm or {}).get("tiles", []) or [])
    crops, animals, _structures = _counts(grid)
    result: Counter[str] = Counter({crop: int(crops[crop]) for crop in CROPS})
    for kind, facts in ANIMALS.items():
        result[str(facts["product"])] += int(animals[kind])
    return result


class OpponentPathExecutor(ShopRouterExecutor):
    """p0064 executor with an auditable public-state path overlay."""

    def __init__(self, params: dict[str, Any], mode: str = "full") -> None:
        if mode not in RC9_MODES:
            raise ValueError(f"unknown RC9 mode {mode!r}")
        super().__init__(params)
        self.mode = mode
        self.target_enabled = mode in {
            "target_only", "full", "fixed_collision", "fixed_scarcity",
            "fixed_liquidator",
        }
        self.market_enabled = mode in {
            "market_only", "full", "fixed_collision", "fixed_scarcity",
            "fixed_liquidator",
        }
        self.forced_path = (mode.removeprefix("fixed_")
                            if mode.startswith("fixed_") else None)

        self.observed_first_shop: str | None = None
        self.observed_shop_history: list[tuple[int, tuple[str, ...]]] = []
        self.path_leaf = self.forced_path or "liquidator"
        self.path_candidate = self.path_leaf
        self.path_streak = 0
        self.path_reason = "initial"
        self.path_counts: Counter[str] = Counter({self.path_leaf: 1})

        self.prev_step: int | None = None
        self.prev_shops: tuple[str, ...] = ()
        self.prev_market_inventory: dict[str, int] = {}
        self.prev_market_prices: dict[str, int] = {}
        self.prev_own_market_items: set[str] = set()
        self.current_contaminated: set[str] = set()
        self.latest_rival_flow: dict[str, float] = {}
        self.flow_ema: dict[str, float] = {}
        self.clean_observations: Counter[str] = Counter()
        self.last_clean_step: dict[str, int] = {}
        self.market_resets = 0

        self.current_step = -1
        self.current_inventory: dict[str, int] = {}
        self.current_prices: dict[str, int] = {}
        self.self_capacity: Counter[str] = Counter()
        self.opponent_capacity: Counter[str] = Counter()
        self.previous_opponent_capacity: Counter[str] = Counter()
        self.collision_product: str | None = None
        self.scarcity_product: str | None = None

        self.stage_commits: dict[int, dict[str, Any]] = {}
        self.crop_overlays: dict[int, Counter[str]] = {}
        self.animal_overlays: dict[int, Counter[str]] = {}
        self.market_policy_counts: Counter[str] = Counter()

    def _reset_market_history(self) -> None:
        self.current_contaminated.clear()
        self.latest_rival_flow.clear()
        self.flow_ema.clear()
        self.clean_observations.clear()
        self.last_clean_step.clear()
        self.prev_own_market_items.clear()
        self.market_resets += 1

    def _begin_observation(self, obs: dict[str, Any]) -> None:
        """Audit obs_t before routing or action generation.

        Demand correction intentionally uses ``prev_step`` and ``prev_shops``.
        A product touched by our prior SELL/BUY_PRODUCT is contaminated and its
        residual is not estimated.  With no such order the residual is exact:
        ``(I_t - I_prev) + D_{t-1}``.
        """
        step = _rc9_step(obs)
        shops = _rc9_shops(obs)
        inventory = _rc9_market_inventory(obs)
        prices = _rc9_market_prices(obs)
        self.current_step = step
        self.current_inventory = inventory
        self.current_prices = prices

        if shops and self.observed_first_shop is None:
            self.observed_first_shop = shops[0]
        if not self.observed_shop_history or self.observed_shop_history[-1][1] != shops:
            self.observed_shop_history.append((step, shops))

        if self.prev_step is not None:
            if step != self.prev_step + 1:
                self._reset_market_history()
            else:
                demand = _rc9_demand(self.prev_step, self.prev_shops)
                contaminated: set[str] = set()
                for item in PRODUCTS:
                    if item in self.prev_own_market_items:
                        contaminated.add(item)
                        continue
                    rival = float(inventory[item] - self.prev_market_inventory[item]
                                  + demand[item])
                    self.latest_rival_flow[item] = rival
                    if item in self.flow_ema:
                        self.flow_ema[item] = (RC9_FLOW_ALPHA * rival
                                               + (1.0 - RC9_FLOW_ALPHA)
                                               * self.flow_ema[item])
                    else:
                        self.flow_ema[item] = rival
                    self.clean_observations[item] += 1
                    self.last_clean_step[item] = step
                self.current_contaminated = contaminated
        else:
            self.current_contaminated = set()

        self.prev_step = step
        self.prev_shops = shops
        self.prev_market_inventory = dict(inventory)
        self.prev_market_prices = dict(prices)
        self.prev_own_market_items = set()

    def _record_own_market_orders(self, orders: list[list[Any]]) -> None:
        touched: set[str] = set()
        for order in orders:
            if not order or order[0] not in {"SELL", "BUY_PRODUCT"} or len(order) < 2:
                continue
            item = str(order[1])
            if item in PRODUCTS:
                touched.add(item)
        self.prev_own_market_items = touched

    def _refresh_capacities(self, obs: dict[str, Any]) -> None:
        farms = list(obs.get("farms") or [{}, {}])
        seat = self._seat(obs)
        own = farms[seat] if seat < len(farms) else {}
        opponent_index = 1 - seat if len(farms) >= 2 else seat
        opponent = farms[opponent_index] if opponent_index < len(farms) else {}
        self.previous_opponent_capacity = Counter(self.opponent_capacity)
        self.self_capacity = _rc9_capacity(own)
        self.opponent_capacity = _rc9_capacity(opponent)

    def _planned_expert(self) -> str:
        if self.committed:
            return self.expert
        if self.observed_first_shop:
            return route_expert([self.observed_first_shop])
        return "grain_egg"

    def _planned_products(self) -> Counter[str]:
        goal = daily_goal(self.genomes[self._planned_expert()], 29)
        result: Counter[str] = Counter({crop: int(goal["crops"].get(crop, 0))
                                       for crop in CROPS})
        for kind, count in goal["animals"].items():
            result[str(ANIMALS[kind]["product"])] += int(count)
        return result

    def _clean_now(self, item: str) -> bool:
        return (item not in self.current_contaminated
                and self.last_clean_step.get(item) == self.current_step)

    def _market_collision(self, item: str) -> bool:
        if not self._clean_now(item):
            return False
        return bool(
            self.flow_ema.get(item, 0.0) >= RC9_FLOW_TRIGGER
            or self.current_inventory.get(item, 10000) >= 10000 + RC9_MARKET_BAND
            or self.current_prices.get(item, BASE_PRICE[item])
            <= int(0.75 * BASE_PRICE[item])
        )

    def _market_scarcity(self, item: str) -> bool:
        if not self._clean_now(item):
            return False
        return bool(
            self.flow_ema.get(item, 0.0) <= -RC9_FLOW_TRIGGER
            or self.current_inventory.get(item, 10000) <= 10000 - RC9_MARKET_BAND
            or self.current_prices.get(item, BASE_PRICE[item]) >= BASE_PRICE[item] + 1
        )

    def _collision_candidates(self) -> list[str]:
        planned = self._planned_products()
        candidates: list[str] = []
        for item in PRODUCTS:
            if item == "FERTILIZER":
                continue
            remaining = max(0, planned[item] - self.self_capacity[item])
            if remaining < 4:
                continue
            capacity_hit = self.opponent_capacity[item] >= max(
                4, int(math.ceil(0.5 * max(1, planned[item])))
            )
            # A clean scarcity observation vetoes the ambiguous capacity-only
            # trigger (notably WHEAT used as feed by the opponent).
            if ((capacity_hit and not self._market_scarcity(item))
                    or self._market_collision(item)):
                candidates.append(item)
        return candidates

    def _choose_collision(self, candidates: list[str]) -> str | None:
        if not candidates:
            return None
        planned = self._planned_products()
        return max(candidates, key=lambda item: (
            max(0, planned[item] - self.self_capacity[item])
            * max(1, self.opponent_capacity[item])
            * max(0.25, 1.0 - self.current_prices.get(item, BASE_PRICE[item])
                  / max(1, BASE_PRICE[item])),
            -PRODUCTS.index(item),
        ))

    def _scarcity_candidates(self) -> list[str]:
        shop = self.observed_first_shop or ""
        return [item for item in SHOP_PRODUCTS.get(shop, ())
                if item in PRODUCTS and self._market_scarcity(item)]

    def _choose_scarcity(self, candidates: list[str]) -> str | None:
        if not candidates:
            return None
        return max(candidates, key=lambda item: (
            -self.flow_ema.get(item, 0.0),
            self.current_prices.get(item, BASE_PRICE[item]) / max(1, BASE_PRICE[item]),
            -self.opponent_capacity[item],
            -PRODUCTS.index(item),
        ))

    def _classify_path(self) -> None:
        collisions = self._collision_candidates()
        scarcities = self._scarcity_candidates()
        collision = self._choose_collision(collisions)
        scarcity = self._choose_scarcity(scarcities)
        if self.forced_path == "collision" and collision is None:
            collision = self._forced_collision_fallback()
        if self.forced_path == "scarcity" and scarcity is None:
            scarcity = self._forced_scarcity_fallback()
        self.collision_product = collision
        self.scarcity_product = scarcity

        if self.forced_path:
            candidate = self.forced_path
            reason = "forced"
        elif collision is not None:
            candidate = "collision"
            reason = f"collision:{collision}"
        elif scarcity is not None:
            candidate = "scarcity"
            reason = f"scarcity:{scarcity}"
        else:
            candidate = "liquidator"
            clean_breadth = sum(
                self._clean_now(item) and self.flow_ema.get(item, 0.0) >= RC9_FLOW_TRIGGER
                for item in PRODUCTS if item != "FERTILIZER"
            )
            reason = f"neutral_or_liquidator:breadth={clean_breadth}"

        if candidate == self.path_candidate:
            self.path_streak += 1
        else:
            self.path_candidate = candidate
            self.path_streak = 1

        # Fixed leaves are immediate.  A clean market collision is also an
        # immediate safety transition; all other online changes need two
        # consecutive public observations.
        immediate = bool(
            self.forced_path
            or (candidate == "collision" and collision is not None
                and self._market_collision(collision))
        )
        if candidate != self.path_leaf and (immediate or self.path_streak >= 2):
            self.path_leaf = candidate
            self.path_counts[candidate] += 1
        self.path_reason = reason

    def _select_escape_crop(self, excluded: set[str]) -> str | None:
        shop_goods = set(SHOP_PRODUCTS.get(self.observed_first_shop or "", ()))
        choices = [crop for crop in CROPS if crop not in excluded]
        if not choices:
            return None
        return max(choices, key=lambda crop: (
            int(crop in shop_goods),
            int(self._market_scarcity(crop)),
            self.current_prices.get(crop, BASE_PRICE[crop]) / max(1, BASE_PRICE[crop]),
            -self.opponent_capacity[crop],
            -list(CROPS).index(crop),
        ))

    def _stage_crop_transfer(self, stage_day: int, source: str, destination: str,
                             budget: int) -> dict[str, Any] | None:
        genome = self.genomes[self.expert]
        block_index = 1 if stage_day == 5 else 2
        block = Counter(genome["crop_blocks"][block_index])
        amount = min(int(budget), int(block[source]))
        if source == "WHEAT":
            final_wheat = int(daily_goal(genome, 29)["crops"].get("WHEAT", 0))
            existing_delta = sum(overlay["WHEAT"] for overlay in self.crop_overlays.values())
            amount = min(amount, max(0, final_wheat + existing_delta - 18))
        if amount <= 0 or source == destination:
            return None
        overlay: Counter[str] = Counter({source: -amount, destination: amount})
        self.crop_overlays[stage_day] = overlay
        return {"kind": "crop", "source": source, "destination": destination,
                "amount": amount}

    def _stage_animal_transfer(self, stage_day: int, source_product: str,
                               destination_product: str, budget: int) -> dict[str, Any] | None:
        source_kind = ANIMAL_PRODUCT_TO_KIND.get(source_product)
        destination_kind = ANIMAL_PRODUCT_TO_KIND.get(destination_product)
        if not source_kind or not destination_kind or source_kind == destination_kind:
            return None
        # Preserve structure compatibility for the minimal overlay.
        source_structure = ANIMALS[source_kind]["structure"]
        destination_structure = ANIMALS[destination_kind]["structure"]
        if source_structure != destination_structure:
            return None
        wave_count = sum(int(count) for day, kind, count
                         in self.genomes[self.expert]["animal_waves"]
                         if int(day) == stage_day and kind == source_kind)
        amount = min(wave_count, max(0, int(budget) // 2))
        if amount <= 0:
            return None
        overlay: Counter[str] = Counter({source_kind: -amount, destination_kind: amount})
        self.animal_overlays[stage_day] = overlay
        return {"kind": "animal", "source": source_kind,
                "destination": destination_kind, "amount": amount}

    def _forced_collision_fallback(self) -> str | None:
        planned = self._planned_products()
        choices = [item for item in PRODUCTS if item != "FERTILIZER"
                   and planned[item] - self.self_capacity[item] >= 4]
        if not choices:
            return None
        return max(choices, key=lambda item: (
            min(planned[item], self.opponent_capacity[item]),
            self.opponent_capacity[item],
            -PRODUCTS.index(item),
        ))

    def _forced_scarcity_fallback(self) -> str | None:
        goods = [item for item in SHOP_PRODUCTS.get(self.observed_first_shop or "", ())
                 if item in PRODUCTS]
        if not goods:
            return None
        return max(goods, key=lambda item: (
            self.current_prices.get(item, BASE_PRICE[item]) / max(1, BASE_PRICE[item]),
            -self.opponent_capacity[item],
            -PRODUCTS.index(item),
        ))

    def _commit_stage(self, stage_day: int) -> None:
        if stage_day in self.stage_commits:
            return
        leaf = self.forced_path or self.path_leaf
        expert_params = self.params["experts"][self.expert]
        budget = int(expert_params["focus2" if stage_day == 5 else "focus3"])
        decision: dict[str, Any] = {"path": leaf, "budget": budget, "change": None}

        if leaf == "collision":
            source = self.collision_product
            if source is None and self.forced_path == "collision":
                source = self._forced_collision_fallback()
            if source in CROPS:
                excluded = set(self._collision_candidates())
                destination = self._select_escape_crop(excluded)
                if destination:
                    decision["change"] = self._stage_crop_transfer(
                        stage_day, source, destination, budget
                    )
            elif source in ANIMAL_PRODUCT_TO_KIND:
                alternatives = [product for product in ("MILK", "WOOL", "EGG")
                                if product != source and product not in self._collision_candidates()]
                if alternatives:
                    destination = max(alternatives, key=lambda item: (
                        int(item in SHOP_PRODUCTS.get(self.observed_first_shop or "", ())),
                        self.current_prices.get(item, BASE_PRICE[item]) / max(1, BASE_PRICE[item]),
                        -self.opponent_capacity[item],
                    ))
                    decision["change"] = self._stage_animal_transfer(
                        stage_day, source, destination, budget
                    )

        elif leaf == "scarcity":
            destination = self.scarcity_product
            if destination is None and self.forced_path == "scarcity":
                destination = self._forced_scarcity_fallback()
            if destination in CROPS:
                block_index = 1 if stage_day == 5 else 2
                block = Counter(self.genomes[self.expert]["crop_blocks"][block_index])
                donors = [crop for crop in CROPS if crop != destination and block[crop] > 0]
                donors.sort(key=lambda crop: (
                    crop == "WHEAT",
                    self.current_prices.get(crop, BASE_PRICE[crop]) / max(1, BASE_PRICE[crop]),
                    -block[crop],
                    list(CROPS).index(crop),
                ))
                if donors:
                    decision["change"] = self._stage_crop_transfer(
                        stage_day, donors[0], destination, budget
                    )
            elif destination in ANIMAL_PRODUCT_TO_KIND:
                destination_kind = ANIMAL_PRODUCT_TO_KIND[destination]
                same_structure = [facts["product"] for kind, facts in ANIMALS.items()
                                  if kind != destination_kind
                                  and facts["structure"] == ANIMALS[destination_kind]["structure"]]
                for source in same_structure:
                    change = self._stage_animal_transfer(
                        stage_day, source, destination, budget
                    )
                    if change:
                        decision["change"] = change
                        break

        self.stage_commits[stage_day] = decision

    def _maybe_commit_stages(self, day: int) -> None:
        if not self.target_enabled:
            return
        for stage_day in RC9_STAGE_DAYS:
            if day >= stage_day and stage_day not in self.stage_commits:
                self._commit_stage(stage_day)

    def goal(self, day: int) -> dict[str, Any]:
        goal = copy.deepcopy(super().goal(day))
        if not self.target_enabled:
            return goal
        for stage_day, overlay in self.crop_overlays.items():
            if int(day) < stage_day:
                continue
            crops = Counter(goal["crops"])
            crops.update(overlay)
            goal["crops"] = {crop: max(0, int(crops[crop])) for crop in CROPS
                             if int(crops[crop]) > 0}
        for stage_day, overlay in self.animal_overlays.items():
            if int(day) < stage_day:
                continue
            animals = Counter(goal["animals"])
            animals.update(overlay)
            goal["animals"] = {kind: max(0, int(animals[kind])) for kind in ANIMALS
                               if int(animals[kind]) > 0}
        goal["feed_reserve"] = 2 * sum(int(value) for value in goal["animals"].values())
        return goal

    @staticmethod
    def _has_non_sale_order(orders: list[list[Any]]) -> bool:
        return any(order and order[0] != "SELL" for order in orders)

    def _clean_broad_sell(self) -> int:
        return sum(self._clean_now(item)
                   and self.flow_ema.get(item, 0.0) >= RC9_FLOW_TRIGGER
                   for item in PRODUCTS if item != "FERTILIZER")

    def _apply_market_policy(self, obs: dict[str, Any],
                             orders: list[list[Any]]) -> list[list[Any]]:
        if not self.market_enabled:
            return orders
        step = _rc9_step(obs)
        if step >= int(self.market_params["liquidation"]):
            self.market_policy_counts["terminal_passthrough"] += 1
            return orders
        # Never remove a sale that the base executor may be using to finance a
        # same-turn purchase.  This is deliberately conservative and state-safe.
        if self._has_non_sale_order(orders):
            self.market_policy_counts["financing_passthrough"] += 1
            return orders

        leaf = self.forced_path or self.path_leaf
        result: list[list[Any]] = []
        for raw in orders:
            order = list(raw)
            if not order or order[0] != "SELL" or len(order) < 3:
                result.append(order)
                continue
            item = str(order[1])
            quantity = int(order[2])
            adjusted = quantity

            if leaf == "collision" and item == self.collision_product \
                    and self._clean_now(item):
                if self._market_collision(item):
                    adjusted = 0
                    self.market_policy_counts["collision_withhold"] += quantity
                elif self.current_prices.get(item, BASE_PRICE[item]) >= BASE_PRICE[item]:
                    adjusted = min(quantity, RC9_PREEMPT_CAP)
                    self.market_policy_counts["collision_preempt_cap"] += quantity - adjusted

            elif leaf == "scarcity" and item == self.scarcity_product \
                    and self._clean_now(item):
                if self.current_prices.get(item, BASE_PRICE[item]) < BASE_PRICE[item]:
                    adjusted = 0
                    self.market_policy_counts["scarcity_below_base_withhold"] += quantity
                else:
                    adjusted = min(quantity, RC9_PREEMPT_CAP)
                    self.market_policy_counts["scarcity_cap"] += quantity - adjusted

            elif leaf == "liquidator" and int(obs.get("day", 0) or 0) >= 27 \
                    and self._clean_broad_sell() >= 3 and self._market_collision(item):
                adjusted = (min(quantity, RC9_PREEMPT_CAP)
                            if self.current_prices.get(item, BASE_PRICE[item]) >= BASE_PRICE[item]
                            else 0)
                self.market_policy_counts["liquidator_stagger"] += quantity - adjusted

            if adjusted > 0:
                order[2] = adjusted
                result.append(order)
        return result[:10]

    def _market(self, obs: dict[str, Any], farm: dict[str, Any], grid: list[list[Any]],
                goal: dict[str, Any], seeds: dict[str, int], projected: dict[str, int],
                inventories: list[dict[str, Any]], pending_plants: Counter[str],
                true_harvests: Counter[str]) -> list[list[Any]]:
        orders = super()._market(obs, farm, grid, goal, seeds, projected,
                                 inventories, pending_plants, true_harvests)
        return self._apply_market_policy(obs, orders)

    def act(self, obs: dict[str, Any]) -> dict[str, Any]:
        # Required ordering: audit the transition obs_{t-1}->obs_t before any
        # route, goal, market, or action decision consumes obs_t.
        self._begin_observation(obs)
        self._refresh_capacities(obs)
        self._classify_path()
        self._route(obs)
        self._maybe_commit_stages(min(29, int(obs.get("day", 0) or 0)))
        action = super().act(obs)
        self._record_own_market_orders(list(action.get("market", []) or []))
        return action

    def diagnostics(self) -> dict[str, Any]:
        return {
            "schema": RC9_SCHEMA,
            "mode": self.mode,
            "router_depth": RC9_ROUTER_DEPTH,
            "first_shop_observed": self.observed_first_shop,
            "shop_is_exogenous": False,
            "base_expert": self.expert,
            "path_leaf": self.path_leaf,
            "path_candidate": self.path_candidate,
            "path_streak": self.path_streak,
            "path_reason": self.path_reason,
            "path_counts": dict(self.path_counts),
            "collision_product": self.collision_product,
            "scarcity_product": self.scarcity_product,
            "prev_step": self.prev_step,
            "market_resets": self.market_resets,
            "current_contaminated": sorted(self.current_contaminated),
            "clean_observations": dict(self.clean_observations),
            "latest_rival_flow": dict(self.latest_rival_flow),
            "flow_ema": dict(self.flow_ema),
            "self_capacity": dict(self.self_capacity),
            "opponent_capacity": dict(self.opponent_capacity),
            "stage_commits": copy.deepcopy(self.stage_commits),
            "crop_overlays": {str(day): dict(value)
                              for day, value in self.crop_overlays.items()},
            "animal_overlays": {str(day): dict(value)
                                for day, value in self.animal_overlays.items()},
            "market_policy_counts": dict(self.market_policy_counts),
            "base_audit": dict(self.audit),
        }


def build_executor(params: dict[str, Any], mode: str = "full") -> OpponentPathExecutor:
    errors = validate_params(params)
    if errors:
        raise ValueError("; ".join(errors))
    return OpponentPathExecutor(params, mode=mode)


DEFAULT_PARAMS_HASH = canonical_hash(DEFAULT_PARAMS)


def make_agent() -> Any:
    return build_executor(DEFAULT_PARAMS, "full").act


__all__ = [
    "DEFAULT_PARAMS", "DEFAULT_PARAMS_HASH", "PARAM_SPEC", "ParamSpec",
    "RC9_MODES", "RC9_PATHS", "RC9_ROUTER_DEPTH", "OpponentPathExecutor",
    "build_executor", "canonical_hash", "canonical_json", "compile_genomes",
    "make_agent", "route_expert", "validate_params",
]
