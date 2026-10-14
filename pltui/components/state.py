from __future__ import annotations

import json
from difflib import unified_diff

from rich.text import Text
from textual import events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Grid, Horizontal, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Checkbox,
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
from pltui.selection import ResourceSelection


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

    def on_click(self, event: events.Click) -> None:
        # Clicks inside the dialog are handled by its widgets, so a click that
        # lands on the screen itself is outside of it.
        if event.widget is self:
            self.dismiss(None)

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
            yield Label(self.resource.name, id="resource-details-label", markup=False)
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
                yield Static("Protected", classes="summary-key")
                yield Static(
                    "Yes" if self.resource.protect else "No", classes="summary-value"
                )
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

    BINDINGS = [
        Binding("space", "toggle_resource", "Select"),
        Binding("e", "expand_cursor", "Expand/collapse resource"),
        Binding("enter", "show_details", "View"),
    ]

    class DetailsRequested(Message):
        def __init__(self, resource: PulumiResource) -> None:
            super().__init__()
            self.resource = resource

    class SelectionChanged(Message):
        def __init__(
            self,
            selected_urns: frozenset[str],
            matching_urns: frozenset[str],
            selecting: bool,
        ) -> None:
            super().__init__()
            self.selected_urns = selected_urns
            self.matching_urns = matching_urns
            self.selecting = selecting

    state: reactive[PulumiStack | None] = reactive(None, always_update=True)
    search_query: reactive[str] = reactive("")
    resource_type: reactive[str] = reactive("")
    protected_only: reactive[bool] = reactive(False)

    def __init__(self, *args, **kwargs):
        self.selection = ResourceSelection()
        self.resource_nodes: dict[str, TreeNode[PulumiResource]] = {}
        super().__init__(*args, **kwargs)
        self.show_root = False
        self.auto_expand = False
        self.guide_depth = 3
        self.root.data = None

    @property
    def selecting(self) -> bool:
        """Multi-selection is active as soon as one resource is selected."""
        return bool(self.selection.urns)

    def watch_state(self, state: PulumiStack | None) -> None:
        self.rebuild_tree()

    def watch_search_query(self, query: str) -> None:
        self.rebuild_tree()

    def watch_resource_type(self, resource_type: str) -> None:
        self.rebuild_tree()

    def watch_protected_only(self, protected_only: bool) -> None:
        self.rebuild_tree()

    @property
    def matching_urns(self) -> frozenset[str]:
        if self.state is None:
            return frozenset()
        return frozenset(
            resource.urn
            for resource in self.state.resources_by_urn.values()
            if self._matches_filters(
                resource, self.search_query.strip(), self.resource_type
            )
        )

    @property
    def selected_resources(self) -> tuple[PulumiResource, ...]:
        if self.state is None:
            return ()
        return tuple(
            resource
            for urn, resource in self.state.resources_by_urn.items()
            if urn in self.selection.urns
        )

    def select_matching(self) -> None:
        self.selection.select(self.matching_urns)
        self._update_selection()

    def deselect_matching(self) -> None:
        self.selection.deselect(self.matching_urns)
        self._update_selection()

    def toggle_resource(self, resource: PulumiResource) -> None:
        if resource.urn not in self.matching_urns:
            self.notify(
                "This parent is shown for context and does not match the filters.",
                title="Resource selection",
            )
            return
        self.selection.toggle(resource.urn)
        self._update_selection()

    def action_toggle_resource(self) -> None:
        if self.cursor_node and self.cursor_node.data:
            self.toggle_resource(self.cursor_node.data)

    def action_show_details(self) -> None:
        if self.cursor_node and self.cursor_node.data:
            self.post_message(self.DetailsRequested(self.cursor_node.data))

    def on_click(self, event: events.Click) -> None:
        meta = event.style.meta
        if event.chain != 2 or "line" not in meta or meta.get("toggle", False):
            return
        node = self.get_node_at_line(meta["line"])
        if node is not None and node.data:
            event.stop()
            self.post_message(self.DetailsRequested(node.data))

    def action_expand_cursor(self) -> None:
        super().action_toggle_node()

    def _resource_label(self, resource: PulumiResource) -> Text:
        label = f"{resource.type} ({resource.name})"
        if resource.protect:
            lock = self.app.get_css_variables()["secondary"].removeprefix("ansi_")
            label = Text.assemble(label, (" 🔒", lock))
        else:
            label = Text(label)
        if not self.selecting:
            return label
        if not self._matches_filters(
            resource, self.search_query.strip(), self.resource_type
        ):
            return Text.assemble("    ", label)
        if resource.urn in self.selection.urns:
            color = self.app.get_css_variables()["secondary"].removeprefix("ansi_")
            return Text.assemble(("[x] ", f"bold {color}"), label)
        return Text.assemble("[ ] ", label)

    def _update_selection(self) -> None:
        matching_urns = self.matching_urns
        total = len(self.state.resources_by_urn) if self.state else 0
        title = (
            f"Resources: {len(matching_urns)} of {total}"
            if self.search_query.strip() or self.resource_type or self.protected_only
            else f"Resources: {total}"
        )
        if self.selecting:
            title += f" | Selected: {len(self.selection.urns)}"
            hidden = len(self.selection.urns - matching_urns)
            if hidden:
                title += f" ({hidden} hidden)"
        self.border_title = title
        for node in self.resource_nodes.values():
            if node.data is not None:
                node.set_label(self._resource_label(node.data))
        self.post_message(
            self.SelectionChanged(
                frozenset(self.selection.urns), matching_urns, self.selecting
            )
        )
        self.refresh_bindings()

    def rebuild_tree(self) -> None:
        self.loading = True
        self.clear()
        self.resource_nodes.clear()
        self.selection.reconcile(
            self.state.name if self.state else None,
            self.state.resources_by_urn if self.state else (),
        )
        query = self.search_query.strip()
        if self.state:
            self.load_tree(
                self.root, self.state.root_resources, query, self.resource_type
            )
            self.root.expand()
        self.loading = False
        self._update_selection()

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
            and (not self.protected_only or resource.protect)
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

            label = self._resource_label(resource)
            matching_children = [
                child
                for child in resource.children
                if self._should_include(child, query, resource_type)
            ]

            if matching_children:
                resource_node = parent_node.add(label, expand=True)
                resource_node.data = resource
                self.load_tree(resource_node, matching_children, query, resource_type)
            else:
                resource_node = parent_node.add_leaf(label)
                resource_node.data = resource
            self.resource_nodes[resource.urn] = resource_node


