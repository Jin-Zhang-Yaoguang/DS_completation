"""ARC-AGI-2 规则搜索 v1。只用每题示例拟合，不读取验证/测试答案。"""

from collections import Counter, deque
from dataclasses import dataclass


def grid(value):
    rows = tuple(tuple(int(cell) for cell in row) for row in value)
    if not rows or not rows[0] or any(len(row) != len(rows[0]) for row in rows):
        raise ValueError("非法网格尺寸")
    return rows


def valid(value):
    try:
        rows = grid(value)
    except (TypeError, ValueError):
        return False
    return len(rows) <= 30 and len(rows[0]) <= 30 and all(0 <= c <= 9 for row in rows for c in row)


def transform(a, mode):
    if mode >= 4:
        a = tuple(zip(*a))
        mode -= 4
    if mode & 1:
        a = tuple(row[::-1] for row in a)
    if mode & 2:
        a = a[::-1]
    return tuple(tuple(row) for row in a)


def background(a):
    border = list(a[0]) + list(a[-1]) + [r[0] for r in a] + [r[-1] for r in a]
    return Counter(border).most_common(1)[0][0]


def crop(a, color=None, invert=False):
    if color is None:
        color = background(a)
        cells = [(y, x) for y, row in enumerate(a) for x, c in enumerate(row) if c != color]
    else:
        cells = [(y, x) for y, row in enumerate(a) for x, c in enumerate(row) if (c != color if invert else c == color)]
    if not cells:
        return a
    ys, xs = zip(*cells)
    return tuple(tuple(row[min(xs): max(xs) + 1]) for row in a[min(ys): max(ys) + 1])


def component(a, which, connectivity):
    bg = background(a)
    seen, groups = set(), []
    h, w = len(a), len(a[0])
    steps = ((1, 0), (-1, 0), (0, 1), (0, -1))
    if connectivity == 8:
        steps += ((1, 1), (1, -1), (-1, 1), (-1, -1))
    for y in range(h):
        for x in range(w):
            if (y, x) in seen or a[y][x] == bg:
                continue
            q, group = deque([(y, x)]), []
            seen.add((y, x))
            while q:
                cy, cx = q.popleft()
                group.append((cy, cx))
                for dy, dx in steps:
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < h and 0 <= nx < w and (ny, nx) not in seen and a[ny][nx] == a[y][x]:
                        seen.add((ny, nx))
                        q.append((ny, nx))
            groups.append(group)
    if not groups:
        return a
    key = lambda g: (len(g), -min(y for y, _ in g), -min(x for _, x in g))
    selected = max(groups, key=key) if which == "largest" else min(groups, key=key)
    ys, xs = zip(*selected)
    y0, y1, x0, x1 = min(ys), max(ys), min(xs), max(xs)
    mask = set(selected)
    return tuple(tuple(a[y][x] if (y, x) in mask else bg for x in range(x0, x1 + 1)) for y in range(y0, y1 + 1))


@dataclass(frozen=True)
class Operation:
    kind: str
    arg: object = None
    geom: int = 0

    def apply(self, a):
        if self.kind == "identity":
            b = a
        elif self.kind == "crop":
            b = crop(a, self.arg)
        elif self.kind == "component":
            b = component(a, *self.arg)
        elif self.kind == "scale":
            sy, sx = self.arg
            b = tuple(tuple(c for c in row for _ in range(sx)) for row in a for _ in range(sy))
        elif self.kind == "tile":
            ty, tx = self.arg
            b = tuple(tuple(row * tx) for _ in range(ty) for row in a)
        elif self.kind == "row":
            b = (a[self.arg if self.arg >= 0 else -1],)
        elif self.kind == "column":
            x = self.arg if self.arg >= 0 else len(a[0]) - 1
            b = tuple((row[x],) for row in a)
        elif self.kind == "constant":
            b = self.arg
        else:
            raise ValueError(self.kind)
        return transform(b, self.geom)

    def cost(self):
        return {"identity": 0, "crop": 2, "component": 4, "scale": 3, "tile": 4,
                "row": 4, "column": 4, "constant": 7}[self.kind] + int(self.geom != 0)


def operations(train):
    colors = sorted({c for p in train for g in (p["input"], p["output"]) for row in g for c in row})
    for geom in range(8):
        yield Operation("identity", geom=geom)
    for color in [None] + colors:
        for geom in range(8):
            yield Operation("crop", color, geom)
    for which in ("largest", "smallest"):
        for connectivity in (4, 8):
            for geom in range(8):
                yield Operation("component", (which, connectivity), geom)
    for kind in ("scale", "tile"):
        for sy in range(1, 5):
            for sx in range(1, 5):
                if (sy, sx) != (1, 1):
                    yield Operation(kind, (sy, sx))
    for kind in ("row", "column"):
        for index in (0, -1):
            yield Operation(kind, index)
    outputs = [grid(p["output"]) for p in train]
    if outputs and all(out == outputs[0] for out in outputs):
        yield Operation("constant", outputs[0])


def fit_color_map(predicted, expected):
    mapping = {}
    for base, target in zip(predicted, expected):
        if len(base) != len(target) or len(base[0]) != len(target[0]):
            return None
        for brow, trow in zip(base, target):
            for before, after in zip(brow, trow):
                if before in mapping and mapping[before] != after:
                    return None
                mapping[before] = after
    return mapping


def apply_map(a, mapping):
    return tuple(tuple(mapping.get(c, c) for c in row) for row in a)


def solve(task):
    train = task["train"]
    pairs = [(grid(p["input"]), grid(p["output"])) for p in train]
    test = [grid(p["input"]) for p in task["test"]]
    candidates = []
    for op in operations(train):
        try:
            bases = [op.apply(a) for a, _ in pairs]
            mapping = fit_color_map(bases, [b for _, b in pairs])
            if mapping is None:
                continue
            predictions = tuple(apply_map(op.apply(a), mapping) for a in test)
            if not all(valid(p) for p in predictions):
                continue
            changes = sum(k != v for k, v in mapping.items())
            score = op.cost() + changes + (1 if len(mapping) > 4 else 0)
            candidates.append((score, repr(op), predictions))
        except (IndexError, ValueError):
            continue
    candidates.sort(key=lambda x: (x[0], x[1]))
    unique = []
    for _, _, predictions in candidates:
        if predictions not in unique:
            unique.append(predictions)
        if len(unique) == 2:
            break
    if not unique:
        unique.append(tuple(test))
    if len(unique) == 1:
        fallback = tuple(crop(a) for a in test)
        unique.append(fallback if fallback != unique[0] and all(valid(p) for p in fallback) else tuple(test))
    return [{"attempt_1": [list(r) for r in unique[0][i]],
             "attempt_2": [list(r) for r in unique[1][i]]} for i in range(len(test))]


def predict(challenges):
    return {task_id: solve(task) for task_id, task in challenges.items()}
