"""Executable deterministic opponent variants used by the audited league."""
from __future__ import annotations


def copy_action(action):
    return {"farmer": list((action or {}).get("farmer") or ["PASS"]), "hands": [list(x or ["PASS"]) for x in (action or {}).get("hands", [])], "market": [list(x or []) for x in (action or {}).get("market", [])]}


def forced_route(module, route):
    def agent(obs):
        module._ACTIONS = module._HIGH_ROUTE_ACTIONS if route else module._LOW_ROUTE_ACTIONS
        return module._CORE_AGENT(obs)
    return agent


def market_scale(module, scale):
    def agent(obs):
        action = copy_action(module.agent(obs))
        for order in action["market"]:
            if len(order) >= 3 and order[0] == "SELL":
                order[2] = max(0, int(round(int(order[2] or 0) * scale)))
        return action
    return agent


def market_delay(module, start_step=360):
    def agent(obs):
        action = copy_action(module.agent(obs))
        if int(obs.get("step", 0) or 0) < start_step:
            action["market"] = [order for order in action["market"] if not (len(order) >= 1 and order[0] == "SELL")]
        return action
    return agent


def market_priority(module, preferred="WHEAT"):
    def agent(obs):
        action = copy_action(module.agent(obs))
        sells = [order for order in action["market"] if len(order) >= 2 and order[0] == "SELL"]
        others = [order for order in action["market"] if not (len(order) >= 2 and order[0] == "SELL")]
        sells.sort(key=lambda order: 0 if order[1] == preferred else 1)
        action["market"] = sells + others
        return action
    return agent


def exploit_wheat(module):
    def agent(obs):
        action = copy_action(module.agent(obs))
        action["market"] = [order for order in action["market"] if not (len(order) >= 2 and order[0] == "BUY_PRODUCT" and order[1] == "WHEAT")]
        return action
    return agent


def exploit_cleanup(module):
    def agent(obs):
        action = copy_action(module.agent(obs))
        step = int(obs.get("step", 0) or 0)
        if step >= 672:
            action["market"] = [order for order in action["market"] if len(order) >= 2 and order[0] == "SELL"]
        return action
    return agent


def exploit_item(module, item):
    """Remove one product buy order to create a supply-side variant."""
    def agent(obs):
        action = copy_action(module.agent(obs))
        action["market"] = [order for order in action["market"] if not (len(order) >= 2 and order[0] == "BUY_PRODUCT" and order[1] == item)]
        return action
    return agent


def cleanup_after(module, start_step):
    """Keep only sales after a configurable late-season step."""
    def agent(obs):
        action = copy_action(module.agent(obs))
        if int(obs.get("step", 0) or 0) >= int(start_step):
            action["market"] = [order for order in action["market"] if len(order) >= 2 and order[0] == "SELL"]
        return action
    return agent


def market_buy(module):
    """Buy-oriented market expert: preserves purchases and delays sales."""
    def agent(obs):
        action = copy_action(module.agent(obs))
        step = int(obs.get("step", 0) or 0)
        if step < 480:
            action["market"] = [order for order in action["market"] if not (len(order) >= 1 and order[0] == "SELL")]
        return action
    return agent
