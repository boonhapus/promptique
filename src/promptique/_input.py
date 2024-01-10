from __future__ import annotations

from typing import Callable, TypedDict
import asyncio
import collections
import datetime as dt
import inspect

from prompt_toolkit.input import create_input
from prompt_toolkit.key_binding import KeyPress
from prompt_toolkit.keys import Keys
import pydantic


class HookSignature(TypedDict):
    key: Keys

Hook = Callable[HookSignature, None]


class KeyContext(pydantic.BaseModel, arbitrary_types_allowed=True):
    key: KeyPress
    when: dt.datetime = pydantic.Field(default_factory=dt.datetime.now)

    def __str__(self) -> str:
        return f"<KeyContext key={self.key.key}, when='{self.when:%H:%M:%S.%f}'>"


class KeyboardListener:
    """Listen for keys from the keyboard."""

    def __init__(self):
        self._background_done: asyncio.Event = None
        self._background_task: asyncio.Task = None
        self._key_hooks: dict[Keys, list[Hook]] = collections.defaultdict(list)

    async def _background_listener(self) -> None:
        self._input = tk_input = create_input()

        with tk_input.raw_mode():
            with tk_input.attach(self._fire_callbacks):
                await self._background_done.wait()

    async def invoke(self, hook, *params):
        parameter_count = len(inspect.signature(hook).parameters)
        result = hook(*params[:parameter_count])

        if inspect.isawaitable(result):
            result = await result

        return result

    def _fire_callbacks(self) -> None:
        active: set[asyncio.Task] = set()

        for key_press in self._input.read_keys():
            hooks = [
                *self._key_hooks.get(key_press.key, []),
                *self._key_hooks.get(Keys.Any, []),
            ]

            if hooks is None:
                continue

            ctx = KeyContext(key=key_press)

            for hook in hooks:
                task = asyncio.create_task(self.invoke(hook, ctx))
                task.add_done_callback(lambda t: active.remove(t))
                active.add(task)

    def add_binding(self, key: Keys, callback) -> None:
        """Add a callback to a key press."""
        self._key_hooks[key].append(callback)

    def run(self) -> None:
        """Synchronous interface to starting a keyboard listener."""
        asyncio.run(self.start(wait=True))

    async def start(self, wait: bool = False) -> None:
        """Start the KeyboardListener."""
        self._background_done = asyncio.Event()
        self._background_task = asyncio.create_task(self._background_listener())

        if wait:
            await self._background_done.wait()

    async def stop(self) -> None:
        """Stop the KeyboardListener."""
        self._background_done.set()


if __name__ == "__main__":
    kb = KeyboardListener()
    kb.add_binding(key=Keys.Any, callback=lambda ctx: print(ctx))
    kb.add_binding(key=Keys.Escape, callback=kb.stop)
    kb.run()
