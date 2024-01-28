from __future__ import annotations

from typing import TYPE_CHECKING
import time

import pydantic
import rich

from promptique import Menu
from promptique.prompts import Confirm, Note, Select, Spinner, UserInput

if TYPE_CHECKING:
    from promptique.validation import ResponseContext


def _sim_sync_work() -> None:
    """Simulate doing some work."""
    time.sleep(3)


def _is_valid_cc_number(ctx: ResponseContext) -> bool:
    """Determine if the credit information is valid."""
    try:
        pydantic.PaymentCardNumber.validate_digits(ctx.response.replace("-", ""))
    except Exception as e:
        raise AssertionError(e) from None

    return True


def main() -> int:
    """Order a pizza."""
    rich.print("\n")

    prompts = [
        Select(
            id="size",
            prompt="Select your pizza size",
            choices={"P": "Personal", "S": "Small", "M": "Medium", "L": "Large", "X": "X-Large"},
            mode="SINGLE",
        ),
        Confirm(id="cheese", prompt="Do you want extra cheese?", default="No"),
        Select(
            id="toppings",
            prompt="Select your pizza size",
            choices=["Pepperoni", "Sausage", "Ham", "Chicken", "Bell Peppers", "Onion", "Pineapple"],
            mode="MULTI",
        ),
        UserInput(
            id="credit_card",
            prompt="What's your credit card number?",
            detail="Format: XXXX-XXXX-XXX-XXXX",
            prefill="3742-4545-540-0126",
            input_validator=_is_valid_cc_number,
        ),
        Spinner(
            prompt="Building your pizza",
            detail="and sending it to the store!",
            rate=5,
            background=_sim_sync_work,
            transient=True,
        ),
    ]

    menu = Menu(*prompts, intro=":pizza: Welcome to the Pyzza Shop! :pizza:", outro="Your order will be there soon!")
    menu.add(Note(prompt=":car: Get ready for some goodness. :tada:", on_screen_time=1))
    menu.run()

    # Print out all the answers.
    rich.print("\n", {prompt.id: prompt._response for prompt in menu.prompts}, "\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
