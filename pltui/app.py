import os
from typing import Optional

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Input, Select
from textual.worker import get_current_worker

from pltui.components import AppFooter, AppHeader, StateInspector
from pltui.components.modals import ActionRunModal, ConfirmModal, ConfirmResult
from pltui.components.state import StateTree
from pltui.models import PulumiStack
from pltui.service import PulumiAction, PulumiService
from pltui.theme import PULUMI_SOFT_THEME, PULUMI_THEME


class PulumiTUI(App):
    CSS_PATH = "ui.tcss"
    COMMAND_PALETTE_BINDING = "ctrl+backslash"
    BINDINGS = [
        # Binding(
        #     "ctrl+l",
        #     "reload_state",
        #     description="Reload state",
        #     tooltip="Reload state for the selected stack.",
        #     id="reload-state",
        # ),
        Binding(
            "ctrl+r",
            "refresh_stack",
            description="Refresh",
            tooltip="Refresh the selected resources (whole stack if none selected)",
            id="refresh-stack",
        ),
        Binding(
            "ctrl+p",
            "preview_stack",
            description="Preview",
            tooltip="Preview changes for the selected resources (whole stack if none selected)",
            id="preview-stack",
        ),
        Binding(
            "ctrl+u",
            "up_stack",
            description="Up",
            tooltip="Deploy the selected resources (whole stack if none selected)",
            id="up-stack",
        ),
        Binding(
            "ctrl+d",
            "delete_state_resources",
            description="Delete",
            tooltip="Delete the selected resources from the Pulumi state only",
            id="delete-state-resources",
        ),
        Binding(
            "ctrl+l",
            "protect_resources",
            description="Protect",
            tooltip="Protect the selected resources (needs an unprotected one selected)",
            id="protect-resources",
        ),
        Binding(
            "ctrl+o",
            "unprotect_resources",
            description="Unprotect",
            tooltip="Unprotect the selected resources (needs a protected one selected)",
            id="unprotect-resources",
        ),
        Binding(
            "ctrl+x",
            "destroy_resources",
            description="Destroy",
            tooltip="Destroy the selected resources (whole stack if none selected)",
            id="destroy-resources",
        ),
        # Binding(
        #     "/",
        #     "focus_search",
        #     description="Focus search",
        #     tooltip="Focus the resource search input.",
        #     id="focus-search",
        # ),
    ]

    pulumi_service: PulumiService

    project_name: reactive[str] = reactive("")
    stacks: reactive[list[str]] = reactive(list)
    stack_name: reactive[Optional[str]] = reactive(None)
    # Resources compare by URN only, so a reloaded state would look unchanged.
    state: reactive[Optional[PulumiStack]] = reactive(None, always_update=True)

    def __init__(self, project_dir: str | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.project_dir = project_dir or os.getcwd()
        self.register_theme(PULUMI_THEME)
        self.register_theme(PULUMI_SOFT_THEME)
        self.theme = PULUMI_THEME.name
        self.pulumi_service = PulumiService()

    def compose(self) -> ComposeResult:
        yield AppHeader(id="header")
        yield StateInspector().data_bind(PulumiTUI.state)
        yield AppFooter(id="footer")

    def on_mount(self) -> None:
        self._initialize_service()
        self.action_reload_stacks()

    def _initialize_service(self) -> bool:
        try:
            self.pulumi_service.setup(self.project_dir)
            project_name = self.pulumi_service.project_name
        except Exception as exc:
            self.query_one(AppFooter).set_status("Workspace unavailable")
            self.notify(
                f"Cannot load Pulumi project at {self.project_dir}: {exc!s}. "
                "Use -C/--cwd to choose a Pulumi project and Ctrl+R to retry.",
                title="Workspace unavailable",
                severity="error",
                markup=False,
            )
            return False
        self.query_one(AppHeader).project_name = project_name
        return True

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
        if self.pulumi_service is None:
            self.call_from_thread(
                self.handle_state_load_error,
                stack_name,
                "No Pulumi workspace initialized.",
            )
            return
        try:
            state = self.pulumi_service.get_state()
        except Exception as exc:
            if not worker.is_cancelled:
                self.call_from_thread(
                    self.handle_state_load_error, stack_name, str(exc)
                )
            return

        if not worker.is_cancelled:
            self.call_from_thread(self.set_state, state)

    def action_reload_stacks(self) -> None:
        """Reload the list of stacks."""
        self.query_one(AppFooter).set_status("Loading stacks")
        self.update_stacks()

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id != "header-stack":
            return
        event.stop()
        if (
            isinstance(event.value, str)
            and event.value in self.stacks
            and event.value == event.select.value
        ):
            self.stack_name = event.value

    def action_reload_state(self) -> None:
        if not self.stack_name:
            self.notify(
                "No stack selected.",
                title="Reload state",
                severity="warning",
            )
            return

        self.query_one(AppFooter).set_status("Loading state")
        self.load_state(self.stack_name)

    def action_refresh_stack(self) -> None:
        self._run_action(PulumiAction.REFRESH)

    def action_preview_stack(self) -> None:
        self._run_action(PulumiAction.PREVIEW)

    def action_up_stack(self) -> None:
        self._run_action(PulumiAction.UP)

    def action_destroy_resources(self) -> None:
        self._run_action(PulumiAction.DESTROY)

    def action_delete_state_resources(self) -> None:
        self._run_action(PulumiAction.STATE_DELETE)

    def action_protect_resources(self) -> None:
        self._run_action(PulumiAction.PROTECT)

    def action_unprotect_resources(self) -> None:
        self._run_action(PulumiAction.UNPROTECT)

    def _eligible_resources(self, action: PulumiAction):
        """Selected resources the action would change."""
        resources = self.query_one(StateTree).selected_resources
        match action:
            case PulumiAction.PROTECT:
                return tuple(r for r in resources if not r.protect)
            case PulumiAction.UNPROTECT:
                return tuple(r for r in resources if r.protect)
            case _:
                return resources

    def _run_action(self, action: PulumiAction) -> None:
        if not self.stack_name:
            self.notify("No stack selected.", title=action.value, severity="warning")
            return

        resources = self._eligible_resources(action)
        if action.requires_targets and not resources:
            self.notify(
                {
                    PulumiAction.PROTECT: "Select at least one unprotected resource.",
                    PulumiAction.UNPROTECT: "Select at least one protected resource.",
                }.get(action, "Select at least one resource first."),
                title=action.value.capitalize(),
                severity="warning",
            )
            return

        urns = tuple(resource.urn for resource in resources)
        scope = f"{len(urns)} selected resource(s)" if urns else "ALL"
        title = f"pulumi {action.value} - Stack '{self.stack_name}' - {scope}"

        def start() -> None:
            self.push_screen(
                ActionRunModal(
                    self.pulumi_service,
                    action,
                    urns,
                    title,
                    preview_only=action is PulumiAction.PREVIEW,
                ),
                lambda applied: self._action_finished(action, bool(applied)),
            )

        if not action.requires_targets:
            start()
            return

        # State edits have no preview, so list exactly what will change.
        listing = "\n".join(f"- {r.type}: {r.name}" for r in resources)
        verb = {
            PulumiAction.STATE_DELETE: "Remove {} from the Pulumi state",
            PulumiAction.PROTECT: "Protect {}",
            PulumiAction.UNPROTECT: "Unprotect {}",
        }[action].format(scope)
        message = f"{verb}?\n\n{listing}\n\n"
        is_delete = action is PulumiAction.STATE_DELETE

        def confirmed(result: ConfirmResult | None) -> None:
            if result and result.confirmed:
                self.push_screen(
                    ActionRunModal(
                        self.pulumi_service,
                        action,
                        urns,
                        title,
                        target_dependents=bool(result.target_dependents),
                    ),
                    lambda applied: self._action_finished(action, bool(applied)),
                )

        self.push_screen(
            ConfirmModal(
                f"Confirm {action.value}",
                message,
                "Delete" if is_delete else action.value.split()[-1].capitalize(),
                target_dependents=True if is_delete else None,
            ),
            confirmed,
        )

    def _action_finished(self, action: PulumiAction, success: bool) -> None:
        if success and action.mutates_state:
            self.action_reload_state()

    def action_focus_search(self) -> None:
        self.query_one("#state-search", Input).focus()

    def set_stacks(self, stacks: list[str]) -> None:
        self.stacks = sorted(stacks)
        footer = self.query_one(AppFooter)
        if not self.stacks:
            self.stack_name = None
            self.state = None
            self.query_one(AppHeader).set_stacks(self.stacks, self.stack_name)
            footer.set_status("No stacks")
            self.notify(
                "No stacks found for this project.",
                title="Stacks",
                severity="warning",
            )
            return

        selected_stack = (
            self.stack_name if self.stack_name in self.stacks else self.stacks[0]
        )
        self.query_one(AppHeader).set_stacks(self.stacks, selected_stack)
        if self.stack_name != selected_stack:
            self.stack_name = selected_stack
        else:
            footer.set_status("Ready")
        self.notify("Success!", title="Stacks loaded", severity="information")

    def watch_stack_name(self, stack_name: Optional[str]) -> None:
        if not stack_name:
            return

        self.pulumi_service.select_stack(stack_name)

        self.query_one(AppHeader).stack_name = stack_name
        footer = self.query_one(AppFooter)
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

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        match action:
            case "delete_state_resources":
                if isinstance(self.screen, ModalScreen) or not self.stack_name:
                    return None
                return True if self.query_one(StateTree).selecting else None
            case "protect_resources" | "unprotect_resources":
                if isinstance(self.screen, ModalScreen) or not self.stack_name:
                    return None
                action = (
                    PulumiAction.PROTECT
                    if action == "protect_resources"
                    else PulumiAction.UNPROTECT
                )
                return True if self._eligible_resources(action) else None
            case "refresh_stack" | "preview_stack" | "up_stack" | "destroy_resources":
                if isinstance(self.screen, ModalScreen):
                    return None
                return True if self.stack_name else None
            case "focus_search" | "reload_state":
                return True if self.stack_name else None
            case _:
                return True

    def on_state_tree_selection_changed(self) -> None:
        self.refresh_bindings()
