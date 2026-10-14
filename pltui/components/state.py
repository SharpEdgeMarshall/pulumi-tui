from typing import Optional, cast

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import (
    Grid,
    Horizontal,
    HorizontalGroup,
    Vertical,
    VerticalScroll,
)
from textual.message import Message
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Footer,
    Input,
    Label,
    OptionList,
    Pretty,
    Static,
    Tree,
)
from textual.widgets.tree import TreeNode

from pltui.models import PulumiResource, PulumiStack


class ResourceDetails(ModalScreen):

    BINDINGS = [
        Binding("ctrl+r", "raw_view", "Raw view"),
        Binding("escape", "dismiss(True)", "Close"),
    ]

    def __init__(self, resource: PulumiResource, name=None, id=None, classes=None):
        super().__init__(name, id, classes)
        self.resource = resource

    def compose(self) -> ComposeResult:
        with Vertical():
            with VerticalScroll():
                yield Label("Resource Details", id="resource-details-label")
                yield Pretty(self.resource, id="resource-details-pretty")
        yield Footer()


class StateSearchInput(Input):
    pass


class StateTree(Tree[PulumiResource]):

    state: reactive[PulumiStack | None] = reactive(None)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.show_root = False
        self.guide_depth = 3
        self.root.data = None

    def watch_state(self, state: PulumiStack | None) -> None:
        self.loading = True
        if state:
            self.load_tree(self.root, state.root_resources)
        self.loading = False

    def load_tree(self, parent_node: TreeNode, resources: list[PulumiResource]) -> None:
        for resource in resources:
            if resource.children:
                resource_node = parent_node.add(f"{resource.type} ({resource.name})")
                resource_node.data = resource
                self.load_tree(resource_node, resource.children)
            else:
                resource_node = parent_node.add_leaf(
                    f"{resource.type} ({resource.name})"
                )
                resource_node.data = resource


class StateInspector(Vertical):

    state: reactive[PulumiStack | None] = reactive(None)

    DEFAULT_CSS = """

    """

    def compose(self):
        yield StateSearchInput(placeholder="Search resources...", id="state-search")
        with Horizontal():
            yield StateTree(
                label="Root",
                id="state-tree",
            ).data_bind(StateInspector.state)

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        if not event.node.data:
            return

        self.app.push_screen(ResourceDetails(event.node.data))
