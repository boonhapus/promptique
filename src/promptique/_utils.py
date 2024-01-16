from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Callable, Optional
import functools as ft
import inspect

from rich.console import Console, Group, RenderableType
from rich.segment import Segment


def count_parameters(func: Callable) -> int:
    """Count the number of parameters in a callable."""
    if isinstance(func, ft.partial):
        return _count_parameters(func.func) + len(func.args)

    if hasattr(func, "__self__"):
        # Bound method
        func = func.__func__  # type: ignore
        return _count_parameters(func) - 1

    return _count_parameters(func)


@ft.lru_cache(maxsize=2048)
def _count_parameters(func: Callable) -> int:
    """Count the number of positional parameters in a callable."""
    parameters: Iterable[inspect.Parameter] = inspect.signature(func).parameters.values()
    return sum(p.kind != inspect.Parameter.KEYWORD_ONLY for p in parameters)


async def invoke(function: Callable[[Any], Any], *params) -> Any:
    """Invoke a function on the event loop."""
    parameter_count = count_parameters(function)
    result = function(*params[:parameter_count])

    if inspect.isawaitable(result):
        result = await result

    return result


def reshape_and_measure(
    *renderables: RenderableType,
    console: Console,
    max_width: Optional[int] = None,
) -> tuple[int, int]:
    """Gather and reshape renderables to meet the max width of the console."""
    options = console.options

    if max_width is not None:
        options = options.update(max_width=max_width)

    group = Group(*renderables)
    lines = console.render_lines(group, options, pad=False)
    shape = Segment.get_shape(lines)
    return shape


def fake_scroll(renderables: Iterable[RenderableType], *, console: Console, overage: int) -> Iterable[RenderableType]:
    """Simulate scrolling of a renderable."""
    trimmed = []

    for lines in renderables:
        width, height = reshape_and_measure(lines, console=console)
        overage = overage - height

        if overage >= -1:
            continue

        trimmed.append(lines)

    return trimmed
