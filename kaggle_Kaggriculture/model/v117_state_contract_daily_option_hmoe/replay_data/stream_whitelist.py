"""流式读取 Replay 白名单字段，禁止物化历史动作和市场轨迹。"""

from __future__ import annotations

import io
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TextIO


class ReplayFormatError(ValueError):
    """Replay 结构不完整或不符合白名单时抛出。"""


class JsonStream:
    def __init__(self, stream: TextIO, chunk_size: int = 64 * 1024):
        self.stream = stream
        self.chunk_size = chunk_size
        self.buffer = ""
        self.pos = 0
        self.eof = False

    def _fill(self) -> None:
        if self.pos > self.chunk_size:
            self.buffer = self.buffer[self.pos :]
            self.pos = 0
        if self.pos >= len(self.buffer) and not self.eof:
            chunk = self.stream.read(self.chunk_size)
            if chunk:
                self.buffer += chunk
            else:
                self.eof = True

    def peek(self) -> str:
        self._fill()
        if self.pos >= len(self.buffer):
            raise ReplayFormatError("JSON 意外结束")
        return self.buffer[self.pos]

    def get(self) -> str:
        char = self.peek()
        self.pos += 1
        return char

    def skip_ws(self) -> None:
        while True:
            self._fill()
            if self.pos >= len(self.buffer) or not self.buffer[self.pos].isspace():
                return
            self.pos += 1

    def expect(self, expected: str) -> None:
        self.skip_ws()
        actual = self.get()
        if actual != expected:
            raise ReplayFormatError(f"期望 {expected!r}，实际 {actual!r}")

    def read_string(self) -> str:
        self.skip_ws()
        if self.get() != '"':
            raise ReplayFormatError("期望 JSON 字符串")
        raw = ['"']
        while True:
            char = self.get()
            raw.append(char)
            if char == '"':
                break
            if char == "\\":
                escaped = self.get()
                raw.append(escaped)
                if escaped == "u":
                    raw.extend(self.get() for _ in range(4))
            elif ord(char) < 0x20:
                raise ReplayFormatError("字符串含未转义控制字符")
        try:
            return json.loads("".join(raw))
        except json.JSONDecodeError as exc:
            raise ReplayFormatError("非法 JSON 字符串") from exc

    def skip_string(self) -> None:
        self.skip_ws()
        if self.get() != '"':
            raise ReplayFormatError("期望 JSON 字符串")
        while True:
            char = self.get()
            if char == '"':
                return
            if char == "\\":
                escaped = self.get()
                if escaped == "u":
                    for _ in range(4):
                        self.get()
            elif ord(char) < 0x20:
                raise ReplayFormatError("字符串含未转义控制字符")

    def read_atom(self) -> Any:
        self.skip_ws()
        chars: list[str] = []
        while True:
            self._fill()
            if self.pos >= len(self.buffer):
                break
            char = self.buffer[self.pos]
            if char.isspace() or char in ",]}:":
                break
            chars.append(char)
            self.pos += 1
        try:
            return json.loads("".join(chars))
        except json.JSONDecodeError as exc:
            raise ReplayFormatError("非法 JSON 原子") from exc

    def read_value(self) -> Any:
        self.skip_ws()
        char = self.peek()
        if char == '"':
            return self.read_string()
        if char == "{":
            return self.read_object()
        if char == "[":
            return self.read_array()
        return self.read_atom()

    def read_object(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        self.expect("{")
        self.skip_ws()
        if self.peek() == "}":
            self.get()
            return result
        while True:
            key = self.read_string()
            self.expect(":")
            result[key] = self.read_value()
            self.skip_ws()
            delimiter = self.get()
            if delimiter == "}":
                return result
            if delimiter != ",":
                raise ReplayFormatError("对象分隔符错误")

    def read_array(self) -> list[Any]:
        result: list[Any] = []
        self.expect("[")
        self.skip_ws()
        if self.peek() == "]":
            self.get()
            return result
        while True:
            result.append(self.read_value())
            self.skip_ws()
            delimiter = self.get()
            if delimiter == "]":
                return result
            if delimiter != ",":
                raise ReplayFormatError("数组分隔符错误")

    def skip_value(self) -> None:
        """消费非白名单值，但不构造它的字符串、数组或对象。"""
        self.skip_ws()
        char = self.peek()
        if char == '"':
            self.skip_string()
            return
        if char == "{":
            self.expect("{")
            self.skip_ws()
            if self.peek() == "}":
                self.get()
                return
            while True:
                self.skip_string()
                self.expect(":")
                self.skip_value()
                self.skip_ws()
                delimiter = self.get()
                if delimiter == "}":
                    return
                if delimiter != ",":
                    raise ReplayFormatError("跳过对象时分隔符错误")
        if char == "[":
            self.expect("[")
            self.skip_ws()
            if self.peek() == "]":
                self.get()
                return
            while True:
                self.skip_value()
                self.skip_ws()
                delimiter = self.get()
                if delimiter == "]":
                    return
                if delimiter != ",":
                    raise ReplayFormatError("跳过数组时分隔符错误")
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
        delimiter = js.get()
        if delimiter == "}":
            return episode_id, seed
        if delimiter != ",":
            raise ReplayFormatError("info 对象结构错误")


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
            if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
                raise ReplayFormatError("town.unlocked_shops 必须是字符串数组")
            shops = tuple(value)
        else:
            js.skip_value()
        js.skip_ws()
        delimiter = js.get()
        if delimiter == "}":
            return shops
        if delimiter != ",":
            raise ReplayFormatError("town 对象结构错误")


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
        delimiter = js.get()
        if delimiter == "}":
            return shops
        if delimiter != ",":
            raise ReplayFormatError("observation 对象结构错误")


def _read_first_seat(js: JsonStream) -> tuple[str, ...] | None:
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
        delimiter = js.get()
        if delimiter == "}":
            return shops
        if delimiter != ",":
            raise ReplayFormatError("seat 对象结构错误")


def _read_step(js: JsonStream) -> tuple[str, ...]:
    js.expect("[")
    js.skip_ws()
    if js.peek() == "]":
        raise ReplayFormatError("Replay step 为空")
    shops = _read_first_seat(js)
    js.skip_ws()
    while js.peek() == ",":
        js.get()
        js.skip_value()
        js.skip_ws()
    js.expect("]")
    if shops is None:
        raise ReplayFormatError("seat 0 缺少 town.unlocked_shops")
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
        delimiter = js.get()
        if delimiter == "]":
            return tuple(steps)
        if delimiter != ",":
            raise ReplayFormatError("steps 数组结构错误")


def read_replay_whitelist(path: str | Path, *, include_steps: bool) -> ReplayWhitelist:
    """只返回白名单字段；元数据模式在 top-level steps 值之前停止。"""
    replay_path = Path(path)
    raw = replay_path.open("rb")
    text = io.TextIOWrapper(raw, encoding="utf-8", newline="")
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
            raise ReplayFormatError("Replay 为空")
        while True:
            key = js.read_string()
            js.expect(":")
            if key == "configuration":
                value = js.read_value()
                if not isinstance(value, dict):
                    raise ReplayFormatError("configuration 必须是对象")
                configuration = value
            elif key == "info":
                episode_id, seed = _read_info(js)
            elif key == "module_version":
                value = js.read_value()
                if not isinstance(value, str):
                    raise ReplayFormatError("module_version 必须是字符串")
                module_version = value
            elif key == "steps":
                if not include_steps:
                    stopped_before_steps = True
                    break
                shops_by_step = _read_steps(js)
            else:
                js.skip_value()

            js.skip_ws()
            delimiter = js.get()
            if delimiter == "}":
                break
            if delimiter != ",":
                raise ReplayFormatError("Replay 根对象结构错误")

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
            raise ReplayFormatError("缺少白名单元数据：" + ", ".join(missing))
        if include_steps and shops_by_step is None:
            raise ReplayFormatError("缺少 steps")
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
