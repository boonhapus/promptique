from __future__ import annotations

from collections.abc import Iterable
from typing import Optional

from rich._loop import loop_first_last
from rich.console import Console, Group, RenderableType
from rich.live import Live

from promptique import _utils
from promptique._base import BasePrompt
from promptique.prompts import Note
from promptique.renderer import PromptRenderer
from promptique.theme import PromptTheme
from promptique.types import PromptPosition


class Menu:
    """
    Draw an interactive menu of prompts.

    Prompts start off in a hidden state, and only come into view as we progress
    through the menu. Transient prompts will be hidden once they've been
    interacted with.
    """

    def __init__(
        self,
        *prompts: BasePrompt,
        intro: str,
        outro: Optional[str] = None,
        console: Optional[Console] = None,
        transient: bool = False,
        theme: Optional[PromptTheme] = None,
    ):
        intro = Note(id="intro", prompt=intro) if isinstance(intro, str) else intro  # type: ignore[assignment]
        outro = Note(id="outro", prompt=outro) if isinstance(outro, str) else outro  # type: ignore[assignment]
        self.has_outro = outro is not None
        self.prompts: list[BasePrompt] = [p for p in (intro, *prompts, outro) if isinstance(p, BasePrompt)]
        self.console = Console() if console is None else console
        self.theme = PromptTheme() if theme is None else theme
        self.prompt_renderer = PromptRenderer
        self.live = Live(
            console=console,
            auto_refresh=False,
            transient=transient,
            get_renderable=self.get_renderable,
            vertical_overflow="visible",
        )

    def __rich__(self) -> RenderableType:
        """Makes the Prompt Menu class itself renderable."""
        return self.get_renderable()

    def get_renderable(self) -> RenderableType:
        """Get a renderable for the prompt menu."""
        renderables = self.build_menu()

        console_width, console_height = self.console.size
        renders_width, renders_height = _utils.reshape_and_measure(*renderables, console=self.console)

        if renders_height > console_height and self.live.is_started:
            renderables = _utils.fake_scroll(renderables, console=self.console, overage=renders_height - console_height)

        return Group(*renderables)

    def build_menu(self) -> Iterable[RenderableType]:
        """Get a number of renderables for the prompt menu."""
        renderables: list[RenderableType] = []

        for is_first_prompt, is_last_prompt, prompt in loop_first_last(self.prompts):
            if prompt.status == "HIDDEN":
                continue

            position: PromptPosition = "MIDDLE"

            if is_first_prompt:
                position = "FIRST"

            if is_last_prompt:
                position = "LAST"

            multiline_prompt = self.prompt_renderer(prompt, position=position, theme=self.theme)
            renderables.append(multiline_prompt)

        return renderables

    def start(self) -> None:
        """
        Start the prompt menu.

        You should prefer to use .begin().
        """
        self.live.start()

    def stop(self, refresh: bool = True) -> None:
        """
        Stop the prmopt menu.

        You should prefer to use .begin().
        Any remaining prompts will remain hidden.
        """
        if refresh:
            self.live.refresh()

        self.live.stop()

    def handle_prompt(self, prompt: BasePrompt) -> None:
        """
        Progress through a prmopt in the menu.

        You should prefer to use .begin().
        """
        with prompt:
            self.live.refresh()

            prompt.interactivity(live=self.live)

    def add(self, prompt: BasePrompt, *, after: Optional[BasePrompt] = None) -> None:
        """Add a prompt to the menu."""
        if after is None:
            after = self.prompts[-1] if not self.has_outro else self.prompts[-2]

        self.prompts.insert(self.prompts.index(after) + 1, prompt)

    def run(self) -> None:
        """Progress through all prompts."""
        self.start()

        for prompt in self.prompts:
            self.handle_prompt(prompt)

            if prompt.status in ("CANCEL", "ERROR"):
                break

        self.stop()
