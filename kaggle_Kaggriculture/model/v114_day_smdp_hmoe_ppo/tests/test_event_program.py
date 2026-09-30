import ast
import copy
import dataclasses
import unittest
from pathlib import Path

from event_program import (
    CropRecipe,
    MacroActionMask,
    MacroDecision,
    MacroPlanExecutor,
    ProductionLine,
    SellStyle,
    TerminalMode,
)


def empty_board():
    return [
        [None if x < 5 and y < 5 else "LOCKED" for x in range(10)]
        for y in range(10)
    ]


def make_observation(
    *,
    step=0,
    money=3000,
    farmer=(0, 0),
    hands=(),
    tiles=None,
    seeds=None,
    shed=None,
    inventories=None,
    prices=None,
):
    hands = [list(position) for position in hands]
    products = (
        "WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
        "EGG", "MILK", "WOOL", "FERTILIZER",
    )
    crop_names = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON")
    seed_state = {crop: 0 for crop in crop_names}
    seed_state.update(seeds or {})
    shed_state = {product: 0 for product in products}
    shed_state.update(shed or {})
    base_prices = {
        "WHEAT": 25, "CARROT": 35, "TOMATO": 60,
        "STRAWBERRY": 120, "MELON": 250, "EGG": 50,
        "MILK": 160, "WOOL": 200, "FERTILIZER": 100,
    }
    base_prices.update(prices or {})
    unit_inventories = copy.deepcopy(inventories or [{} for _ in range(1 + len(hands))])
    board = copy.deepcopy(tiles if tiles is not None else empty_board())
    own_farm = {
        "money": float(money),
        "tiles": board,
        "farmer": list(farmer),
        "hands": hands,
        "unlocked_quadrants": ["NW"],
        "hires_today": 0,
    }
    opponent = copy.deepcopy(own_farm)
    return {
        "step": step,
        "day": step // 24,
        "hour": step % 24,
        "player": 0,
        "farms": [own_farm, opponent],
        "private": {
            "shed": shed_state,
            "seeds": seed_state,
            "inventories": unit_inventories,
        },
        "market": {
            "inventory": {product: 10000 for product in products},
            "prices": base_prices,
        },
        "town": {"unlocked_shops": []},
    }


def decision(
    production_line="WHEAT",
    worker_cap=1,
    cash_reserve=0,
    sell_style="HOLD",
    terminal_mode="NORMAL",
):
    return MacroDecision(
        production_line=production_line,
        worker_cap=worker_cap,
        cash_reserve=cash_reserve,
        sell_style=sell_style,
        terminal_mode=terminal_mode,
    )


def market_orders(action, operation):
    return [order for order in action["market"] if order and order[0] == operation]


