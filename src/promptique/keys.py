from __future__ import annotations

import datetime as dt

from prompt_toolkit.key_binding import KeyPress  # noqa: TCH002
from prompt_toolkit.keys import Keys
import pydantic


class KeyPressContext(pydantic.BaseModel, arbitrary_types_allowed=True):
    """Metadata about when a KeyPress happened."""

    key_press: KeyPress
    when: pydantic.AwareDatetime = pydantic.Field(default_factory=dt.datetime.utcnow)

    def __str__(self) -> str:
        return f"<KeyPressContext key={self.key_press.key}, when='{self.when:%H:%M:%S.%f}'>"


# TODO: create namesake that implements a similar protocol to prompt_toolkit.keys.Keys
Keys = Keys
