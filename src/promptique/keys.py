from __future__ import annotations

from typing import Any, Union

from prompt_toolkit.keys import Keys as _PromptToolkitKeys
import pydantic

# TODO:
# Create a proper namesake that implements a similar protocol to prompt_toolkit.keys.Keys , so users of our API don't
# confused using an object from another package.
#
# GOALS:
# We want to track things like.. Keys.Spacebar, Keys.Enter, etc ..like Prompt Toolkit does, but also allow things like
#
# - Keys.letter("A", case_sensitive=True)
# - Keys.number(1)
# - Keys.phrase("match this", case_sensitive=True)
#
Keys = _PromptToolkitKeys
_key_cache: dict[str, Key] = {}


def __getattr__(key_name: str) -> Key:
    try:
        key = _key_cache[key_name]
    except KeyError:
        raise AttributeError(f"AttributeError: module 'promptique.keys' has no attribute '{key_name}'") from None

    return key


class Key(pydantic.BaseModel, arbitrary_types_allowed=True):
    """Represent known keys."""

    name: str
    data: Any
    is_printable: bool = False

    @pydantic.model_validator(mode="after")
    def _cache_new_representation(self) -> Key:
        _key_cache[self.name] = self
        return self

    @classmethod
    def letter(cls, value: str, *, case_sensitive: bool = False) -> Key:
        """Convert a single character into a Key"""
        if len(value) > 1:
            raise ValueError(f"You must provide only single characters, got '{value}'")

        # Ensure we're caching both variants, future module level access will hit the cache
        if not case_sensitive:
            cls(name=value.upper(), data=value.upper())
            cls(name=value.lower(), data=value.lower())

        return _key_cache[value]

    @classmethod
    def number(cls, value: Union[str, int]) -> Key:
        """Convert a single number into a Key"""
        if not str(value).isdigit() or len(str(value)) > 1:
            raise ValueError(f"You must provide only single numbers, got '{value}'")

        return cls(name=f"number_{value}", data=value)


# HOW TO PROPERLY DO THIS ONLY ONCE?
if not _key_cache:
    _key_cache["Space"] = Key(name="Space", data=" ", is_printable=True)

    # See: https://github.com/prompt-toolkit/python-prompt-toolkit/blob/master/src/prompt_toolkit/keys.py
    for key in _PromptToolkitKeys:
        _key_cache[key.name] = Key(name=key.name, data=key.value, is_printable=False)
