from __future__ import annotations

from typing import Callable, Literal, Optional
import pathlib
import stat
import threading

from rich._emoji_replace import _emoji_replace
from rich.console import Console, ConsoleOptions, RenderResult
from rich.live import Live
from rich.style import Style
from rich.text import Text
import pydantic

from promptique import keys
from promptique._base import BasePrompt
from promptique.keyboard import KeyboardListener, KeyPressContext
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
        self.status = "CANCEL"
        ctx.keyboard.simulate(key=keys.ControlC)

    def interactivity(self, live: Live) -> None:
        """Handle taking input from the User."""
        original_prompt = str(self.prompt)

        kb = KeyboardListener()

        # Simulate being an input() subshell
        kb.bind(keys.Any, fn=self._interact_buffer_append)
        kb.bind(keys.Enter, fn=self._interact_validate, original_prompt=original_prompt)
        kb.bind(keys.Escape, fn=self._interact_terminate)
        kb.bind(keys.Backspace, keys.Left, fn=lambda: self._buffer.pop() if self._buffer else False)
        kb.bind(keys.Any, fn=live.refresh)

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


class FileInput(UserInput):
    """Ask the User for a File or Directory."""

    path_type: Literal["ANY", "FILE", "DIRECTORY"] = "ANY"
    show_hidden_files: bool = False
    page_size: int = 10
    exists: bool = True

    _suggestions: list[pathlib.Path] = pydantic.PrivateAttr(default_factory=list)
    _root: pathlib.Path = pathlib.Path(".").resolve()
    _debounce_handle: Optional[threading.Timer] = None
    _current_page: int = 1
    _response: Optional[pathlib.Path] = None  # type: ignore[assignment]

    def __init__(self, **options):
        super().__init__(prefill=pathlib.Path().resolve().as_posix(), input_validator=FileInput.is_path_type, **options)
        self._update_suggestions()

    @staticmethod
    def is_path_type(ctx: ResponseContext) -> bool:
        """Determine if the input was a valid Path."""
        assert isinstance(ctx.prompt, FileInput)

        if not ctx.prompt.exists:
            return True

        if ctx.prompt.path_type == "FILE" and not ctx.response.is_file():
            ctx.prompt.warning = "Path must be a valid existing File!"
            return False

        if ctx.prompt.path_type == "DIRECTORY" and not ctx.response.is_dir():
            ctx.prompt.warning = "Path must be a valid existing Directory!"
            return False

        return True

    @property
    def root(self) -> pathlib.Path:
        """The rirectory to start our path search in."""
        return self._root

    @root.setter
    def root(self, value: pathlib.Path) -> None:
        assert isinstance(value, pathlib.Path), f"FileInput.root must be a pathlib.Path, got {type(value)}"
        self._current_page = 1
        self._root = value

    @property
    def max_pages(self) -> int:
        """Calculate the number of pages to draw."""
        pages, excess = divmod(len(self._suggestions), self.page_size)
        return pages + (1 if excess else 0)

    def _update_suggestions(self) -> None:
        """Fetch all relevant path recommendations."""
        prefix = self.buffer_as_string()
        self._suggestions = []

        for suggestion in self.root.iterdir():
            if self.path_type == "FILE" and not suggestion.is_file():
                continue

            if self.path_type == "DIRECTORY" and not suggestion.is_dir():
                continue

            if not self.show_hidden_files and suggestion.stat().st_file_attributes & stat.FILE_ATTRIBUTE_HIDDEN:
                continue

            if suggestion.as_posix().lower().startswith(prefix.lower()):
                self._suggestions.append(suggestion)

    def _interact_buffer_append(self, ctx: KeyPressContext) -> None:
        """Add to the buffer if the key is printable."""
        if ctx.key == keys.Key.letter("\\"):
            self._buffer.append("/")
            self.root = pathlib.Path(self.buffer_as_string())

        elif ctx.key == keys.Key.letter('"'):
            pass

        elif ctx.key.is_printable:
            self._buffer.append(ctx.key.data)
            self._current_page = 1

        self._update_suggestions()

    def _interact_buffer_remove(self) -> None:
        """Remove characters from the buffer."""
        if not self._buffer:
            return

        if self._buffer.pop() == "/":
            self.root = self.root.parent

        self._update_suggestions()

    def _interact_accept_next_suggestion(self) -> None:
        """Simulate tab completion."""
        try:
            suggestion = self._suggestions[0]
        except IndexError:
            return

        if suggestion.is_dir():
            self.root = suggestion

        self._buffer = list(suggestion.as_posix())
        self._update_suggestions()

    def _interact_update_root(self, ctx: KeyPressContext) -> None:
        """When we hit a path delimiter, update the root path."""
        self._buffer.append(ctx.key.data)
        self.root = pathlib.Path(self.buffer_as_string())

    def _interact_validate(self, ctx: KeyPressContext, *, original_prompt: str) -> None:
        """Simulate input()'s validate on enter."""
        r_ctx = ResponseContext(prompt=self, response=pathlib.Path(self.buffer_as_string()))

        if self.input_validator(r_ctx):
            self.prompt = original_prompt
            self._response = r_ctx.response
            self._suggestions = []
            ctx.keyboard.simulate(key=keys.ControlC)

    def _interact_page(self, ctx: KeyPressContext) -> None:
        """When we hit a path delimiter, update the root path."""
        if ctx.key in (keys.PageUp, keys.Up):
            self._current_page = max(self._current_page - 1, 1)

        if ctx.key in (keys.PageDown, keys.Down):
            self._current_page = min(self.max_pages, self._current_page + 1)

    def interactivity(self, live: Live) -> None:
        """Handle taking input from the User."""
        original_prompt = str(self.prompt)

        kb = KeyboardListener()
        kb.bind(keys.Any, fn=self._interact_buffer_append)
        kb.bind(keys.Backspace, keys.Left, fn=self._interact_buffer_remove)
        kb.bind(keys.Tab, fn=self._interact_accept_next_suggestion)
        kb.bind(keys.Key.letter("/"), fn=self._interact_update_root)
        kb.bind(keys.PageUp, keys.PageDown, keys.Up, keys.Down, fn=self._interact_page)
        kb.bind(keys.Enter, fn=self._interact_validate, original_prompt=original_prompt)
        kb.bind(keys.Escape, fn=self._interact_terminate)
        kb.bind(keys.Any, fn=live.refresh)
        kb.run()

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        """How Rich should display the Prompt."""
        yield from super().__rich_console__(console=console, options=options)

        if self.is_active and self._suggestions:
            yield Text("\n>>> Suggestions ") + Text(f"{self._current_page}/{self.max_pages}", style="dim white")

            for idx, suggestion in enumerate(self._suggestions):
                min_result = (self._current_page * self.page_size) - self.page_size
                max_result = self._current_page * self.page_size

                if min_result <= idx < max_result:
                    emoji = ":page_facing_up:" if suggestion.is_file() else ":file_folder:"
                    yield Text(f"{_emoji_replace(emoji)} {suggestion.as_posix()}", style="bold dim white")

                if max_result < idx:
                    yield Text("more..", style="bold dim white")
                    break
