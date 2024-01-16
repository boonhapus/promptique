from __future__ import annotations

from typing import Any, Callable, Optional, Union
import asyncio
import collections
import datetime as dt
import logging

from prompt_toolkit.input import Input, create_input
from prompt_toolkit.key_binding import KeyPress
import pydantic

from promptique import _utils
from promptique.keys import Keys

log = logging.getLogger(__name__)


class KeyPressContext(pydantic.BaseModel, arbitrary_types_allowed=True):
    """Metadata about a KeyPress."""

    key_press: KeyPress
    keyboard: KeyboardListener
    when: pydantic.AwareDatetime = pydantic.Field(default_factory=dt.datetime.utcnow)

    def __str__(self) -> str:
        return f"<KeyPressContext key={self.key_press.key}, when='{self.when:%H:%M:%S.%f}'>"


class KeyboardListener:
    """Listen for keys from the keyboard."""

    def __init__(self):
        self._background_done: Optional[asyncio.Event] = None
        self._input_pipe: Optional[Input] = None
        self._key_hooks: dict[str, list[Callable[[KeyPressContext], Any]]] = collections.defaultdict(list)
        self._active_hooks: set[asyncio.Task] = set()
        self._is_accepting_keys: bool = False

    def _trigger_hooks(self, key_press: KeyPress) -> None:
        """Trigger hooked callbacks on key press."""
        if not self._is_accepting_keys:
            log.warning(f"{key_press} ignored, listener has been shut")
            return

        hooks = [
            *self._key_hooks.get(key_press.key, []),
            *self._key_hooks.get(Keys.Any, []),
        ]

        if hooks is None:
            return

        ctx = KeyPressContext(key_press=key_press, keyboard=self)

        for hook in hooks:
            task = asyncio.create_task(_utils.invoke(hook, ctx))
            task.add_done_callback(lambda t: self._active_hooks.discard(t))
            self._active_hooks.add(task)

    def bind(self, key: Keys, fn: Callable) -> None:
        """Add a callback to a key press."""
        self._key_hooks[key].append(fn)

    def simulate(self, key: Union[Keys, str]) -> None:
        """Pretend to press a key."""
        self._trigger_hooks(key_press=KeyPress(key=key))

    def run(self) -> None:
        """Synchronous interface to starting a keyboard listener."""
        asyncio.run(self.start())

    async def start(self, *, ignore_control_c: bool = False) -> None:
        """Start the KeyboardListener."""
        self._is_accepting_keys = True

        if not ignore_control_c:
            self.bind(Keys.ControlC, fn=self.stop)

        self._input_pipe = create_input()
        self._background_done = asyncio.Event()

        def _feed_keys() -> None:
            """Engage prompt_toolkit to listen for keys cross-platform."""
            assert self._input_pipe is not None, "KeyboardListener has not yet been started"
            for key_press in self._input_pipe.read_keys():
                # key_press = KeyPress.from_ptk_keypress(key_press)
                self._trigger_hooks(key_press)

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
    kb.bind(key=Keys.Any, fn=lambda ctx: log.info(ctx))
    kb.run()
