from __future__ import annotations

from typing import Any

import pydantic

from promptique._base import BasePrompt


class ResponseContext(pydantic.BaseModel, arbitrary_types_allowed=True):
    """Represent the result of User interaction with a prompt."""

    prompt: BasePrompt
    response: Any


def noop_always_valid(ctx: ResponseContext) -> bool:
    """For any given input, always pass validation."""
    return True
