from __future__ import annotations

from typing import Optional

from rich._loop import loop_first_last
from rich.segment import Segment
from rich.style import Style

from promptique._base import BasePrompt
from promptique.theme import PromptTheme
from promptique.types import PromptPosition


class PromptRenderer:
    """
    Prompts in the menu have a left hand rail.

    A renderer simply allows prompts to be rendered.

      a. The first prompt in the menu will have a null-styled opening marker.
      b. All Prompts will have a .style'd status indicator shown at all times.
      c. All multi-prompts will have their non-marked lines shown as a .style'd rail.
      d. The active prompt will have the first line .style'd, with all other lines in
         the NULL_STYLE.
      e. The last line in the last prompt will have a closing marker.

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
    """

    MENU_RAIL_BEG = "┌"
    MENU_RAIL_BAR = "│"
    MENU_RAIL_END = "└"

    def __init__(self, prompt: BasePrompt, position: PromptPosition = "MIDDLE", theme: Optional[PromptTheme] = None):
        self.prompt = prompt
        self.padding_width = 2
        self.position = position
        self.theme = PromptTheme() if theme is None else theme

    def determine_rail_marker(self, is_first_line: bool) -> str:
        """ """
        marker = {
            "FIRST": PromptRenderer.MENU_RAIL_BEG,
            "MIDDLE": self.prompt._marker or self.theme[self.prompt.status].marker,
            "LAST": PromptRenderer.MENU_RAIL_END,
        }
        return marker[self.position] if is_first_line else PromptRenderer.MENU_RAIL_BAR

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

    def __rich_console__(self, console, options):
        NULL_STYLE = Style.null()

        render_options = options.update(max_width=options.max_width - self.padding_width)
        lines = console.render_lines(self.prompt, render_options, pad=False)

        if not self.position == "FIRST":
            yield PromptRenderer.MENU_RAIL_BAR

        for is_first_line, is_last_line, line in loop_first_last(lines):
            marker = self.determine_rail_marker(is_first_line)
            marker_style = self.determine_rail_style(is_first_line)
            line_style = self.determine_line_style(is_first_line)

            # assert len(marker) == 1
            yield Segment(text=f"{marker} ", style=marker_style)
            yield from Segment.apply_style(line, style=NULL_STYLE, post_style=line_style)
            yield Segment("\n")

            if self.prompt.is_active and is_last_line:
                yield Segment(PromptRenderer.MENU_RAIL_END, style=self.theme[self.prompt.status].style)
                yield Segment("\n")
