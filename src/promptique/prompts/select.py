from __future__ import annotations

from typing import Any, Callable, Literal, Optional

from rich.console import Console, ConsoleOptions, RenderResult
from rich.live import Live
from rich.style import Style
from rich.text import Text
import pydantic

from promptique._base import BasePrompt
from promptique._keyboard import KeyboardListener, KeyPressContext
from promptique.keys import Keys


class PromptOption(pydantic.BaseModel):
    """Represent a choice a User can make."""

    text: str
    description: Optional[str] = None
    is_selected: bool = False
    is_highlighted: bool = False
    hotkey: Optional[str] = None

    def toggle(self) -> None:
        """Flip the value of .is_selected."""
        self.is_selected = False if self.is_selected else True


def _noop_always_valid(prompt, answer):
    return True


class Select(BasePrompt):
    """Ask the User to choose from a list of options."""

    choices: list[PromptOption]
    mode: Literal["SINGLE", "MULTI"]
    selection_validator: Callable[[BasePrompt, list[PromptOption]], bool] = pydantic.Field(default=_noop_always_valid)
    """Validates the answer, sets a warning if the selection is in an invalid state."""

    _UI_RADIO_ACTIVE: str = pydantic.PrivateAttr("●")
    _UI_RADIO_INACTIVE: str = pydantic.PrivateAttr("○")
    _UI_CHECK_ACTIVE: str = pydantic.PrivateAttr("◼")
    _UI_CHECK_INACTIVE: str = pydantic.PrivateAttr("◻")

    @pydantic.model_validator(mode="before")
    @classmethod
    def _convert_string_to_choice(cls, data: Any) -> Any:
        """Ensure all choice options are PromptOptions."""
        choices = data.pop("choices")
        data["choices"] = []

        if isinstance(choices, list):
            choices = {f"None_{n}": choice for n, choice in enumerate(choices)}

        for idx, (hotkey, choice) in enumerate(choices.items()):
            if isinstance(choice, str):
                hotkey = None if hotkey.startswith("None") else hotkey
                data["choices"].insert(idx, PromptOption(text=choice, is_highlighted=not idx, hotkey=hotkey))
            else:
                data["choices"].insert(idx, choice)

        if not any(choice.is_selected for choice in data["choices"]):
            data["choices"][0].is_selected = True

        return data

    @property
    def answer(self) -> list[PromptOption]:
        """Retrieve the valid answers."""
        return [option for option in self.choices if option.is_selected]

    def _get_highlighted_info(self) -> tuple[int, PromptOption]:
        """Implement a naive cursor fetcher. This could be better."""
        for idx, choice in enumerate(self.choices):
            if choice.is_highlighted:
                return (idx, choice)
        raise ValueError("No option is active.")

    def _input_highlighter(self, ctx: KeyPressContext) -> None:
        """ """
        idx, highlighted = self._get_highlighted_info()
        more_than_one_option = len(self.choices) > 1

        if ctx.key_press.key in (Keys.Right, Keys.Down):
            next_idx = (idx + 1) % len(self.choices)
            to_highlight = self.choices[next_idx]
            self.highlight(to_highlight.text)

            if self.mode == "SINGLE" and more_than_one_option:
                self.select(to_highlight.text)

        if ctx.key_press.key in (Keys.Left, Keys.Up):
            last_idx = (idx - 1) % len(self.choices)
            to_highlight = self.choices[last_idx]
            self.highlight(to_highlight.text)

            if self.mode == "SINGLE" and more_than_one_option:
                self.select(to_highlight.text)

    def _input_select(self) -> None:
        """ """
        more_than_one_option = len(self.choices) > 1

        if self.mode == "MULTI" and more_than_one_option:
            idx, highlighted = self._get_highlighted_info()
            self.select(highlighted.text)

    def _input_hotkey_select(self, *, choice) -> None:
        """ """
        self.select(choice.text)

        if self.mode == "SINGLE":
            self.highlight(choice.text)

    def _input_terminate(self, ctx: KeyPressContext) -> None:
        """ """
        self.status = "CANCEL"
        ctx.keyboard.simulate(key=Keys.ControlC)

    def _input_validate(self, ctx: KeyPressContext) -> None:
        """ """
        if self.selection_validator(self, self.answer):
            ctx.keyboard.simulate(key=Keys.ControlC)

    def select(self, choice: str) -> None:
        """Make a selection."""
        for option in self.choices:
            if option.text == choice and self.mode == "SINGLE" and option.is_selected:
                pass

            elif option.text == choice:
                option.toggle()

            elif self.mode == "SINGLE":
                option.is_selected = False

    def highlight(self, choice: str) -> None:
        """Highlight an option."""
        for option in self.choices:
            if option.text == choice:
                option.is_highlighted = True
            else:
                option.is_highlighted = False

    def interactivity(self, live: Live) -> None:
        """Handle selecting one of the choices from the User."""
        kb = KeyboardListener()

        # Add controls to our selection UI.
        kb.bind(key=Keys.Up, fn=self._input_highlighter)
        kb.bind(key=Keys.Right, fn=self._input_highlighter)
        kb.bind(key=Keys.Down, fn=self._input_highlighter)
        kb.bind(key=Keys.Left, fn=self._input_highlighter)
        kb.bind(key=Keys.Escape, fn=self._input_terminate)
        kb.bind(key=Keys.Enter, fn=self._input_validate)
        kb.bind(key=Keys.Any, fn=live.refresh)

        # Add default choice selector
        kb.bind(key=" ", fn=self._input_select)

        # Add hotkey choice selectors
        for choice in self.choices:
            if choice.hotkey is not None:
                kb.bind(key=choice.hotkey, fn=self._input_hotkey_select, choice=choice)
                kb.bind(key=choice.hotkey.lower(), fn=self._input_hotkey_select, choice=choice)

        kb.run()

    def draw_selector(self) -> Text:
        """Render the choices to select from."""
        # fmt: off
        active = self._UI_RADIO_ACTIVE   if self.mode == "SINGLE" else self._UI_CHECK_ACTIVE
        hidden = self._UI_RADIO_INACTIVE if self.mode == "SINGLE" else self._UI_CHECK_INACTIVE
        choices  = []
        # fmt: on

        for option in self.choices:
            # fmt: off
            marker = active if option.is_selected else hidden
            focus  = option.is_highlighted and self.is_active
            color  = "green" if (focus or option.is_selected and not self.is_active) else "white"
            choice = Text(text=f"{marker} {option.text}", style=Style(color=color, bold=True, dim=not focus))

            if self.is_active or (not self.is_active and option.is_selected):
                choices.append(choice)
            # fmt: on

        return Text(text=" / ").join(choices)

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        """How Rich should display the Prompt."""
        yield from super().__rich_console__(console=console, options=options)
        yield self.draw_selector()

        if self.is_active:
            highlighted = next(option for option in self.choices if option.is_highlighted)

            if highlighted.description is not None:
                yield Text(text=highlighted.description, style=Style(color="green", bold=True, italic=True, dim=True))


class Confirm(Select):
    """Ask the User a Yes/No question."""

    default: Literal["Yes", "No"]
    choice_means_stop: Optional[Literal["Yes", "No"]] = None

    def __init__(self, **options):
        default = options.get("default")
        choices = [
            PromptOption(text="Yes", is_selected="Yes" == default, is_highlighted="Yes" == default, hotkey="Y"),
            PromptOption(text="No", is_selected="No" == default, is_highlighted="No" == default, hotkey="N"),
        ]
        super().__init__(choices=choices, mode="SINGLE", selection_validator=Confirm.cancel_if_stop_choice, **options)

    @classmethod
    def cancel_if_stop_choice(cls, prompt: BasePrompt, answer: list[PromptOption]) -> bool:
        """Set internal state if the answer means cancelled."""
        assert isinstance(prompt, Confirm)

        # In single-select mode, there is always only ever 1 answer.
        if answer[0].text == prompt.choice_means_stop:
            prompt.status = "CANCEL"

        return True
