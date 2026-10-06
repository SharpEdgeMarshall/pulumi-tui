from typing import Optional

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
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
            Text(f"Select stack to switch to ({len(self.stacks)} available):\n", "bold"),
            id="question",
        )
        options = OptionList(*self.stacks, id="stacks-list")
        if self.current and self.current in self.stacks:
            options.highlighted = self.stacks.index(self.current)
        yield Vertical(
            question,
            options,
            Button("OK", id="ok"),
            id="stacks",
        )

    def action_refresh_stacks(self) -> None:
        self.app.action_refresh_stacks()
        self.dismiss(None)

    def on_key(self, event) -> None:
        options = self.query_one("#stacks-list", OptionList)

        if event.key == "enter" and options.highlighted is not None:
            self.dismiss(self.stacks[options.highlighted])
        elif event.key == "escape":
            self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id != "ok":
            return

        options = self.query_one("#stacks-list", OptionList)
        if options.highlighted is None:
            self.dismiss(None)
            return

        self.dismiss(self.stacks[options.highlighted])
