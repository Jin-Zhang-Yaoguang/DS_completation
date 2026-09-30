#!/usr/bin/env python3
"""Fit a conservative depth-2 early-switch leaf without reading test labels."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


HERE = Path(__file__).resolve().parent
FIT = (87000, 87128)
VALIDATION = (87128, 87192)
TEST = (87192, 87256)


@dataclass(frozen=True)
class Predicate:
    feature: str
    operator: str
    value: object
    mask: int

    def record(self) -> dict:
        return {"feature": self.feature, "operator": self.operator, "value": self.value}


def range_mask(rows: list[dict], bounds: tuple[int, int]) -> int:
    value = 0
    for index, row in enumerate(rows):
        if bounds[0] <= int(row["seed"]) < bounds[1]:
            value |= 1 << index
    return value


def label_mask(rows: list[dict], sign: int) -> int:
    value = 0
    for index, row in enumerate(rows):
        delta = float(row["score_delta"])
        if (sign > 0 and delta > 0) or (sign < 0 and delta < 0) or (sign == 0 and delta == 0):
            value |= 1 << index
    return value


def predicate_mask(rows: list[dict], feature: str, operator: str, target: object) -> int:
    value = 0
    for index, row in enumerate(rows):
        observed = row["features"].get(feature, 0)
        matched = observed == target if operator == "==" else float(observed) <= float(target) if operator == "<=" else float(observed) > float(target)
        if matched:
            value |= 1 << index
    return value


def quantiles(values: list[float]) -> list[float]:
    ordered = sorted(values)
    result = []
    for numerator in range(1, 10):
        index = int(round((len(ordered) - 1) * numerator / 10))
        result.append(ordered[index])
    return sorted(set(result))


def metrics(mask: int, split: int, positive: int, negative: int, rows: list[dict]) -> dict:
    selected = mask & split
    indexes = [index for index in range(len(rows)) if selected & (1 << index)]
    return {
        "cells": len(indexes),
        "positive_zero_negative": [
            (selected & positive).bit_count(),
            len(indexes) - (selected & positive).bit_count() - (selected & negative).bit_count(),
            (selected & negative).bit_count(),
        ],
        "score_uplift_pp": 100 * sum(float(rows[index]["score_delta"]) for index in indexes) / max(1, len(indexes)),
        "margin_delta_mean": sum(float(rows[index]["margin_delta"]) for index in indexes) / max(1, len(indexes)),
        "own_delta_mean": sum(float(rows[index]["own_delta"]) for index in indexes) / max(1, len(indexes)),
        "positive_families": sorted({rows[index]["opponent_family"] for index in indexes if float(rows[index]["score_delta"]) > 0}),
        "negative_families": sorted({rows[index]["opponent_family"] for index in indexes if float(rows[index]["score_delta"]) < 0}),
        "positive_seats": sorted({int(rows[index]["seat"]) for index in indexes if float(rows[index]["score_delta"]) > 0}),
        "seed_count": len({int(rows[index]["seed"]) for index in indexes}),
    }


def main() -> int:
    dataset = json.loads((HERE / "early_switch_dataset.json").read_text(encoding="utf-8"))
    rows = dataset["rows"]
    fit = range_mask(rows, FIT)
    validation = range_mask(rows, VALIDATION)
    test = range_mask(rows, TEST)
    positive = label_mask(rows, 1)
    negative = label_mask(rows, -1)
    fit_rows = [row for row in rows if FIT[0] <= int(row["seed"]) < FIT[1]]
    feature_example = fit_rows[0]["features"]
    predicates = []
    for feature in ("shop_1", "shop_2", "shop_pair"):
        for target in sorted({row["features"][feature] for row in fit_rows}):
            predicates.append(Predicate(feature, "==", target, predicate_mask(rows, feature, "==", target)))
    for feature, sample in feature_example.items():
        if feature in {"seat", "shop_1", "shop_2", "shop_pair"} or not isinstance(sample, (int, float)):
            continue
        values = [float(row["features"].get(feature, 0) or 0) for row in fit_rows]
        for target in quantiles(values):
            predicates.append(Predicate(feature, "<=", target, predicate_mask(rows, feature, "<=", target)))
            predicates.append(Predicate(feature, ">", target, predicate_mask(rows, feature, ">", target)))
    # Remove duplicate masks and near-tautologies before pair enumeration.
    unique = {}
    for predicate in predicates:
        support = (predicate.mask & fit).bit_count()
        if 8 <= support <= len(fit_rows) - 8:
            unique.setdefault(predicate.mask, predicate)
    predicates = list(unique.values())

    family_positive_masks = {}
    seat_positive_masks = {}
    for family in sorted({row["opponent_family"] for row in rows}):
        mask = 0
        for index, row in enumerate(rows):
            if row["opponent_family"] == family and float(row["score_delta"]) > 0:
                mask |= 1 << index
        family_positive_masks[family] = mask
    for seat in (0, 1):
        mask = 0
        for index, row in enumerate(rows):
            if int(row["seat"]) == seat and float(row["score_delta"]) > 0:
                mask |= 1 << index
        seat_positive_masks[seat] = mask

    candidates = []
    all_predicates = [None, *predicates]
    for left_index, left in enumerate(all_predicates):
        start = 1 if left is None else left_index
        for right in predicates[start:]:
            mask = right.mask if left is None else left.mask & right.mask
            fit_selected = mask & fit
            fit_cells = fit_selected.bit_count()
            fit_positive = (fit_selected & positive).bit_count()
            fit_negative = (fit_selected & negative).bit_count()
            if fit_cells < 16 or fit_positive < 2 or fit_negative != 0:
                continue
            fit_positive_families = sum(bool(fit_selected & family_mask) for family_mask in family_positive_masks.values())
            fit_positive_seats = sum(bool(fit_selected & seat_mask) for seat_mask in seat_positive_masks.values())
            if fit_positive_families < 3 or fit_positive_seats < 2:
                continue
            validation_selected = mask & validation
            validation_positive = (validation_selected & positive).bit_count()
            validation_negative = (validation_selected & negative).bit_count()
            if validation_selected.bit_count() < 8 or validation_positive < 1 or validation_negative != 0:
                continue
            validation_margin = sum(
                float(row["margin_delta"])
                for index, row in enumerate(rows)
                if validation_selected & (1 << index)
            )
            candidates.append({
                "predicates": [predicate.record() for predicate in (left, right) if predicate is not None],
                "mask": mask,
                "selection_key": [validation_positive, fit_positive, validation_margin, -fit_cells],
            })
    candidates.sort(key=lambda row: tuple(row["selection_key"]), reverse=True)
    if not candidates:
        result = {
            "schema": "kaggriculture-v20-conservative-depth2-router-v1",
            "status": "NO_QUALIFIED_LEAF",
            "predicate_count": len(predicates),
            "fit_range": list(FIT), "validation_range": list(VALIDATION), "test_range": list(TEST),
        }
    else:
        selected = candidates[0]
        mask = int(selected.pop("mask"))
        result = {
            "schema": "kaggriculture-v20-conservative-depth2-router-v1",
            "status": "LEAF_SELECTED_BEFORE_TEST_READ",
            "predicate_count": len(predicates),
            "qualified_leaf_count": len(candidates),
            "fit_range": list(FIT), "validation_range": list(VALIDATION), "test_range": list(TEST),
            "selected_leaf": selected,
            "fit": metrics(mask, fit, positive, negative, rows),
            "validation": metrics(mask, validation, positive, negative, rows),
            "test": metrics(mask, test, positive, negative, rows),
            "router_policy": "switch at step144 iff every selected predicate is true; otherwise use safe step360",
        }
    (HERE / "early_router_tree.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
