from __future__ import annotations

from typing import Any, Callable, Optional
import asyncio
import collections
import datetime as dt
import inspect

from prompt_toolkit.input import create_input
from prompt_toolkit.key_binding import KeyPress  # noqa: TCH002
from prompt_toolkit.keys import Keys
import pydantic


class KeyPressContext(pydantic.BaseModel, arbitrary_types_allowed=True):
    """Metadata about when a KeyPress happened."""

    key_press: KeyPress
    when: pydantic.AwareDatetime = pydantic.Field(default_factory=dt.datetime.utcnow)

    def __str__(self) -> str:
        return f"<KeyPressContext key={self.key_press.key}, when='{self.when:%H:%M:%S.%f}'>"


class KeyboardListener:
    """Listen for keys from the keyboard."""

    def __init__(self):
        self._background_done: Optional[asyncio.Event] = None
        self._background_task: Optional[asyncio.Task] = None
        self._key_hooks: dict[str, list[Callable[[KeyPressContext], Any]]] = collections.defaultdict(list)

    async def _background_listener(self) -> None:
        """Engage prompt_toolkit to listen for keys cross-platform."""
        self._input = tk_input = create_input()

        with tk_input.raw_mode():
            with tk_input.attach(self._trigger_callbacks):
                assert self._background_done is not None, "KeyboardListener has not yet been started"
                await self._background_done.wait()

    def _trigger_callbacks(self) -> None:
        """Trigger hooked callbacks on key press."""
        active_tasks: set[asyncio.Task] = set()

        for key_press in self._input.read_keys():
            hooks = [
                *self._key_hooks.get(key_press.key, []),
                *self._key_hooks.get(Keys.Any, []),
            ]

            if hooks is None:
                continue

            ctx = KeyPressContext(key_press=key_press)

            for hook in hooks:
                task = asyncio.create_task(self._invoke(hook, ctx))
                task.add_done_callback(lambda t: active_tasks.discard(t))
                active_tasks.add(task)

    async def _invoke(self, hook: Callable[[KeyPressContext], Any], *params) -> Any:
        """Invoke a keybound callback."""
        parameter_count = len(inspect.signature(hook).parameters)
        result = hook(*params[:parameter_count])

        if inspect.isawaitable(result):
            result = await result

        return result

    def add_binding(self, key: Keys, callback: Callable) -> None:
        """Add a callback to a key press."""
        self._key_hooks[key].append(callback)

    def run(self) -> None:
        """Synchronous interface to starting a keyboard listener."""
        asyncio.run(self.start(wait=True))

    async def start(self, *, wait: bool = False, ignore_control_c: bool = False) -> None:
        """Start the KeyboardListener."""
        if not ignore_control_c:
            self.add_binding(Keys.ControlC, callback=self.stop)

        self._background_done = asyncio.Event()
        self._background_task = asyncio.create_task(self._background_listener())

        if wait:
            await self._background_done.wait()

    async def stop(self) -> None:
        """Stop the KeyboardListener."""
        assert self._background_done is not None, "KeyboardListener has not yet been started"
        self._background_done.set()


if __name__ == "__main__":
    import logging

    from rich.logging import RichHandler

    logging.basicConfig(format="%(message)s", datefmt="[%X]", level=logging.INFO, handlers=[RichHandler()])
    log = logging.getLogger(__name__)

    kb = KeyboardListener()
    kb.add_binding(key=Keys.Any, callback=lambda ctx: log.info(ctx))
    kb.run()
