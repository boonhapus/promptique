from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from promptique._base import BasePrompt


class ResponseContext:
    """Represent the result of User interaction with a prompt."""

    def __init__(self, prompt: BasePrompt, response: Any):
        self.prompt = prompt
        self.response = response


def noop_always_valid(ctx: ResponseContext) -> bool:  # noqa: ARG001
    """For any given input, always pass validation."""
    return True
