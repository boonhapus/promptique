from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Literal, Optional

from rich.style import Style
from rich.text import Text
import pydantic

from promptique import keys
from promptique._base import BasePrompt
from promptique.keyboard import KeyboardListener
from promptique.validation import ResponseContext, noop_always_valid

if TYPE_CHECKING:
    from rich.console import Console, ConsoleOptions, RenderResult
    from rich.live import Live

    from promptique.keyboard import KeyPressContext


class PromptOption(pydantic.BaseModel):
    """Represent a choice a User can make."""

    text: str
    description: Optional[str] = None
    is_selected: bool = False
    hotkey: Optional[str] = None

    def toggle(self) -> None:
        """Flip the value of .is_selected."""
        self.is_selected = False if self.is_selected else True


class Select(BasePrompt):
    """Ask the User to choose from a list of options."""

    choices: list[PromptOption]
    mode: Literal["SINGLE", "MULTI"]
    selection_validator: Callable[[ResponseContext], bool] = pydantic.Field(default=noop_always_valid)
    """Validates the answer, sets a warning if the selection is in an invalid state."""

    _focused: Optional[PromptOption] = None
    """The first highlighted option. If no choices are highlighted, the first option will be highlited on __init__"""

    # UI ELEMENTS
    _UI_RADIO_ACTIVE: str = "●"
    _UI_RADIO_INACTIVE: str = "○"
    _UI_CHECK_ACTIVE: str = "◼"
    _UI_CHECK_INACTIVE: str = "◻"

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
                data["choices"].insert(idx, PromptOption(text=choice, hotkey=hotkey))
            else:
                data["choices"].insert(idx, choice)

        return data

    @pydantic.model_validator(mode="after")
    def _force_at_least_one_selection(self):
        try:
            self._focused = next(choice for choice in self.choices if choice.is_selected)
        except StopIteration:
            self._focused = self.choices[0]
            self._focused.is_selected = True

    def _interact_focus(self, ctx: KeyPressContext) -> None:
        """Move to the next/previous option under focus."""
        assert self._focused is not None
        more_than_one_option = len(self.choices) > 1
        idx = self.choices.index(self._focused)

        if ctx.key in (keys.Right, keys.Down):
            next_idx = (idx + 1) % len(self.choices)
            self._focused = self.choices[next_idx]

            if self.mode == "SINGLE" and more_than_one_option:
                self.select(self._focused)

        if ctx.key in (keys.Left, keys.Up):
            last_idx = (idx - 1) % len(self.choices)
            self._focused = self.choices[last_idx]

            if self.mode == "SINGLE" and more_than_one_option:
                self.select(self._focused)

    def _interact_select(self) -> None:
        """Select the option under highlight."""
        assert self._focused is not None
        more_than_one_option = len(self.choices) > 1

        if self.mode == "MULTI" and more_than_one_option:
            self.select(self._focused)

    def _interact_hotkey_select(self, *, choice: PromptOption) -> None:
        """Select based on the given hotkey."""
        self.select(choice)
        self._focused = choice

    def _interact_terminate(self, ctx: KeyPressContext) -> None:
        """Quit the prompt."""
        self.status = "CANCEL"
        ctx.keyboard.simulate(key=keys.ControlC)

    def _interact_validate(self, ctx: KeyPressContext) -> None:
        """Validate the prompt choice."""
        try:
            response_ctx = ResponseContext(prompt=self, response=[opt for opt in self.choices if opt.is_selected])
            self.selection_validator(response_ctx)

        except AssertionError as e:
            self.warning = str(e)

        else:
            self._response = response_ctx.response
            ctx.keyboard.simulate(key=keys.ControlC)

    def select(self, choice: PromptOption) -> None:
        """Make a selection."""
        for option in self.choices:
            is_selected_option = option == choice

            if is_selected_option and self.mode == "SINGLE" and option.is_selected:
                pass

            elif is_selected_option:
                option.toggle()

            elif self.mode == "SINGLE":
                option.is_selected = False

    def interactivity(self, live: Live) -> None:
        """Handle selecting one of the choices from the User."""
        kb = KeyboardListener()

        # Add controls to our selection UI.
        kb.bind(keys.Up, keys.Right, keys.Down, keys.Left, fn=self._interact_focus)
        kb.bind(keys.Escape, fn=self._interact_terminate)
        kb.bind(keys.Enter, fn=self._interact_validate)
        kb.bind(keys.Any, fn=live.refresh)

        # Add default choice selector
        kb.bind(keys.Space, fn=self._interact_select)

        # Add hotkey choice selectors
        for choice in self.choices:
            if choice.hotkey is not None:
                kb.bind(
                    keys.Key.letter(choice.hotkey.lower()),
                    keys.Key.letter(choice.hotkey.upper()),
                    fn=self._interact_hotkey_select,
                    choice=choice,
                )

        kb.run()

    def draw_selector(self) -> Text:
        """Render the choices to select from."""
        # fmt: off
        active   = self._UI_RADIO_ACTIVE   if self.mode == "SINGLE" else self._UI_CHECK_ACTIVE
        inactive = self._UI_RADIO_INACTIVE if self.mode == "SINGLE" else self._UI_CHECK_INACTIVE
        choices  = []
        # fmt: on

        for option in self.choices:
            # fmt: off
            marker = active if option.is_selected else inactive
            focus  = self._focused == option
            color  = "green" if (focus or option.is_selected) else "white"
            choice = Text(text=f"{marker} {option.text}", style=Style(color=color, bold=True, dim=not focus))
            # fmt: on

            if self.is_active or option.is_selected:
                choices.append(choice)

        return Text(text=" / ").join(choices)

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        """How Rich should display the Prompt."""
        assert self._focused is not None
        yield from super().__rich_console__(console=console, options=options)
        yield self.draw_selector()

        if self.is_active and self._focused.description is not None:
            yield Text(text=self._focused.description, style=Style(color="green", bold=True, italic=True, dim=True))


class Confirm(Select):
    """Ask the User a Yes/No question."""

    default: Literal["Yes", "No"]
    choice_means_stop: Optional[Literal["Yes", "No"]] = None

    def __init__(self, **options):
        choices = [
            PromptOption(text="Yes", is_selected="Yes" == options["default"], hotkey="Y"),
            PromptOption(text="No", is_selected="No" == options["default"], hotkey="N"),
        ]
        super().__init__(choices=choices, mode="SINGLE", selection_validator=Confirm.cancel_if_stop_choice, **options)

    @staticmethod
    def cancel_if_stop_choice(ctx: ResponseContext) -> bool:
        """Set internal state if the answer means cancelled."""
        assert isinstance(ctx.prompt, Confirm)

        # In single-select mode, there is always only ever 1 answer.
        if ctx.response[0].text == ctx.prompt.choice_means_stop:
            ctx.prompt.status = "CANCEL"

        return True
