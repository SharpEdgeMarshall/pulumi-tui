import os
from importlib.metadata import version

from pulumi.automation import LocalWorkspace
from textual.containers import HorizontalGroup, Vertical
from textual.reactive import reactive
from textual.widgets import Label, Static


class AppHeader(HorizontalGroup):
    LOGO = r""" ______   __         ______   __  __     __    
/\  == \ /\ \       /\__  _\ /\ \/\ \   /\ \   
\ \  _-/ \ \ \____  \/_/\ \/ \ \ \_\ \  \ \ \  
 \ \_\    \ \_____\    \ \_\  \ \_____\  \ \_\ 
  \/_/     \/_____/     \/_/   \/_____/   \/_/ 
"""

    BORDER_TITLE = "PLTUI"
    BORDER_SUBTITLE = f"the Pulumi terminal user interface - {version('pltui')}"

    project_name: reactive[str | None] = reactive(None)
    stack_name: reactive[str | None] = reactive(None)

    DEFAULT_CSS = """
    AppHeader {
        dock: top;
        width: 100%;
        background: $panel;
        color: $foreground;
        height: 1;
    }
    """

    def compose(self):

        with Vertical(classes="header-box"):
            yield Static(id="project-name")
            yield Static(id="stack-name")

        yield Static(self.LOGO, classes="header-box", id="logo-box")

    def on_mount(self) -> None:
        self.query_one("#project-name", Static).update(f"Project: {self.project_name}")
        self.query_one("#stack-name", Static).update(f"Stack: {self.stack_name}")

    def watch_project_name(self, project_name: str) -> None:
        self.query_one("#project-name", Static).update(f"Project: {project_name}")

    def watch_stack_name(self, stack_name: str) -> None:
        self.query_one("#stack-name", Static).update(f"Stack: {stack_name}")
