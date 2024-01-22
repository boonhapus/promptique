from __future__ import annotations

from collections.abc import Iterable
from typing import Callable, Literal
import functools as ft
import itertools as it
import threading
import time

from rich.live import Live

from promptique._base import BasePrompt


class Note(BasePrompt):
    """Print an informative message."""

    on_screen_time: float = 0

    def interactivity(self, live: Live) -> None:  # noqa: ARG002
        """Optionally give the User some time to read."""
        time.sleep(self.on_screen_time)


class Spinner(BasePrompt):
    """ """

    background: Callable
    icons: Iterable[str] = ("◒", "◐", "◓", "◑")
    rate: float = 3.0
    location: Literal["MARKER", "DETAIL"] = "MARKER"
    transient: bool = True

    def interactivity(self, live: Live) -> None:
        """Optionally give the User some time to read."""
        if self.location == "MARKER":
            update_visible_icon = ft.partial(setattr, self, "marker")

        if self.location == "DETAIL":
            update_visible_icon = ft.partial(setattr, self, "detail")

        icons = it.cycle(self.icons)
        update_visible_icon(next(icons))

        bg_worker = threading.Thread(target=self.background)
        bg_worker.start()

        last_step = time.perf_counter()
        max_waits = 1 / self.rate

        while bg_worker.is_alive():
            delta = time.perf_counter() - last_step
            time.sleep(max_waits - delta)
            update_visible_icon(next(icons))
            live.refresh()
            last_step = time.perf_counter()

        self._marker = None
