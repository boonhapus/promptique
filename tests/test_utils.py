from __future__ import annotations

from typing import Callable
import functools as ft

import pytest

from promptique._utils import count_parameters


class TestDummy:
    def only_keyword_arguments(self, *, a, b, c):
        pass

    def only_positional_arguments(self, a, b, c):
        pass

    def mixed_arguments(self, a, *, b, c):
        pass

    @staticmethod
    def no_instance_method(a, b, c):
        pass


@pytest.mark.parametrize(
    "fn,n_parameters",
    [
        (lambda: None, 0),
        (TestDummy().only_keyword_arguments, 0),
        (TestDummy().only_positional_arguments, 3),
        (TestDummy().mixed_arguments, 1),
        (TestDummy().no_instance_method, 3),
        (ft.partial(TestDummy().no_instance_method), 3),
    ],
)
def test_count_parameters_always_2(fn: Callable, n_parameters: int):
    assert count_parameters(fn) == n_parameters