class MacroContractTests(unittest.TestCase):
    def test_macro_decision_has_exact_five_fields_and_valid_domains(self):
        self.assertEqual(
            [field.name for field in dataclasses.fields(MacroDecision)],
            [
                "production_line",
                "worker_cap",
                "cash_reserve",
                "sell_style",
                "terminal_mode",
            ],
        )
        value = decision("MELON", 4, 1500, "PRICE_GATE", "LIQUIDATE")
        self.assertIs(value.production_line, ProductionLine.MELON)
        self.assertIs(value.sell_style, SellStyle.PRICE_GATE)
        self.assertIs(value.terminal_mode, TerminalMode.LIQUIDATE)
        with self.assertRaises(ValueError):
            decision(worker_cap=3)
        with self.assertRaises(ValueError):
            decision(cash_reserve=100)

    def test_macro_mask_uses_current_observation_and_terminal_boundary(self):
        obs = make_observation(step=10, money=700, hands=((1, 1),))
        mask = MacroActionMask.from_observation(obs)
        self.assertEqual(mask.worker_caps, (2, 4))
        self.assertEqual(mask.cash_reserves, (0, 500))
        self.assertIn(SellStyle.HOLD, mask.sell_styles)
        self.assertEqual(mask.terminal_modes, (TerminalMode.NORMAL,))

        expected_modes = {
            647: (TerminalMode.NORMAL,),
            648: (TerminalMode.NORMAL, TerminalMode.LIQUIDATE),
            670: (TerminalMode.NORMAL, TerminalMode.LIQUIDATE),
            671: (TerminalMode.LIQUIDATE,),
        }
        for step, expected in expected_modes.items():
            with self.subTest(step=step):
                boundary = MacroActionMask.from_observation(
                    make_observation(step=step, money=3000)
                )
                self.assertEqual(boundary.terminal_modes, expected)
                if step >= 671:
                    self.assertEqual(
                        boundary.sell_styles, (SellStyle.IMMEDIATE,)
                    )

    def test_active_crop_route_blocks_cross_line_switch_despite_empty_tiles(self):
        board = [[None for _ in range(10)] for _ in range(10)]
        board[0][0] = {
            "kind": "PLANT",
            "crop": "WHEAT",
            "planted_day": 0,
            "yield_units": 2,
            "watered_today": False,
        }
        obs = make_observation(step=24, tiles=board)
        mask = MacroActionMask.from_observation(obs)
        self.assertEqual(mask.production_lines, (ProductionLine.WHEAT,))

    def test_plan_is_immutable_within_day_and_replaceable_next_day(self):
        executor = MacroPlanExecutor()
        obs = make_observation(step=3, seeds={"WHEAT": 1, "CARROT": 1})
        wheat = decision("WHEAT")
        carrot = decision("CARROT")
        state = executor.activate(obs, wheat)

        same_day = executor.step(obs, state, daily_decision=carrot)
        self.assertIs(same_day.state.decision.production_line, ProductionLine.WHEAT)
        self.assertEqual(same_day.action["farmer"], ["PLANT", "WHEAT"])
        self.assertFalse(same_day.audit["decision_updated"])

        next_obs = make_observation(step=24, seeds={"WHEAT": 1, "CARROT": 1})
        next_day = executor.step(next_obs, same_day.state, daily_decision=carrot)
        self.assertIs(next_day.state.decision.production_line, ProductionLine.CARROT)
        self.assertEqual(next_day.action["farmer"], ["PLANT", "CARROT"])
        self.assertTrue(next_day.audit["decision_updated"])


class CropRecipeTests(unittest.TestCase):
    def test_one_time_crop_requires_age_and_positive_yield(self):
        board = [["LOCKED" for _ in range(10)] for _ in range(10)]
        board[0][0] = {
            "kind": "PLANT",
            "crop": "WHEAT",
            "planted_day": 0,
            "watered_today": False,
            "yield_units": 1,
        }
        immature = make_observation(step=24, tiles=board)
        tasks = CropRecipe("WHEAT").build_tasks(immature)
        self.assertNotIn("HARVEST", [task.stage for task in tasks])
        self.assertEqual([task.stage for task in tasks], ["WATER"])

        mature = make_observation(step=48, tiles=board)
        tasks = CropRecipe("WHEAT").build_tasks(mature)
        self.assertEqual([task.stage for task in tasks], ["HARVEST"])

        no_yield = copy.deepcopy(mature)
        no_yield["farms"][0]["tiles"][0][0]["yield_units"] = 0
        tasks = CropRecipe("WHEAT").build_tasks(no_yield)
        self.assertNotIn("HARVEST", [task.stage for task in tasks])

    def test_task_graph_priority_and_nearest_assignment_are_deterministic(self):
        board = [["LOCKED" for _ in range(10)] for _ in range(10)]
        board[1][0] = {
            "kind": "PLANT",
            "crop": "CARROT",
            "planted_day": 0,
            "watered_today": False,
            "yield_units": 2,
        }
        board[3][4] = {"kind": "WEED"}
        obs = make_observation(
            step=48,
            farmer=(0, 0),
            hands=((4, 4),),
            tiles=board,
            inventories=[{}, {}],
        )
        executor = MacroPlanExecutor()
        state = executor.activate(obs, decision("WHEAT", worker_cap=2))
        first = executor.step(obs, state)
        second = executor.step(copy.deepcopy(obs), state)
        self.assertEqual(first.action, second.action)
        self.assertEqual(first.audit, second.audit)
        self.assertEqual(first.action["farmer"], ["SOUTH"])
        self.assertEqual(first.action["hands"], [["NORTH"]])
        self.assertEqual(
            [stage.name for stage in CropRecipe("WHEAT").task_graph],
            ["HARVEST", "WATER", "CLEAR_WEED", "PLANT"],
        )


