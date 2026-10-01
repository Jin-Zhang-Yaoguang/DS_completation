"""Small streaming JSON reader with an explicit Kaggriculture field whitelist.

The reader never builds a replay step, action, farm, private state, reward, or
market object.  Values outside the whitelist are consumed structurally and
discarded without materialising their strings or containers.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO, TextIO


class ReplayFormatError(ValueError):
    """Raised when a replay is malformed or violates the whitelist contract."""


class JsonStream:
    def __init__(self, stream: TextIO, chunk_size: int = 64 * 1024):
        self.stream = stream
        self.chunk_size = chunk_size
        self.buffer = ""
        self.pos = 0
        self.eof = False

    def _compact(self) -> None:
        if self.pos > self.chunk_size:
            self.buffer = self.buffer[self.pos :]
            self.pos = 0

    def _fill(self) -> None:
        self._compact()
        if self.pos >= len(self.buffer) and not self.eof:
            chunk = self.stream.read(self.chunk_size)
            if chunk:
                self.buffer += chunk
            else:
                self.eof = True

    def peek(self) -> str:
        self._fill()
        if self.pos >= len(self.buffer):
            raise ReplayFormatError("unexpected end of JSON")
        return self.buffer[self.pos]

    def get(self) -> str:
        ch = self.peek()
        self.pos += 1
        return ch

    def skip_ws(self) -> None:
        while True:
            self._fill()
            if self.pos >= len(self.buffer):
                return
            if not self.buffer[self.pos].isspace():
                return
            self.pos += 1

    def expect(self, expected: str) -> None:
        self.skip_ws()
        actual = self.get()
        if actual != expected:
            raise ReplayFormatError(f"expected {expected!r}, got {actual!r}")

    def read_string(self) -> str:
        self.skip_ws()
        if self.get() != '"':
            raise ReplayFormatError("expected JSON string")
        raw = ['"']
        while True:
            ch = self.get()
            raw.append(ch)
            if ch == '"':
                break
            if ch == "\\":
                escaped = self.get()
                raw.append(escaped)
                if escaped == "u":
                    raw.extend(self.get() for _ in range(4))
            elif ord(ch) < 0x20:
                raise ReplayFormatError("unescaped control character in string")
        try:
            return json.loads("".join(raw))
        except json.JSONDecodeError as exc:
            raise ReplayFormatError("invalid JSON string") from exc

    def skip_string(self) -> None:
        self.skip_ws()
        if self.get() != '"':
            raise ReplayFormatError("expected JSON string")
        while True:
            ch = self.get()
            if ch == '"':
                return
            if ch == "\\":
                escaped = self.get()
                if escaped == "u":
                    for _ in range(4):
                        self.get()
            elif ord(ch) < 0x20:
                raise ReplayFormatError("unescaped control character in string")

    def read_atom(self) -> Any:
        self.skip_ws()
        chars: list[str] = []
        while True:
            self._fill()
            if self.pos >= len(self.buffer):
                break
            ch = self.buffer[self.pos]
            if ch.isspace() or ch in ",]}:":
                break
            chars.append(ch)
            self.pos += 1
        token = "".join(chars)
        try:
            return json.loads(token)
        except json.JSONDecodeError as exc:
            raise ReplayFormatError(f"invalid JSON atom {token!r}") from exc

    def read_value(self) -> Any:
        """Materialise a value only for an explicitly allowed field."""
        self.skip_ws()
        ch = self.peek()
        if ch == '"':
            return self.read_string()
        if ch == "{":
            return self.read_object()
        if ch == "[":
            return self.read_array()
        return self.read_atom()

    def read_object(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        self.expect("{")
        self.skip_ws()
        if self.peek() == "}":
            self.get()
            return out
        while True:
            key = self.read_string()
            self.expect(":")
            out[key] = self.read_value()
            self.skip_ws()
            ch = self.get()
            if ch == "}":
                return out
            if ch != ",":
                raise ReplayFormatError("expected ',' or '}'")

    def read_array(self) -> list[Any]:
        out: list[Any] = []
        self.expect("[")
        self.skip_ws()
        if self.peek() == "]":
            self.get()
            return out
        while True:
            out.append(self.read_value())
            self.skip_ws()
            ch = self.get()
            if ch == "]":
                return out
            if ch != ",":
                raise ReplayFormatError("expected ',' or ']'")

    def skip_value(self) -> None:
        """Consume a disallowed value without constructing it."""
        self.skip_ws()
        ch = self.peek()
        if ch == '"':
            self.skip_string()
            return
        if ch == "{":
            self.expect("{")
            self.skip_ws()
            if self.peek() == "}":
                self.get()
                return
            while True:
                self.skip_string()  # Disallowed key is not materialised.
                self.expect(":")
                self.skip_value()
                self.skip_ws()
                delim = self.get()
                if delim == "}":
                    return
                if delim != ",":
                    raise ReplayFormatError("expected ',' or '}' while skipping")
        if ch == "[":
            self.expect("[")
            self.skip_ws()
            if self.peek() == "]":
                self.get()
                return
            while True:
                self.skip_value()
                self.skip_ws()
                delim = self.get()
                if delim == "]":
                    return
                if delim != ",":
                    raise ReplayFormatError("expected ',' or ']' while skipping")
        self.read_atom()


@dataclass(frozen=True)
class ReplayWhitelist:
    configuration: dict[str, Any]
    episode_id: int
    seed: int
    module_version: str
    shops_by_step: tuple[tuple[str, ...], ...] | None
    stopped_before_steps: bool


def _read_info(js: JsonStream) -> tuple[int | None, int | None]:
    episode_id: int | None = None
    seed: int | None = None
    js.expect("{")
    js.skip_ws()
    if js.peek() == "}":
        js.get()
        return episode_id, seed
    while True:
        key = js.read_string()
        js.expect(":")
        if key == "EpisodeId":
            episode_id = int(js.read_value())
        elif key == "seed":
            seed = int(js.read_value())
        else:
            js.skip_value()
        js.skip_ws()
        delim = js.get()
        if delim == "}":
            return episode_id, seed
        if delim != ",":
            raise ReplayFormatError("malformed info object")


def _read_town(js: JsonStream) -> tuple[str, ...] | None:
    shops: tuple[str, ...] | None = None
    js.expect("{")
    js.skip_ws()
    if js.peek() == "}":
        js.get()
        return shops
    while True:
        key = js.read_string()
        js.expect(":")
        if key == "unlocked_shops":
            value = js.read_value()
            if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
                raise ReplayFormatError("town.unlocked_shops must be a string array")
            shops = tuple(value)
        else:
            js.skip_value()
        js.skip_ws()
        delim = js.get()
        if delim == "}":
            return shops
        if delim != ",":
            raise ReplayFormatError("malformed town object")


def _read_observation(js: JsonStream) -> tuple[str, ...] | None:
    shops: tuple[str, ...] | None = None
    js.expect("{")
    js.skip_ws()
    if js.peek() == "}":
        js.get()
        return shops
    while True:
        key = js.read_string()
        js.expect(":")
        if key == "town":
            shops = _read_town(js)
        else:
            js.skip_value()
        js.skip_ws()
        delim = js.get()
        if delim == "}":
            return shops
        if delim != ",":
            raise ReplayFormatError("malformed observation object")


def _read_first_state(js: JsonStream) -> tuple[str, ...] | None:
    shops: tuple[str, ...] | None = None
    js.expect("{")
    js.skip_ws()
    if js.peek() == "}":
        js.get()
        return shops
    while True:
        key = js.read_string()
        js.expect(":")
        if key == "observation":
            shops = _read_observation(js)
        else:
            js.skip_value()
        js.skip_ws()
        delim = js.get()
        if delim == "}":
            return shops
        if delim != ",":
            raise ReplayFormatError("malformed state object")


def _read_step(js: JsonStream) -> tuple[str, ...]:
    shops: tuple[str, ...] | None = None
    js.expect("[")
    js.skip_ws()
    if js.peek() == "]":
        raise ReplayFormatError("empty replay step")
    shops = _read_first_state(js)
    js.skip_ws()
    while js.peek() == ",":
        js.get()
        js.skip_value()  # All non-zero seats are intentionally ignored.
        js.skip_ws()
    js.expect("]")
    if shops is None:
        raise ReplayFormatError("seat 0 town.unlocked_shops missing")
    return shops


def _read_steps(js: JsonStream) -> tuple[tuple[str, ...], ...]:
    steps: list[tuple[str, ...]] = []
    js.expect("[")
    js.skip_ws()
    if js.peek() == "]":
        js.get()
        return tuple()
    while True:
        steps.append(_read_step(js))
        js.skip_ws()
        delim = js.get()
        if delim == "]":
            return tuple(steps)
        if delim != ",":
            raise ReplayFormatError("malformed steps array")


def _open_text(path: Path) -> tuple[BinaryIO, TextIO]:
    raw = path.open("rb")
    import io

    return raw, io.TextIOWrapper(raw, encoding="utf-8", newline="")


def read_replay_whitelist(path: str | Path, *, include_steps: bool) -> ReplayWhitelist:
    """Read only approved fields; with include_steps=False, stop before its value."""
    replay_path = Path(path)
    raw, text = _open_text(replay_path)
    try:
        js = JsonStream(text)
        configuration: dict[str, Any] | None = None
        episode_id: int | None = None
        seed: int | None = None
        module_version: str | None = None
        shops_by_step: tuple[tuple[str, ...], ...] | None = None
        stopped_before_steps = False

        js.expect("{")
        js.skip_ws()
        if js.peek() == "}":
            raise ReplayFormatError("empty replay")
        while True:
            key = js.read_string()
            js.expect(":")
            if key == "configuration":
                value = js.read_value()
                if not isinstance(value, dict):
                    raise ReplayFormatError("configuration must be an object")
                configuration = value
            elif key == "info":
                episode_id, seed = _read_info(js)
            elif key == "module_version":
                value = js.read_value()
                if not isinstance(value, str):
                    raise ReplayFormatError("module_version must be a string")
                module_version = value
            elif key == "steps":
                if not include_steps:
                    stopped_before_steps = True
                    break
                shops_by_step = _read_steps(js)
            else:
                js.skip_value()

            js.skip_ws()
            delim = js.get()
            if delim == "}":
                break
            if delim != ",":
                raise ReplayFormatError("malformed replay root")

        missing = [
            name
            for name, value in (
                ("configuration", configuration),
                ("info.EpisodeId", episode_id),
                ("info.seed", seed),
                ("module_version", module_version),
            )
            if value is None
        ]
        if missing:
            raise ReplayFormatError("missing approved metadata: " + ", ".join(missing))
        if include_steps and shops_by_step is None:
            raise ReplayFormatError("steps missing")
        return ReplayWhitelist(
            configuration=configuration or {},
            episode_id=int(episode_id),
            seed=int(seed),
            module_version=str(module_version),
            shops_by_step=shops_by_step,
            stopped_before_steps=stopped_before_steps,
        )
    finally:
        text.close()

