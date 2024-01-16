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

    def interactivity(self, live: Live) -> None:
        """Optionally give the User some time to read."""
        stepper = it.cycle(self.icons)
        last_step = time.perf_counter()

        if self.location == "MARKER":
            set_placement = ft.partial(setattr, self, "_marker")

        if self.location == "DETAIL":
            set_placement = ft.partial(setattr, self, "detail")

        set_placement(next(stepper))

        thread = threading.Thread(target=self.background)
        thread.start()

        while thread.is_alive():
            delta = time.perf_counter() - last_step

            if delta <= (1 / self.rate):
                time.sleep((1 / self.rate) - delta)
                set_placement(next(stepper))
                live.refresh()
                last_step = time.perf_counter()

        self._marker = None
