from __future__ import annotations

import time

from promptique import Menu
from promptique.prompts import Note, Select, Spinner


def background_work():
    time.sleep(5)


def main() -> int:
    """ """
    menu = Menu(intro="Welcome.", outro="Smell ya later.")
    menu.add(Note(prompt="Hello, world!", detail="here's some information~", on_screen_time=2))
    menu.add(Select(prompt="Choose wisely", choices=["A", "B", "C", "D", "E", "F", "G"], mode="SINGLE"))
    menu.add(Spinner(prompt="This is a background task.", rate=10.0, background=background_work))
    menu.run()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
