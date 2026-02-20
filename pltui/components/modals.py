from typing import Optional

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Grid, Horizontal, Vertical
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import Button, OptionList, Static


class StackSelectModal(ModalScreen[str | None]):
    stacks: list[str] = []
    current: Optional[str] = None

    BINDINGS = [Binding("ctrl+r", "refresh_stacks", "Refresh stacks")]

    def __init__(self, stacks: list[str], current: Optional[str], *args, **kwargs):
        self.current = current
        self.stacks = stacks
        super().__init__(*args, **kwargs)

    def compose(self) -> ComposeResult:
        question = Static(
            Text("Select stack to switch to:\n", "bold"),
            id="question",
        )
        options = OptionList(*self.stacks, id="stacks-list")
        if self.current:
            options.highlighted = self.stacks.index(self.current)
        yield Vertical(
            question,
            options,
            Button("OK", id="ok"),
            id="stacks",
        )

    def on_key(self, event) -> None:
        options = self.query_one("#stacks-list", OptionList)

        if event.key == "enter" and options.highlighted is not None:
            self.dismiss(self.stacks[options.highlighted])
        elif event.key == "escape":
            self.dismiss(None)
