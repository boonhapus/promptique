from __future__ import annotations

from prompt_toolkit.keys import Keys as _PromptToolkitKeys

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


# class Keys(pydantic.BaseModel, arbitrary_types_allowed=True):
#     """Represent known keys."""
#
#     @classmethod
#     def from_ptk_keys(cls, keys: _PromptToolkitKeys) -> Keys:
#         return cls()
#
#     @classmethod
#     @ft.cache
#     def new_representation(cls, data) -> Keys:
#         return cls(...)
#
#     @classmethod
#     def letter(cls, value: Any) -> Key:
#         """Convert a single character into a Key"""
#         if len(str(value)) > 1:
#             raise ValueError(f"You must only provide single characters, got '{value}'")
#         return cls.new_representation(key=str(value).encode())
#
