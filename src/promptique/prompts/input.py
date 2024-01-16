from __future__ import annotations

from promptique._base import BasePrompt


class UserInput(BasePrompt):
    """Ask the User to type a response"""

    is_secret: bool = False
    input_validator: Callable[[BasePrompt, str], bool] = pydantic.Field(default=_noop_always_valid)
    """Validates the input, sets a warning if the selection is in an invalid state."""

    _buffer: list[str] = pydantic.PrivateAttr(default_factory=list)

    def buffer_as_string(self, *, on_screen: bool = False) -> str:
        """Render the buffer."""
        buffer = self._buffer

        if on_screen and self.is_secret:
            buffer = ["?" for character in self._buffer]

        return "".join(buffer)

    def set_buffer(self, user_input: str) -> None:
        """Directly set the underlying buffer."""
        self._buffer = list(user_input)

    def _input_validate(self, *, original_prompt: str) -> None:
        """Simulate input()'s validate on enter."""
        validated = self.input_validator(self, self.buffer_as_string())

        if validated:
            self.prompt = original_prompt
        else:
            self._buffer.clear()

    def _input_terminate(self, ctx: KeyPressContext, *, keyboard: KeyboardListener) -> None:
        """Simulate input()'s SIGINT."""
        if ctx.key == Keys.Escape:
            self.status = PromptStatus.cancel()

        keyboard.simulate(key=Keys.ControlC)

    def interactivity(self, live: Live) -> None:
        """Handle taking input from the User."""
        original_prompt = str(self.prompt)

        kb = KeyboardListener()

        # Simulate being an input() subshell
        kb.bind(key=Keys.Any, fn=lambda ctx: self._buffer.append(ctx.key) if ctx.key.is_printable else False)
        kb.bind(key=Keys.Enter, fn=self._input_validate, original_prompt=original_prompt)
        kb.bind(key=Keys.Escape, fn=self._input_terminate, keyboard=kb)
        kb.bind(key=Keys.Backspace, fn=lambda: self._buffer.pop() if self._buffer else False)
        kb.bind(key=Keys.Left, fn=lambda: self._buffer.pop() if self._buffer else False)
        kb.bind(key=Keys.Any, fn=live.refresh)

        kb.run()

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        """How Rich should display the Prompt."""
        yield from super().__rich_console__(console=console, options=options)

        buffered_text = self.buffer_as_string(on_screen=True)

        if self.is_active and self.is_secret:
            self.detail = f"..currently {len(buffered_text)} characters"
            yield Text(buffered_text, style=Style(color="white", bgcolor="blue", bold=True))
        elif self.is_active:
            yield Text(buffered_text, style="bold white on blue")
        else:
            yield buffered_text
