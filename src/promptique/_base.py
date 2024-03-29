from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Optional
import logging
import uuid

from rich.measure import Measurement
from rich.style import Style
from rich.styled import Styled
from rich.text import Text
import pydantic

from promptique.types import PromptStatus
from promptique.validation import ResponseContext

if TYPE_CHECKING:
    from types import TracebackType

    from rich.console import Console, ConsoleOptions, RenderResult
    from rich.live import Live

    from promptique._compat import Self
    from promptique.menu import Menu

log = logging.getLogger(__name__)


class BasePrompt(pydantic.BaseModel, arbitrary_types_allowed=True):
    """A base class for Prompts."""

    id: str = pydantic.Field(default_factory=lambda: uuid.uuid4().hex)
    prompt: str
    detail: Optional[str] = None
    transient: bool = False

    _response: Optional[Any] = None
    _warning: Optional[str] = None
    _exception: Optional[BaseException] = None
    _status: PromptStatus = "HIDDEN"

    _marker_static: Optional[str] = None
    """Allow the prompt marker to be set explicitly."""

    _menu: "Menu" = pydantic.PrivateAttr()
    """Place this prompt inside a Menu."""

    _linked_prompts: list[Callable[[ResponseContext], None]] = pydantic.PrivateAttr(default_factory=list)
    """Prompts to attempt running after this prompt."""

    @property
    def is_active(self) -> bool:
        """Determine if the Prompt is active."""
        return self._status in ("ACTIVE", "WARNING")

    @property
    def marker(self) -> Optional[str]:
        """Retrieve the prompt's marker override."""
        return self._marker_static

    @marker.setter
    def marker(self, marker: str) -> None:
        self._marker_static = marker

    @property
    def status(self) -> PromptStatus:
        """Retrieve the prompt's status."""
        return self._status

    @status.setter
    def status(self, status: PromptStatus) -> None:
        self._status = status

    @property
    def warning(self) -> Optional[str]:
        """Retrieve the warning message, if one is set."""
        return self._warning

    @warning.setter
    def warning(self, message: str) -> None:
        self._warning = message
        self._status = "WARNING"

    @property
    def exception(self) -> Optional[BaseException]:
        """Retrieve the exception, if one occurred."""
        return self._exception

    @exception.setter
    def exception(self, exception: Exception) -> None:
        self._exception = exception
        self._status = "ERROR"

    def __rich_measure__(self, console: Console, options: ConsoleOptions) -> Measurement:
        """Describes the the min/max number of characters required to render."""
        sized_content = Measurement.get(console, options, self.prompt)
        return sized_content.with_maximum(options.max_width)

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        """How Rich should display the Prompt."""
        yield self.prompt

        if not self.is_active:
            pass

        elif self.warning is not None:
            yield Text.from_markup(f"X [dim white]>>[/] {self.warning}")

        elif self.detail is not None:
            yield Styled(self.detail, style=Style(color="white", dim=True))

    def __str__(self) -> str:
        return f"<{self.__class__.__name__} id='{self.id}', status='{self.status}'>"

    def __enter__(self) -> Self:
        self._status = "ACTIVE"
        return self

    def interactivity(self, live: Live) -> None:
        """Allow a Prompt to get feedback from the User."""
        # Override in a subclass to implement functionality.
        pass

    def bind(self, menu: Menu) -> BasePrompt:
        """Allow a Prompt to get feedback from the User."""
        self._menu = menu
        return self

    def link(self, next_prompt: BasePrompt, validator: Callable[[ResponseContext], None]) -> BasePrompt:
        """Chain a prompt to this one, based on the User's response."""

        def decorator(ctx: ResponseContext) -> None:
            if not validator(ctx):
                return

            ctx.prompt._menu.add(next_prompt, after=ctx.prompt)

        # .insert(0, ...) instead of .append because if the check passes we'll insert next_prompt after this one
        #  which would appear backwards to the user
        self._linked_prompts.insert(0, decorator)

        return self

    def __exit__(self, class_: type[BaseException], exception: BaseException, traceback: TracebackType) -> bool:
        if isinstance(exception, KeyboardInterrupt):
            self._status = "CANCEL"

        elif exception is not None:
            self.exception = exception
            log.error(
                f"{class_.__name__} occurred in {self.__class__.__name__} prompt, check .exception or see DEBUG log "
                f"for details..",
                exc_info=True,
            )
            log.debug("Full error..", exc_info=True)

        elif self.is_active:
            self._status = "SUCCESS" if not self.transient else "HIDDEN"

            # Process the linked Prompts to this one.
            ctx = ResponseContext(prompt=self, response=self._response)
            [link(ctx) for link in self._linked_prompts]

        # If we're exiting but we're not active or in an error state, then the status was set intentionally.
        else:
            pass

        return True
