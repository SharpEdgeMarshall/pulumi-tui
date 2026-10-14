import importlib.metadata
import os
from sre_parse import State
from typing import Optional

from textual import work
from textual.app import App
from textual.binding import Binding
from textual.events import Key
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import ContentSwitcher, Footer, Input, OptionList
from textual.widgets import RichLog as TextLog
from textual.widgets import Static, Tree
from textual.worker import get_current_worker

from pltui.components import AppHeader, StackSelectModal, StateInspector
from pltui.models import PulumiStack
from pltui.service import PulumiFakeService, PulumiService, StateService


class PulumiTUI(App):

    CSS_PATH = "ui.tcss"
    BINDINGS = [
        Binding(
            "ctrl+s",
            "select_stack",
            description="Select Stack",
            tooltip="Select the Pulumi Stack to work on.",
            id="select-stack",
        ),
        Binding(
            "ctrl+r",
            "refresh_stacks",
            description="Refresh Stacks list",
            tooltip="Refresh the Pulumi Stacks list.",
            id="refresh-stacks",
        ),
        Binding(
            "ctrl+c",
            "app.quit",
            description="Quit",
            tooltip="Quit the application.",
            priority=True,
            id="quit",
        ),
    ]

    pulumi_service: StateService

    project_name: reactive[str] = reactive("")
    stacks: reactive[list[str]] = reactive(list)
    stack_name: reactive[Optional[str]] = reactive(None)
    state: reactive[Optional[PulumiStack]] = reactive(None)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

    def compose(self):
        yield AppHeader(id="header")
        yield StateInspector().data_bind(PulumiTUI.state)
        yield Footer()

    def on_mount(self) -> None:
        header = self.query_one(AppHeader)
        self.pulumi_service = PulumiFakeService()
        header.project_name = self.pulumi_service.project_name
        self.state = self.pulumi_service.get_state("")
        print(f"Screen stack: {self.screen_stack}")

    @work(exclusive=True, thread=True)
    async def update_stacks(self) -> None:
        self.notify("Please wait...", title="Loading stacks", severity="information")
        worker = get_current_worker()
        stacks = self.pulumi_service.list_stacks()
        stack_names = [s.name for s in stacks]

        if not worker.is_cancelled:
            self.notify("Success!", title="Stacks loaded", severity="information")
            self.call_from_thread(self.set_stacks, stack_names)

    @work(exclusive=True, thread=True)
    async def load_state(self, stack_name: str) -> None:
        self.notify("Please wait...", title="Loading stack", severity="information")
        worker = get_current_worker()
        state = self.pulumi_service.get_state(stack_name)
        if not worker.is_cancelled:
            self.notify("Success!", title="Stack loaded", severity="information")
            self.call_from_thread(self.set_state, state)

    def action_refresh_stacks(self) -> None:
        """Refresh the list of stacks."""
        self.update_stacks()

    def action_select_stack(self) -> None:
        focused = self.focused

        def callback(stack_selected: str | None) -> None:
            if focused:
                self.screen.set_focus(focused)

            if stack_selected:
                self.stack_name = stack_selected

        self.set_focus(None)

        self.push_screen(
            StackSelectModal(
                stacks=self.stacks,
                current=self.stack_name,
            ),
            callback=callback,
        )

    def set_stacks(self, stacks: list[str]) -> None:
        self.stacks = stacks
        if not self.stack_name:
            self.action_select_stack()

    def watch_stack_name(self, stack_name: str) -> None:
        if not stack_name:
            return
        header = self.query_one(AppHeader)
        header.stack_name = stack_name
        self.load_state(stack_name)

    def set_state(self, state) -> None:
        self.state = state
