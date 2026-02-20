from textual import work
from textual.widgets import Tree

from pltui.clients.pulumi import PulumiClient


class StateTree(Tree):
    current_node = None
    highlighted_resource_node = []
    selected_nodes = []
    current_state = []
    sensitive_values = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_state = PulumiClient().get_state()
        self.loading = False
        self.guide_depth = 3
        self.root.data = ""

    def build_tree(self, search_string="") -> None:
        self.clear()
        self.selected_nodes = []
        self.current_node = None
        module_nodes = {}

        filtered_blocks = dict(
            filter(
                lambda block: search_string in block[1].contents
                or search_string in block[1].name
                or search_string in block[1].submodule,
                self.current_state.state_tree.items(),
            )
        )
        modules = {
            block.submodule
            for block in filtered_blocks.values()
            if block.submodule != ""
        }

        for module_fullname in sorted(modules):
            parts = split_resource_name(module_fullname)
            submodule = ""
            i = 0
            while i < len(parts):
                parent = submodule
                short_name = f"{parts[i]}.{parts[i+1]}"
                submodule = (
                    ".".join([submodule, short_name]) if submodule else short_name
                )
                if submodule not in module_nodes:
                    if module_nodes.get(parent) is None:
                        parent_node = self.root
                    else:
                        parent_node = module_nodes[parent]
                    node = parent_node.add(short_name, data=submodule)
                    module_nodes[submodule] = node
                i += 2

        # build resource tree
        for block in filtered_blocks.values():
            if block.submodule == "":
                module_node = self.root
            else:
                module_node = module_nodes[block.submodule]
            leaf = module_node.add_leaf(block.name, data=block)
            if block.is_tainted:
                leaf.label.stylize("gold3 strike")

        self.root.expand_all()

    @work(exclusive=True)
    async def extract_sensitive_values(self) -> None:
        self.sensitive_values = {}
        try:
            returncode, stdout = await execute_async(
                ApplicationGlobals.executable, "show -json"
            )
            if returncode == 0:
                self.current_state_json = json.loads(stdout)
                self.sensitive_values = extract_sensitive_values(
                    self.current_state_json
                )
        except CancelledError:
            pass
        except Exception as e:
            logger.error("Error extracting sensitive values: %s", e)

    @work(exclusive=True)
    async def refresh_state(self, focus=True) -> None:
        self.loading = True
        self.app.notify("Refreshing state tree")
        self.app.search.value = ""
        try:
            await self.current_state.refresh_state()
            self.extract_sensitive_values()
        except Exception as e:
            ApplicationGlobals.successful_termination = False
            self.app.exit(e)
            return

        self.build_tree()
        self.current_node = self.get_node_at_line(min(self.cursor_line, self.last_line))
        self.update_highlighted_resource_node(self.current_node)
        self.loading = False
        OutboundAPIs.post_usage("refreshed state")
        if focus:
            self.focus()

    def update_highlighted_resource_node(self, node) -> None:
        self.current_node = node
        if type(self.current_node.data) == Block:
            self.highlighted_resource_node = (
                [node] if self.current_node.data.type == Block.TYPE_RESOURCE else []
            )
        else:
            self.highlighted_resource_node = []

    def on_tree_node_highlighted(self, node) -> None:
        self.update_highlighted_resource_node(node.node)

    def on_tree_node_selected(self) -> None:
        if not self.current_node:
            return
        if not self.current_node.allow_expand:
            self.app.resource.clear()
            self.app.resource.write(self.current_node.data.contents)
            self.app.switcher.border_title = (
                f"{self.current_node.data.submodule}.{self.current_node.data.name}"
                if self.current_node.data.submodule
                else self.current_node.data.name
            )
            self.app.switcher.current = "resource"

    def select_current_node(self) -> None:
        if self.current_node is None:
            return
        if (
            self.current_node.allow_expand
            or self.current_node.data.type == Block.TYPE_DATASOURCE
        ):
            return
        if self.current_node in self.selected_nodes:
            self.selected_nodes.remove(self.current_node)
            self.current_node.label = self.current_node.label.plain
            if self.current_node.data.is_tainted:
                self.current_node.label.stylize("gold3 strike")
        else:
            self.selected_nodes.append(self.current_node)
            self.current_node.label.stylize("red bold italic reverse")

    def display_sensitive_data(self, fullname, contents) -> None:
        self.app.resource.clear()
        sensitive_values = self.sensitive_values.get(fullname)
        if sensitive_values:
            for value in sensitive_values.values():
                if value:
                    contents = contents.replace(
                        " (sensitive value)\n", f" {value}\n", 1
                    )
        self.app.resource.write(contents)