class StateInspector(Vertical):

    BINDINGS = [
        Binding("a", "select_all", "Select all"),
        Binding("d", "deselect_all", "Deselect all"),
    ]

    state: reactive[PulumiStack | None] = reactive(None, always_update=True)

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        # Mirrors the enabled state of the Select all / Deselect all buttons.
        if action not in {"select_all", "deselect_all"}:
            return True
        trees = self.query(StateTree)
        if not trees:
            return None
        tree = trees.first()
        if action == "select_all":
            return True if tree.matching_urns - tree.selection.urns else None
        return True if tree.matching_urns & tree.selection.urns else None

    def action_select_all(self) -> None:
        self.query_one(StateTree).select_matching()

    def action_deselect_all(self) -> None:
        self.query_one(StateTree).deselect_matching()

    def compose(self):
        with Horizontal(id="state-filters"):
            yield StateSearchInput(placeholder="Search resources...", id="state-search")
            yield Select(
                [("All resource types", "")],
                allow_blank=False,
                value="",
                id="state-type-filter",
                tooltip="Filter by resource type",
            )
            yield Checkbox(
                "Protected only",
                id="state-protected-filter",
                tooltip="Show only protected resources",
            )
            with Horizontal(id="resource-selection-actions"):
                yield Button(
                    "Select all",
                    id="select-matching",
                    tooltip="Select all resources matching the current filters (A)",
                )
                yield Button(
                    "Deselect all",
                    id="deselect-matching",
                    tooltip="Deselect all resources matching the current filters (D)",
                )
        with Horizontal(id="state-tree-container"):
            yield StateTree(
                label="Root",
                id="state-tree",
            ).data_bind(StateInspector.state)

    def on_mount(self) -> None:
        self._update_resource_types()

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        if event.checkbox.id == "state-protected-filter":
            event.stop()
            self.query_one("#state-tree", StateTree).protected_only = event.value

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id in {"select-matching", "deselect-matching"}:
            event.stop()
            tree = self.query_one(StateTree)
            if event.button.id == "select-matching":
                tree.select_matching()
            else:
                tree.deselect_matching()

    def on_state_tree_selection_changed(
        self, event: StateTree.SelectionChanged
    ) -> None:
        self.query_one("#select-matching", Button).disabled = (
            not event.matching_urns - event.selected_urns
        )
        deselect = self.query_one("#deselect-matching", Button)
        deselect.display = event.selecting
        deselect.disabled = not event.matching_urns & event.selected_urns

    def watch_state(self, state: PulumiStack | None) -> None:
        if self.is_mounted:
            self._update_resource_types()

    def _update_resource_types(self) -> None:
        type_filter = self.query_one("#state-type-filter", Select)
        selected = type_filter.value
        resource_types = sorted(
            {resource.type for resource in self.state.resources_by_urn.values()}
            if self.state
            else set()
        )
        resource_type = (
            selected if isinstance(selected, str) and selected in resource_types else ""
        )
        type_filter.set_options(
            [("All resource types", ""), *((kind, kind) for kind in resource_types)]
        )
        type_filter.value = resource_type
        self.query_one("#state-tree", StateTree).resource_type = resource_type

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "state-type-filter" and isinstance(event.value, str):
            self.query_one("#state-tree", StateTree).resource_type = event.value

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != "state-search":
            return
        tree = self.query_one("#state-tree", StateTree)
        tree.search_query = event.value.strip()

    def action_focus_search(self) -> None:
        self.query_one("#state-search", StateSearchInput).focus()

    def on_state_tree_details_requested(
        self, event: StateTree.DetailsRequested
    ) -> None:
        event.stop()
        self.app.push_screen(ResourceDetails(event.resource))
