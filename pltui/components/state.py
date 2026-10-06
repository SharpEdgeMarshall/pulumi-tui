from __future__ import annotations

import json
from difflib import unified_diff

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Grid, Horizontal, Vertical
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Footer,
    Input,
    Label,
    RichLog,
    Select,
    Static,
    Tab,
    Tabs,
    Tree,
)
from textual.widgets.tree import TreeNode

from pltui.models import PulumiResource, PulumiStack


class ResourceDetails(ModalScreen[None]):
    current_view: reactive[str] = reactive("overview")

    BINDINGS = [
        Binding("escape", "dismiss(None)", "Close"),
        Binding("v", "show_overview", "Overview"),
        Binding("i", "show_inputs", "Inputs"),
        Binding("o", "show_outputs", "Outputs"),
        Binding("d", "show_diff", "Diff"),
    ]

    def __init__(self, resource: PulumiResource, name=None, id=None, classes=None):
        super().__init__(name, id, classes)
        self.resource = resource
        self.inputs_payload = self._pretty_json(self.resource.inputs)
        self.outputs_payload = self._pretty_json(self.resource.properties)
        self.diff_payload: str | None = None

    def _pretty_json(self, payload: object) -> str:
        return json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            default=str,
        )

    def _build_diff(self) -> str:
        diff_lines = list(
            unified_diff(
                self.inputs_payload.splitlines(),
                self.outputs_payload.splitlines(),
                fromfile="inputs",
                tofile="outputs",
                lineterm="",
            )
        )
        if not diff_lines:
            return "No differences between inputs and outputs."
        return "\n".join(diff_lines)

    def compose(self) -> ComposeResult:
        with Vertical(id="resource-details"):
            yield Label(
                self.resource.name, id="resource-details-label", markup=False
            )
            yield Tabs(
                Tab("Overview", id="overview"),
                Tab("Inputs", id="inputs"),
                Tab("Outputs", id="outputs"),
                Tab("Diff", id="diff"),
                active=self.current_view,
                id="resource-view-tabs",
            )
            with Grid(id="resource-summary"):
                yield Static("Name", classes="summary-key")
                yield Static(self.resource.name, classes="summary-value")
                yield Static("Type", classes="summary-key")
                yield Static(self.resource.type, classes="summary-value")
                yield Static("ID", classes="summary-key")
                yield Static(self.resource.id or "-", classes="summary-value")
                yield Static("URN", classes="summary-key")
                yield Static(self.resource.urn, classes="summary-value")
                yield Static("Parent URN", classes="summary-key")
                yield Static(self.resource.parent_urn or "-", classes="summary-value")
                yield Static("Dependencies", classes="summary-key")
                yield Static(
                    str(len(self.resource.dependencies)), classes="summary-value"
                )
                yield Static("Modified", classes="summary-key")
                yield Static(
                    (
                        self.resource.modified.isoformat()
                        if self.resource.modified
                        else "-"
                    ),
                    classes="summary-value",
                )
                yield Static("Source", classes="summary-key")
                yield Static(
                    self.resource.sourcePosition or "-", classes="summary-value"
                )
            yield RichLog(
                id="resource-payload",
                wrap=False,
                auto_scroll=False,
                markup=False,
                highlight=False,
            )
        yield Footer()

    def on_mount(self) -> None:
        self._render_payload()

    def action_show_overview(self) -> None:
        self.current_view = "overview"

    def action_show_inputs(self) -> None:
        self.current_view = "inputs"

    def action_show_outputs(self) -> None:
        self.current_view = "outputs"

    def action_show_diff(self) -> None:
        self.current_view = "diff"

    def on_tabs_tab_activated(self, event: Tabs.TabActivated) -> None:
        if event.tabs.id == "resource-view-tabs":
            event.stop()
            if event.tab.id in {"overview", "inputs", "outputs", "diff"}:
                self.current_view = event.tab.id

    def watch_current_view(self, current_view: str) -> None:
        if self.is_mounted:
            self.query_one("#resource-view-tabs", Tabs).active = current_view
            self._render_payload()

    def _render_payload(self) -> None:
        overview = self.current_view == "overview"
        self.query_one("#resource-summary", Grid).display = overview
        payload_view = self.query_one("#resource-payload", RichLog)
        payload_view.display = not overview
        if overview:
            return
        payload_view.clear()

        if self.current_view == "inputs":
            payload_view.write(self.inputs_payload)
            return

        if self.current_view == "outputs":
            payload_view.write(self.outputs_payload)
            return

        if self.diff_payload is None:
            self.diff_payload = self._build_diff()
        payload_view.write(self.diff_payload)


class StateSearchInput(Input):
    pass


