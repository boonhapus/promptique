from __future__ import annotations

from typing import Optional

from rich._loop import loop_first_last
from rich.console import Console, ConsoleOptions
from rich.segment import Segment
from rich.style import Style

from promptique._base import BasePrompt
from promptique.theme import PromptTheme
from promptique.types import PromptPosition


class PromptRenderer:
    """
    Wrap prompt rendering so that they fit into a menu.

    To implement, simply define a __rich_console__ method.

    The default PromptRenderer will place a marker in front of the first line
    in a prompt, and a rail on every other line. The first and last lines of
    the menu as a whole will have overridden markers as well.

    a. The first marker will be overriden with a top-wrap character.
    b. The prompt marker will take the theme style.
    e. The last marker will be overriden with a bottom-wrap character.


    A --> ┌ cs_tools config create
          │
    B --> ◇ Please name your configuration.
    C --> │ 710
          │
          ◇ Config 710 exists, do you want to overwrite it?
          │ ● Yes / ○ No
          │
          ...
          │
    D --> ◆ Which authentication method do you want to use?
      --> │ ◻ Password / ◼ Trusted Authentication / ◻ Bearer Token
      --> │ this is the password used on the ThoughtSpot login screen
          │
          ...
          │
    E --> └ Complete!

    Attributes
    ----------
    prompt: BasePrompt
      ...

    position: PromptPosition
      ...

    theme: PromptTheme
      ...
    """

    MENU_RAIL_BEG = "┌"
    MENU_RAIL_BAR = "│"
    MENU_RAIL_END = "└"

    def __init__(self, prompt: BasePrompt, position: PromptPosition, theme: Optional[PromptTheme] = None):
        self.prompt = prompt
        self.position = position
        self.theme = PromptTheme() if theme is None else theme

    @property
    def max_marker_width(self) -> int:
        """Find the length of the longest marker on a prompt."""
        return len(self.prompt.marker or self.theme[self.prompt.status].marker)

    def determine_rail_marker(self, is_first_line: bool) -> str:
        """ """
        if self.position == "FIRST":
            marker = PromptRenderer.MENU_RAIL_BEG

        elif self.position == "LAST" and not self.prompt.is_active:
            marker = PromptRenderer.MENU_RAIL_END

        elif is_first_line:
            marker = self.prompt.marker or self.theme[self.prompt.status].marker

        else:
            marker = PromptRenderer.MENU_RAIL_BAR

        return marker

    def determine_rail_style(self, is_first_line: bool) -> Style:
        """ """
        style = Style.null()

        if is_first_line and self.position == "MIDDLE":
            style = self.theme[self.prompt.status].style

        elif self.prompt.is_active and self.prompt.warning is not None:
            style = self.theme[self.prompt.status].style

        elif self.prompt.is_active:
            style = self.theme[self.prompt.status].style

        elif self.prompt.status != "SUCCESS" and not is_first_line:
            style = self.theme[self.prompt.status].style

        return style

    def determine_line_style(self, is_first_line: bool) -> Style:
        """ """
        style = self.theme[self.prompt.status].style

        if self.prompt.is_active and not is_first_line:
            style = Style.null()

        elif not self.prompt.is_active and is_first_line and self.prompt.status == "SUCCESS":
            style = Style.null()

        elif not self.prompt.is_active and not is_first_line:
            style = Style(color="white", dim=True)

        return style

    def __rich_console__(self, console: Console, options: ConsoleOptions):
        NULL_STYLE = Style.null()

        render_options = options.update(max_width=options.max_width - self.max_marker_width)
        lines = console.render_lines(self.prompt, render_options, pad=False)

        # Add the │ prior to creating the prompt, this is our gap character.
        if not self.position == "FIRST":
            yield PromptRenderer.MENU_RAIL_BAR

        for is_first_line, is_last_line, line in loop_first_last(lines):
            marker = self.determine_rail_marker(is_first_line)
            marker_style = self.determine_rail_style(is_first_line)
            line_style = self.determine_line_style(is_first_line)

            yield Segment(text=f"{marker} ", style=marker_style)
            yield from Segment.apply_style(line, style=NULL_STYLE, post_style=line_style)
            yield Segment("\n")

            if self.prompt.is_active and is_last_line:
                yield Segment(PromptRenderer.MENU_RAIL_END, style=self.theme[self.prompt.status].style)
                yield Segment("\n")
