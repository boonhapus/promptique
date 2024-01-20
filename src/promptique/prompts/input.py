from __future__ import annotations

from typing import Callable, Optional

from rich.console import Console, ConsoleOptions, RenderResult
from rich.live import Live
from rich.style import Style
from rich.text import Text
import pydantic

from promptique import keys
from promptique._base import BasePrompt
from promptique._keyboard import KeyboardListener, KeyPressContext
from promptique.validation import ResponseContext, noop_always_valid


class UserInput(BasePrompt):
    """Ask the User to type a response"""

    prefill: Optional[str] = None
    is_secret: bool = False
    input_validator: Callable[[ResponseContext], bool] = pydantic.Field(default=noop_always_valid)
    """Validates the input, sets a warning if the selection is in an invalid state."""

    _buffer: list[str] = pydantic.PrivateAttr(default_factory=list)
    _response: str = pydantic.PrivateAttr(default_factory=list)

    def __init__(self, **data):
        super().__init__(**data)

        if self.prefill is not None:
            self.set_buffer(self.prefill)

    def buffer_as_string(self, *, on_screen: bool = False) -> str:
        """Render the buffer."""
        buffer = self._buffer

        if on_screen and self.is_secret:
            buffer = ["?" for character in self._buffer]

        return "".join(buffer)

    def set_buffer(self, user_input: str) -> None:
        """Directly set the underlying buffer."""
        self._buffer = list(user_input)

    def _interact_buffer_append(self, ctx: KeyPressContext) -> None:
        """Add to the buffer if the key is printable."""
        if ctx.key.is_printable:
            self._buffer.append(ctx.key.data)

    def _interact_validate(self, ctx: KeyPressContext, *, original_prompt: str) -> None:
        """Simulate input()'s validate on enter."""
        r_ctx = ResponseContext(prompt=self, response=self.buffer_as_string())

        if self.input_validator(r_ctx):
            self.prompt = original_prompt
            self._response = r_ctx.response
            ctx.keyboard.simulate(key=keys.ControlC)
        else:
            self._buffer.clear()

    def _interact_terminate(self, ctx: KeyPressContext) -> None:
        """Simulate input()'s SIGINT."""
        if ctx.key == keys.Escape:
            self.status = "CANCEL"

        ctx.keyboard.simulate(key=keys.ControlC)

    def interactivity(self, live: Live) -> None:
        """Handle taking input from the User."""
        original_prompt = str(self.prompt)

        kb = KeyboardListener()

        # Simulate being an input() subshell
        kb.bind(key=keys.Any, fn=self._interact_buffer_append)
        kb.bind(key=keys.Enter, fn=self._interact_validate, original_prompt=original_prompt)
        kb.bind(key=keys.Escape, fn=self._interact_terminate)
        kb.bind(key=keys.Backspace, fn=lambda: self._buffer.pop() if self._buffer else False)
        kb.bind(key=keys.Left, fn=lambda: self._buffer.pop() if self._buffer else False)
        kb.bind(key=keys.Any, fn=live.refresh)

        kb.run()

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        """How Rich should display the Prompt."""
        yield from super().__rich_console__(console=console, options=options)

        buffered_text = self.buffer_as_string(on_screen=True)

        if self.is_active and self.is_secret:
            self.detail = f"..currently {len(buffered_text)} characters"
            yield Text(buffered_text, style=Style(color="white", bgcolor="blue", bold=True))
        elif self.is_active:
            dim = "dim " if buffered_text == self.prefill else ""
            yield Text(buffered_text, style=f"bold {dim}white on blue")
        else:
            yield buffered_text
