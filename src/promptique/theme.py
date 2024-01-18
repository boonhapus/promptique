from __future__ import annotations

from typing import Annotated, Any
import logging

from rich.console import Group
from rich.panel import Panel
from rich.style import Style
from rich.text import Text
import pydantic
import rich

from promptique.types import PromptStatus

log = logging.getLogger(__name__)


class ThemeElement(pydantic.BaseModel, arbitrary_types_allowed=True):
    """Necessary information to render a status."""

    marker: Annotated[str, pydantic.StringConstraints(min_length=1, max_length=1)]
    style: Style

    _status: PromptStatus = pydantic.PrivateAttr()

    @pydantic.field_validator("style", mode="before")
    @classmethod
    def _parse_style(cls, styleable: Any) -> Style:
        if isinstance(styleable, Style):
            return styleable

        if isinstance(styleable, str):
            return Style.parse(styleable)

        raise ValueError(f"'style' must be a parseable rich.style.Style, got '{styleable}' ({type(styleable)})")

    def __set_name__(self, owner, name: str) -> None:
        """Assume the name of the variable we're being set to."""
        self._status = name.upper()  # type: ignore[assignment]

    def __eq__(self, other: object) -> bool:
        if isinstance(other, ThemeElement):
            return self.status == other.status

        if isinstance(other, str):
            return self.status == other.upper()

        raise NotImplementedError

    def __rich__(self) -> Text:
        return Text("<Status ") + Text(self.status, style=self.style) + Text(f" [{self.marker}]>")

    def __str__(self) -> str:
        return self.__rich__().plain

    @property
    def status(self) -> PromptStatus:
        """Get the status."""
        return self._status


class PromptTheme(pydantic.BaseModel, arbitrary_types_allowed=True):
    """Represent a theme for prompts in a menu."""

    hidden: ThemeElement = ThemeElement(marker=" ", style=Style.null())
    active: ThemeElement = ThemeElement(marker="◆", style=Style(color="blue", bold=True))
    success: ThemeElement = ThemeElement(marker="◇", style=Style(color="green", bold=True))
    warning: ThemeElement = ThemeElement(marker="◈", style=Style(color="yellow"))
    error: ThemeElement = ThemeElement(marker="✦", style=Style(color="red", bold=True))
    cancel: ThemeElement = ThemeElement(marker="◈", style=Style(color="white", bold=True, dim=True))

    def __getitem__(self, element_name: str) -> ThemeElement:
        try:
            return getattr(self, element_name.lower())
        except AttributeError:
            raise KeyError(f"No theme element by name '{element_name.lower()}'") from None

    def __rich__(self) -> Panel:
        sample = "Lorem ipsum dolor sit amet.."
        renderables = []

        for render_status in (self.hidden, self.active, self.success, self.warning, self.error, self.cancel):
            renderables.append(
                Text(f"{render_status.status: >7}", style=render_status.style)
                + Text(" | ", style=Style(color="white", dim=False))
                + Text(f"{render_status.marker} {sample}", style=render_status.style),
            )

        return Panel(Group(*renderables), expand=False)

    def get_style_for(self, status: str) -> Style:
        """Return the style for a given theme element."""
        styled = getattr(self, status.casefold(), Style.null())

        if styled is Style.null():
            log.warning(f"No style found for status '{status.upper()}'")

        return styled

    def get_marker_for(self, status: str) -> str:
        """Return the marker for a given theme element."""
        marker = getattr(self, status.casefold(), " ")

        if marker == " ":
            log.warning(f"No marker found for status '{status.upper()}'")

        return marker


if __name__ == "__main__":
    rich.print(PromptTheme())
