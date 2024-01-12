from __future__ import annotations

import asyncio

import pytest

from promptique._keyboard import KeyboardListener


@pytest.mark.asyncio
async def test_can_run_async():
    kb = KeyboardListener()

    _ = asyncio.create_task(kb.start())
    await asyncio.sleep(0)
    assert kb._background_done.is_set() is False
    assert kb._is_accepting_keys is True

    await kb.stop()
    assert kb._background_done.is_set() is True
    assert kb._is_accepting_keys is False
