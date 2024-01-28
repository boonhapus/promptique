from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from collections.abc import Iterable

    from promptique._base import BasePrompt


class ResponseContext:
    """Represent the result of User interaction with a prompt."""

    def __init__(self, prompt: BasePrompt, response: Any):
        self.prompt = prompt
        self.response = response


def noop_always_valid(ctx: ResponseContext) -> bool:  # noqa: ARG001
    """For any given input, always pass validation."""
    return True


def response_not_null(ctx: ResponseContext) -> bool:
    """Ensure the input is given."""
    assert ctx.response, "You must give a response!"
    return True


def response_is(value: Any, *, any_of: bool = False) -> Callable[[ResponseContext], bool]:
    """Compare the response of a Prompt against a given value."""

    def decorator(ctx: ResponseContext) -> bool:
        values: Iterable[Any] = ctx.response if any_of else [ctx.response]
        return any(getattr(r, "text", r) == value for r in values)

    return decorator
