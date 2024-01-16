from __future__ import annotations

from typing import Literal

PromptStatus = Literal["HIDDEN", "ACTIVE", "SUCCESS", "WARNING", "ERROR", "CANCEL"]
PromptPosition = Literal["FIRST", "MIDDLE", "LAST"]
