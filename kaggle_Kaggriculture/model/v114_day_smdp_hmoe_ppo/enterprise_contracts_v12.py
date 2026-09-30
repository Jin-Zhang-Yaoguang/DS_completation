"""Shared enterprise contracts between V12 unit and event-market experts."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EnterpriseContract:
    name: str
    crop: str
    animal: str | None = None

    @property
    def logistics_items(self) -> frozenset[str]:
        values = {self.crop, "FERTILIZER"}
        if self.animal:
            values.add(self.animal)
            values.add({"GOOSE": "EGG", "COW": "MILK", "SHEEP": "WOOL"}[self.animal])
        return frozenset(values)

    def allows_task(self, operation: str, item: str) -> bool:
        if operation == "PLANT":
            return item in {self.crop, "WHEAT"} if self.animal else item == self.crop
        if operation in {"BUILD_COOP"}:
            return self.animal == "GOOSE"
        if operation in {"BUILD_PASTURE"}:
            return self.animal in {"COW", "SHEEP"}
        if operation in {"FEED", "CARE", "COLLECT_FERTILIZER"}:
            return self.animal is not None
        if operation in {"PICKUP", "PLACE"}:
            return item in self.logistics_items
        return True

    def allows_transaction(self, head: str) -> bool:
        if head.startswith("SELL:"):
            return True
        common = {
            "HIRE", "BUY_LAND", f"BUY_SEED:{self.crop}",
            "BUY_PRODUCT:FERTILIZER",
        }
        if self.animal:
            common.update({
                "BUY_SEED:WHEAT", "BUY_PRODUCT:WHEAT",
                f"BUY_ANIMAL:{self.animal}",
            })
        return head in common


CONTRACTS = {
    "WHEAT_CASH": EnterpriseContract("WHEAT_CASH", "WHEAT"),
    "MELON_CASH": EnterpriseContract("MELON_CASH", "MELON"),
    "COW_DAIRY": EnterpriseContract("COW_DAIRY", "WHEAT", "COW"),
}


def resolve_contract(name: str | None) -> EnterpriseContract | None:
    if name in (None, "", "NONE"):
        return None
    if name not in CONTRACTS:
        raise ValueError(f"unknown V12 enterprise contract: {name}")
    return CONTRACTS[name]