class FieldCausalityTests(unittest.TestCase):
    def setUp(self):
        self.executor = MacroPlanExecutor()

    def run_plan(self, obs, macro):
        return self.executor.step(obs, self.executor.activate(obs, macro))

    def test_production_line_changes_plant_and_seed_procurement(self):
        obs = make_observation(seeds={"WHEAT": 1, "CARROT": 1})
        wheat = self.run_plan(obs, decision("WHEAT"))
        carrot = self.run_plan(obs, decision("CARROT"))
        self.assertEqual(wheat.action["farmer"], ["PLANT", "WHEAT"])
        self.assertEqual(carrot.action["farmer"], ["PLANT", "CARROT"])
        self.assertEqual(market_orders(wheat.action, "BUY_SEED")[0][1], "WHEAT")
        self.assertEqual(market_orders(carrot.action, "BUY_SEED")[0][1], "CARROT")

    def test_worker_cap_changes_hire_count_without_exceeding_cap(self):
        obs = make_observation(seeds={"WHEAT": 25})
        cap_one = self.run_plan(obs, decision(worker_cap=1))
        cap_four = self.run_plan(obs, decision(worker_cap=4))
        self.assertEqual(len(market_orders(cap_one.action, "HIRE")), 0)
        self.assertEqual(len(market_orders(cap_four.action, "HIRE")), 3)
        self.assertEqual(cap_four.audit["market"]["planned_hires"], 3)

    def test_cash_reserve_reduces_seed_budget(self):
        obs = make_observation(money=1600)
        reserve_zero = self.run_plan(obs, decision(cash_reserve=0))
        reserve_high = self.run_plan(obs, decision(cash_reserve=1500))
        zero_quantity = market_orders(reserve_zero.action, "BUY_SEED")[0][2]
        high_quantity = market_orders(reserve_high.action, "BUY_SEED")[0][2]
        self.assertGreater(zero_quantity, high_quantity)
        self.assertLessEqual(reserve_high.audit["market"]["planned_spend"], 100)
        self.assertGreaterEqual(
            1600 - reserve_high.audit["market"]["planned_spend"], 1500
        )

    def test_sell_style_changes_only_safe_inventory_sales(self):
        obs = make_observation(
            shed={"WHEAT": 3}, prices={"WHEAT": 20}, seeds={"WHEAT": 25}
        )
        immediate = self.run_plan(obs, decision(sell_style="IMMEDIATE"))
        gated = self.run_plan(obs, decision(sell_style="PRICE_GATE"))
        hold = self.run_plan(obs, decision(sell_style="HOLD"))
        self.assertEqual(market_orders(immediate.action, "SELL"), [["SELL", "WHEAT", 3]])
        self.assertEqual(market_orders(gated.action, "SELL"), [])
        self.assertEqual(market_orders(hold.action, "SELL"), [])

    def test_terminal_mode_is_ignored_midseason_and_acts_on_final_day(self):
        common = dict(
            farmer=(0, 0),
            money=3000,
            shed={"CARROT": 2},
            inventories=[{"WHEAT": 1}],
            seeds={"WHEAT": 1},
        )
        midseason = make_observation(step=647, **common)
        illegal_liquidate = self.run_plan(
            midseason, decision(worker_cap=2, terminal_mode="LIQUIDATE")
        )
        self.assertTrue(market_orders(illegal_liquidate.action, "HIRE"))
        self.assertTrue(market_orders(illegal_liquidate.action, "BUY_SEED"))
        self.assertEqual(illegal_liquidate.audit["effective_terminal_mode"], "NORMAL")
        self.assertFalse(illegal_liquidate.audit["macro_decision_allowed"])

        final_day = make_observation(step=648, **common)
        normal = self.run_plan(
            final_day, decision(worker_cap=2, terminal_mode="NORMAL")
        )
        liquidate = self.run_plan(
            final_day, decision(worker_cap=2, terminal_mode="LIQUIDATE")
        )
        self.assertTrue(market_orders(normal.action, "HIRE"))
        self.assertFalse(market_orders(liquidate.action, "HIRE"))
        self.assertFalse(market_orders(liquidate.action, "BUY_SEED"))
        self.assertEqual(
            market_orders(liquidate.action, "SELL"), [["SELL", "CARROT", 2]]
        )
        self.assertNotEqual(normal.action["farmer"], liquidate.action["farmer"])
        self.assertTrue(liquidate.audit["macro_decision_allowed"])


