from importlib.metadata import PackageNotFoundError, version

from textual.app import ComposeResult
from textual.containers import Grid, Vertical
from textual.reactive import reactive
from textual.widgets import Select, Static

try:
    APP_VERSION = version("pulumi-tui")
except PackageNotFoundError:
    APP_VERSION = "dev"


class AppHeader(Vertical):
    project_name: reactive[str | None] = reactive(None)
    stack_name: reactive[str | None] = reactive(None)

    DEFAULT_CSS = """
    AppHeader {
        dock: top;
        width: 100%;
        background: $panel;
        color: $foreground;
        height: 4;
    }
    """

    def compose(self) -> ComposeResult:
        with Grid(id="header-meta"):
            yield Static("Project", classes="header-key")
            yield Static(id="header-project", markup=False)
            yield Static("Stack", classes="header-key")
            yield Select(
                [("Loading stacks...", "loading")],
                allow_blank=False,
                value="loading",
                prompt="Loading stacks",
                id="header-stack",
                compact=True,
                disabled=True,
            )

    def on_mount(self) -> None:
        self.border_title = f"PLTUI v{APP_VERSION}"
        self._render_project_name(self.project_name)
        self._render_stack_name(self.stack_name)

    def watch_project_name(self, project_name: str | None) -> None:
        self._render_project_name(project_name)

    def watch_stack_name(self, stack_name: str | None) -> None:
        self._render_stack_name(stack_name)

    def _render_project_name(self, project_name: str | None) -> None:
        if not self.is_mounted:
            return
        self.query_one("#header-project", Static).update(project_name or "-")

    def _render_stack_name(self, stack_name: str | None) -> None:
        if not self.is_mounted:
            return
        self.query_one("#header-stack", Select).value = (
            stack_name if stack_name is not None else ""
        )

    def set_stacks(self, stacks: list[str], current: str | None) -> None:
        selector = self.query_one("#header-stack", Select)
        selector.set_options(
            [(stack, stack) for stack in stacks] or [("No stacks available", "")]
        )
        selector.disabled = not stacks
        selector.value = current if current in stacks else stacks[0] if stacks else ""
