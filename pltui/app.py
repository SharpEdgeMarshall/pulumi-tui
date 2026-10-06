import os
from typing import Optional

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.widgets import Input
from textual.worker import get_current_worker

from pltui.components import AppHeader, StackSelectModal, StateInspector, AppFooter
from pltui.models import PulumiStack
from pltui.service import PulumiFakeService, PulumiService, StateService
from pltui.theme import PULUMI_SOFT_THEME


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
            "ctrl+l",
            "refresh_state",
            description="Refresh state",
            tooltip="Reload state for the selected stack.",
            id="refresh-state",
        ),
        Binding(
            "/",
            "focus_search",
            description="Focus search",
            tooltip="Focus the resource search input.",
            id="focus-search",
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
    use_fake_data: bool = False

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.register_theme(PULUMI_SOFT_THEME)
        self.theme = PULUMI_SOFT_THEME.name

    def compose(self) -> ComposeResult:
        yield AppHeader(id="header")
        yield StateInspector().data_bind(PulumiTUI.state)
        yield AppFooter(id="footer")

    def on_mount(self) -> None:
        header = self.query_one(AppHeader)
        self.pulumi_service = self._build_service()
        header.project_name = self.pulumi_service.project_name
        self.action_refresh_stacks()

    def _build_service(self) -> StateService:
        fake_requested = os.getenv("PLTUI_FAKE_STATE", "").lower() in {
            "1",
            "true",
            "yes",
        }

        if fake_requested:
            self.use_fake_data = True
            return PulumiFakeService()

        project_dir = os.getenv("PLTUI_PROJECT_DIR")
        try:
            service = PulumiService(project_dir=project_dir or os.getcwd())
            _ = service.project_name
            return service
        except Exception as exc:
            self.use_fake_data = True
            self.notify(
                f"Pulumi workspace unavailable ({exc!s}). Falling back to state.json.",
                title="Fallback mode",
                severity="warning",
            )
            return PulumiFakeService()

    @work(exclusive=True, thread=True)
    async def update_stacks(self) -> None:
        worker = get_current_worker()
        try:
            stack_names = self.pulumi_service.list_stacks()
        except Exception as exc:
            if not worker.is_cancelled:
                self.call_from_thread(self.handle_stack_load_error, str(exc))
            return

        if not worker.is_cancelled:
            self.call_from_thread(self.set_stacks, stack_names)

    @work(exclusive=True, thread=True)
    async def load_state(self, stack_name: str) -> None:
        worker = get_current_worker()
        try:
            state = self.pulumi_service.get_state(stack_name)
        except Exception as exc:
            if not worker.is_cancelled:
                self.call_from_thread(self.handle_state_load_error, stack_name, str(exc))
            return

        if not worker.is_cancelled:
            self.call_from_thread(self.set_state, state)

    def action_refresh_stacks(self) -> None:
        """Refresh the list of stacks."""
        self.query_one(AppFooter).set_status("Loading stacks")
        self.update_stacks()

    def action_select_stack(self) -> None:
        if not self.stacks:
            self.notify(
                "No stacks available. Try Ctrl+R after selecting a Pulumi project.",
                title="No stacks",
                severity="warning",
            )
            return

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

    def action_refresh_state(self) -> None:
        if not self.stack_name:
            self.notify(
                "No stack selected.",
                title="Refresh state",
                severity="warning",
            )
            return

        self.query_one(AppFooter).set_status("Loading state")
        self.load_state(self.stack_name)

    def action_focus_search(self) -> None:
        self.query_one("#state-search", Input).focus()

    def set_stacks(self, stacks: list[str]) -> None:
        self.stacks = sorted(stacks)
        footer = self.query_one(AppFooter)
        if not self.stacks:
            self.stack_name = None
            footer.set_status("No stacks")
            self.notify(
                "No stacks found for this project.",
                title="Stacks",
                severity="warning",
            )
            return

        if self.stack_name not in self.stacks:
            self.stack_name = self.stacks[0]
        else:
            footer.set_status("Ready")
        self.notify("Success!", title="Stacks loaded", severity="information")

    def watch_stack_name(self, stack_name: Optional[str]) -> None:
        if not stack_name:
            return
        header = self.query_one(AppHeader)
        footer = self.query_one(AppFooter)
        header.stack_name = stack_name
        footer.set_status("Loading state")
        self.load_state(stack_name)

    def set_state(self, state: PulumiStack) -> None:
        self.state = state
        footer = self.query_one(AppFooter)
        footer.set_status("Ready")
        self.notify("Success!", title="Stack loaded", severity="information")

    def handle_stack_load_error(self, error: str) -> None:
        self.query_one(AppFooter).set_status("Error loading stacks")
        self.notify(
            error,
            title="Failed to load stacks",
            severity="error",
        )

    def handle_state_load_error(self, stack_name: str, error: str) -> None:
        self.query_one(AppFooter).set_status("Error loading state")
        self.notify(
            f"Unable to load state for '{stack_name}': {error}",
            title="State error",
            severity="error",
        )