class SafetyAndSchemaTests(unittest.TestCase):
    def setUp(self):
        self.executor = MacroPlanExecutor()

    def test_market_ordering_budget_and_quantity_contracts(self):
        obs = make_observation(
            money=1600,
            shed={"WHEAT": 7},
            prices={"WHEAT": 30},
        )
        macro = decision(
            "WHEAT", worker_cap=4, cash_reserve=1500, sell_style="IMMEDIATE"
        )
        result = self.executor.step(obs, self.executor.activate(obs, macro))
        operations = [order[0] for order in result.action["market"]]
        self.assertEqual(operations[:4], ["SELL", "HIRE", "HIRE", "HIRE"])
        self.assertEqual(market_orders(result.action, "SELL")[0][2], 7)
        self.assertLessEqual(result.audit["market"]["planned_spend"], 100)
        self.assertEqual(result.audit["violations"], [])

    def test_terminal_boundary_forbids_procurement_and_returns_to_shed(self):
        obs = make_observation(
            step=671,
            farmer=(0, 0),
            money=3000,
            shed={"CARROT": 3},
            inventories=[{"WHEAT": 2}],
        )
        macro = decision("WHEAT", worker_cap=4, terminal_mode="NORMAL")
        result = self.executor.step(obs, self.executor.activate(obs, macro))
        self.assertEqual(result.action["farmer"], ["EAST"])
        self.assertEqual(market_orders(result.action, "SELL"), [["SELL", "CARROT", 3]])
        self.assertFalse(market_orders(result.action, "HIRE"))
        self.assertFalse(market_orders(result.action, "BUY_SEED"))
        self.assertTrue(result.audit["forced_terminal"])

        at_shed = make_observation(
            step=671,
            farmer=(4, 4),
            shed={"CARROT": 3},
            inventories=[{"WHEAT": 2}],
        )
        dropped = self.executor.step(at_shed, self.executor.activate(at_shed, macro))
        self.assertEqual(dropped.action["farmer"], ["DROP"])
        self.assertEqual(
            market_orders(dropped.action, "SELL"),
            [["SELL", "WHEAT", 2], ["SELL", "CARROT", 3]],
        )

    def test_same_turn_drop_projection_obeys_total_shed_capacity_and_item_order(self):
        obs = make_observation(
            step=671,
            farmer=(4, 4),
            shed={"CARROT": 3, "GOOSE": 96},
            inventories=[{"GOOSE": 2, "WHEAT": 5}],
        )
        macro = decision(terminal_mode="LIQUIDATE")
        result = self.executor.step(obs, self.executor.activate(obs, macro))
        self.assertEqual(result.action["farmer"], ["DROP"])
        # Only one shed slot exists.  The first GOOSE consumes it, so none of
        # the carried WHEAT can be projected into the same-turn sale.
        self.assertEqual(
            market_orders(result.action, "SELL"), [["SELL", "CARROT", 3]]
        )
        self.assertEqual(result.audit["violations"], [])

    def test_action_matches_official_schema_and_runs_one_official_step(self):
        from kaggle_environments import make

        environment = make(
            "kaggriculture", debug=True, configuration={"seed": 114009}
        )
        environment.reset(num_agents=2)
        observation = environment.state[0].observation
        macro = decision("TOMATO", worker_cap=2, cash_reserve=500)
        result = self.executor.step(
            observation, self.executor.activate(observation, macro)
        )
        self.assertEqual(set(result.action), {"farmer", "hands", "market"})
        self.assertIsInstance(result.action["farmer"], list)
        self.assertEqual(len(result.action["hands"]), 0)
        self.assertTrue(all(isinstance(order, list) for order in result.action["market"]))
        environment.step(
            [result.action, {"farmer": ["PASS"], "hands": [], "market": []}]
        )
        self.assertEqual(environment.state[0].status, "ACTIVE")

    def test_module_has_no_external_policy_or_file_loading_dependency(self):
        module_path = Path(__file__).resolve().parents[1] / "event_program.py"
        source = module_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported_roots = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".")[0])
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                self.assertNotEqual(node.func.id, "open")
        self.assertLessEqual(
            imported_roots,
            {"__future__", "dataclasses", "enum", "typing"},
        )


if __name__ == "__main__":
    unittest.main()