class StateTree(Tree[PulumiResource]):

    state: reactive[PulumiStack | None] = reactive(None)
    query: reactive[str] = reactive("")
    resource_type: reactive[str] = reactive("")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.show_root = False
        self.guide_depth = 3
        self.root.data = None

    def watch_state(self, state: PulumiStack | None) -> None:
        self.rebuild_tree()

    def watch_query(self, query: str) -> None:
        self.rebuild_tree()

    def watch_resource_type(self, resource_type: str) -> None:
        self.rebuild_tree()

    def rebuild_tree(self) -> None:
        self.loading = True
        self.clear()
        query = self.query.strip()
        resources = self.state.resources_by_urn.values() if self.state else ()
        total = len(self.state.resources_by_urn) if self.state else 0
        matching = sum(
            self._matches_filters(resource, query, self.resource_type)
            for resource in resources
        )
        self.border_title = (
            f"Resources: {matching} of {total}"
            if query or self.resource_type else f"Resources: {total}"
        )
        if self.state:
            self.load_tree(
                self.root, self.state.root_resources, query, self.resource_type
            )
            self.root.expand()
        self.loading = False

    def _matches_query(self, resource: PulumiResource, query: str) -> bool:
        q = query.lower()
        target = " ".join(
            [
                resource.type,
                resource.name,
                resource.urn,
                resource.id or "",
                resource.parent_urn or "",
            ]
        ).lower()
        return q in target

    def _matches_filters(
        self, resource: PulumiResource, query: str, resource_type: str = ""
    ) -> bool:
        return (
            (not resource_type or resource.type == resource_type)
            and (not query or self._matches_query(resource, query))
        )

    def _should_include(
        self, resource: PulumiResource, query: str, resource_type: str = ""
    ) -> bool:
        if self._matches_filters(resource, query, resource_type):
            return True
        return any(
            self._should_include(child, query, resource_type)
            for child in resource.children
        )

    def load_tree(
        self,
        parent_node: TreeNode[PulumiResource],
        resources: list[PulumiResource],
        query: str,
        resource_type: str = "",
    ) -> None:
        for resource in resources:
            if not self._should_include(resource, query, resource_type):
                continue

            label = f"{resource.type} ({resource.name})"
            matching_children = [
                child
                for child in resource.children
                if self._should_include(child, query, resource_type)
            ]

            if matching_children:
                resource_node = parent_node.add(
                    label, expand=bool(query or resource_type)
                )
                resource_node.data = resource
                self.load_tree(resource_node, matching_children, query, resource_type)
            else:
                resource_node = parent_node.add_leaf(label)
                resource_node.data = resource


class StateInspector(Vertical):

    state: reactive[PulumiStack | None] = reactive(None)
    filters_expanded: reactive[bool] = reactive(False)

    DEFAULT_CSS = """

    """

    def compose(self):
        with Horizontal(id="state-filters"):
            yield StateSearchInput(placeholder="Search resources...", id="state-search")
            yield Button(
                "▶ Filters",
                id="toggle-filters",
                tooltip="Show or hide resource filters",
            )
        with Vertical(id="state-filter-panel"):
            yield Label("Resource type", id="state-type-label")
            yield Select(
                [("All resource types", "")],
                allow_blank=False,
                value="",
                id="state-type-filter",
            )
        with Horizontal(id="state-tree-container"):
            yield StateTree(
                label="Root",
                id="state-tree",
            ).data_bind(StateInspector.state)

    def on_mount(self) -> None:
        self._update_resource_types()
        self._render_filter_panel()

    def watch_filters_expanded(self, expanded: bool) -> None:
        if self.is_mounted:
            self._render_filter_panel()

    def _render_filter_panel(self) -> None:
        self.query_one("#state-filter-panel").set_class(
            self.filters_expanded, "-expanded"
        )
        selected = self.query_one("#state-type-filter", Select).value
        active_count = 1 if isinstance(selected, str) and selected else 0
        arrow = "▼" if self.filters_expanded else "▶"
        count = f" ({active_count})" if active_count else ""
        self.query_one("#toggle-filters", Button).label = f"{arrow} Filters{count}"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "toggle-filters":
            event.stop()
            self.filters_expanded = not self.filters_expanded

    def watch_state(self, state: PulumiStack | None) -> None:
        if self.is_mounted:
            self._update_resource_types()

    def _update_resource_types(self) -> None:
        type_filter = self.query_one("#state-type-filter", Select)
        selected = type_filter.value
        resource_types = sorted(
            {resource.type for resource in self.state.resources_by_urn.values()}
            if self.state else set()
        )
        resource_type = (
            selected if isinstance(selected, str) and selected in resource_types else ""
        )
        type_filter.set_options(
            [("All resource types", ""), *((kind, kind) for kind in resource_types)]
        )
        type_filter.value = resource_type
        self.query_one("#state-tree", StateTree).resource_type = resource_type
        self._render_filter_panel()

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "state-type-filter" and isinstance(event.value, str):
            self.query_one("#state-tree", StateTree).resource_type = event.value
            self._render_filter_panel()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != "state-search":
            return
        tree = self.query_one("#state-tree", StateTree)
        tree.query = event.value.strip()

    def action_focus_search(self) -> None:
        self.query_one("#state-search", StateSearchInput).focus()

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        if not event.node.data:
            return

        self.app.push_screen(ResourceDetails(event.node.data))
