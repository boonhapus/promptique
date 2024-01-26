from __future__ import annotations

import time

import rich

from promptique import Menu
from promptique.prompts import FileInput, Note, Select, Spinner, UserInput
from promptique.prompts.select import PromptOption


def main() -> int:
    """Create a new Code Repository."""
    rich.print("\n")

    prompts = [
        UserInput(id="name", prompt="Repository name", detail="Great repository names are short and memorable."),
        FileInput(id="root", prompt="Where should we create your new project?", path_type="DIRECTORY", exists=False),
        Select(id="privacy", prompt="Which type of Privacy?", mode="SINGLE", choices=["Public", "Private"]),
        Select(
            id="extras",
            prompt="Initialize this repository with..",
            mode="MULTI",
            choices=[
                PromptOption(
                    text="README.md",
                    description="This is where you can write a long description for your project",
                ),
                PromptOption(
                    text=".gitignore",
                    description="Choose which files not to track from a list of templates",
                ),
                PromptOption(
                    text="LICENSE",
                    description="A license tells others what they can and can't do with your code",
                    is_selected=True,
                ),
            ],
        ),
        Spinner(prompt="Creating your repository.", rate=5, background=lambda: time.sleep(3)),
        # Note(),
    ]

    menu = Menu(*prompts, intro="New Repository", outro="Repository setup is complete!")
    menu["extras"].link(Note(prompt="IGNORE"), validator=lambda ctx: any(o.text == ".gitignore" for o in ctx.response))
    menu["extras"].link(Note(prompt="README"), validator=lambda ctx: any(o.text == "README.md" for o in ctx.response))
    menu["extras"].link(Note(prompt="LICENSE"), validator=lambda ctx: any(o.text == "LICENSE" for o in ctx.response))
    menu.run()

    # Print out all the answers.
    rich.print("\n", {prompt.id: prompt._response for prompt in menu.prompts}, "\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
