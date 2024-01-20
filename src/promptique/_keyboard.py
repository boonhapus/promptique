from __future__ import annotations

from typing import Any, Callable, Optional
import asyncio
import collections
import datetime as dt
import functools as ft
import logging

from prompt_toolkit.input import Input, create_input
from prompt_toolkit.keys import Keys
import pydantic

from promptique import _utils, keys

log = logging.getLogger(__name__)


class KeyPressContext(pydantic.BaseModel, arbitrary_types_allowed=True):
    """Metadata about a KeyPress."""

    key: keys.Key
    keyboard: KeyboardListener
    when: pydantic.AwareDatetime = pydantic.Field(default_factory=dt.datetime.utcnow)

    def __str__(self) -> str:
        return f"<KeyPressContext key={self.key.name}, when='{self.when:%H:%M:%S.%f}'>"


class KeyboardListener:
    """Listen for keys from the keyboard."""

    def __init__(self):
        self._background_done: Optional[asyncio.Event] = None
        self._input_pipe: Optional[Input] = None
        self._key_hooks: dict[keys.Key, list[Callable[[KeyPressContext], Any]]] = collections.defaultdict(list)
        self._active_hooks: set[asyncio.Task] = set()
        self._is_accepting_keys: bool = False

    def _trigger_hooks(self, key: keys.Key) -> None:
        """Trigger hooked callbacks on key press."""
        if not self._is_accepting_keys:
            log.warning(f"{key} ignored, listener has been shut")
            return

        hooks = [
            *self._key_hooks.get(key, []),
            *self._key_hooks.get(keys.Any, []),
        ]

        if hooks is None:
            return

        ctx = KeyPressContext(key=key, keyboard=self)

        for hook in hooks:
            task = asyncio.create_task(_utils.invoke(hook, ctx))
            task.add_done_callback(lambda t: self._active_hooks.discard(t))
            self._active_hooks.add(task)

    def bind(self, key: keys.Key, fn: Callable, **kw) -> None:
        """Add a callback to a key press."""
        if kw:
            fn = ft.partial(fn, **kw)
        self._key_hooks[key].append(fn)

    def simulate(self, key: keys.Key) -> None:
        """Pretend to press a key."""
        self._trigger_hooks(key=key)

    def run(self) -> None:
        """Synchronous interface to starting a keyboard listener."""
        asyncio.run(self.start())

    async def start(self, *, ignore_control_c: bool = False) -> None:
        """Start the KeyboardListener."""
        self._is_accepting_keys = True

        if not ignore_control_c:
            self.bind(keys.ControlC, fn=self.stop)

        self._input_pipe = create_input()
        self._background_done = asyncio.Event()

        def _feed_keys() -> None:
            """Engage prompt_toolkit to listen for keys cross-platform."""
            assert self._input_pipe is not None, "KeyboardListener has not yet been started"
            for key_press in self._input_pipe.read_keys():
                if isinstance(key_press.key, Keys) and key_press.key.name == "BracketedPaste":
                    key = keys.Key.model_construct(name=key_press.key.name, data=key_press.data, is_printable=True)
                elif isinstance(key_press.key, Keys):
                    key = keys.Key(name=key_press.key.name, data=key_press.data)
                else:
                    key = keys.Key(name=key_press.key, data=key_press.data, is_printable=True)

                self._trigger_hooks(key)

        with self._input_pipe.raw_mode():
            with self._input_pipe.attach(_feed_keys):
                await self._background_done.wait()

    async def stop(self, *, no_wait: bool = False) -> None:
        """Stop the KeyboardListener."""
        assert self._background_done is not None, "KeyboardListener has not yet been started"
        self._is_accepting_keys = False

        if currently_active_hooks := [hook for hook in self._active_hooks if hook != asyncio.current_task()]:
            if no_wait:
                [hook.cancel() for hook in currently_active_hooks]

                # allow .cancel() to propogate
                await asyncio.sleep(0)
            else:
                await asyncio.wait(currently_active_hooks, timeout=1)

        self._background_done.set()


if __name__ == "__main__":
    import logging

    from rich.logging import RichHandler

    logging.basicConfig(format="%(message)s", datefmt="[%X]", level=logging.INFO, handlers=[RichHandler()])
    log = logging.getLogger(__name__)

    kb = KeyboardListener()
    kb.bind(key=keys.Any, fn=lambda ctx: log.info(ctx))
    kb.bind(key=keys.Paste, fn=lambda ctx: log.info(ctx.key.data))
    kb.run()
