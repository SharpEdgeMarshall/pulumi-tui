
<h1 align="center">PLTUI - The Pulumi Terminal UI</h1>

<p align="center">
  A terminal UI to explore and operate on your Pulumi stacks.<br>
  Built with <a href="https://textual.textualize.io">Textual</a> and the Pulumi Automation API.
</p>

[![PyPI version](https://img.shields.io/pypi/v/pulumi-tui?style=for-the-badge)](https://pypi.org/project/pulumi-tui/)
[![CI](https://img.shields.io/github/actions/workflow/status/SharpEdgeMarshall/pulumi-tui/test.yml?style=for-the-badge
)](https://github.com/SharpEdgeMarshall/pulumi-tui/actions/workflows/test.yml)
![License](https://img.shields.io/github/license/SharpEdgeMarshall/pulumi-tui?style=for-the-badge)
![PyPI - Downloads](https://img.shields.io/pypi/dm/pulumi-tui?style=for-the-badge)

<p align="center">
  <img src="https://raw.githubusercontent.com/SharpEdgeMarshall/pulumi-tui/main/docs/preview.svg" alt="PLTUI previewing a Pulumi stack" width="100%">
</p>

## Features

- **State explorer**: browse a stack's resources as a parent/child tree.
- **Search and filters**: live search (type, name, URN, ID, parent URN), a resource-type dropdown and a "Protected only" checkbox, all on one row.
- **Multi-selection**: select resources with the keyboard, or use filter-aware **Select all** / **Deselect all**.
- **Resource details**: overview, inputs, outputs and a diff of both, in a modal.
- **Pulumi actions**: preview, up, refresh and destroy, on the selected resources or the whole stack.
- **Safe by design**: up, refresh and destroy show a preview first and apply only after confirmation. If the stack state changes while you review, apply is blocked.
- **State editing**: delete resources from the state, or protect and unprotect them (🔒 marks protected resources).
- **Pulumi-branded dark theme** built on the three colours of the Pulumi logo.

## Install

The package `pulumi-tui` provides the `pltui` command.

| Tool   | Install                    | Upgrade                       | Run                                      |
| ------ | -------------------------- | ----------------------------- | ---------------------------------------- |
| pipx   | `pipx install pulumi-tui`  | `pipx upgrade pulumi-tui`     | `cd /path/to/pulumi/project && pltui`    |
| uv     | `uv tool install pulumi-tui` | `uv tool upgrade pulumi-tui` | `cd /path/to/pulumi/project && pltui`    |
| uvx    | none (no install needed)   | n/a                           | `uvx --from pulumi-tui pltui`            |
| Source | `git clone https://github.com/SharpEdgeMarshall/pulumi-tui.git && cd pulumi-tui && poetry install` | `git pull && poetry install` | `poetry run pltui` |

Requires Python 3.11 or newer.

Doesn't require pulumi, it's auto installed.

Building from source requires [Poetry](https://python-poetry.org/docs/#installation).

## Usage

Run `pltui` from a Pulumi project directory, or point it at one:

```bash
cd path/to/your/pulumi-project
pltui

# or
pltui -C path/to/your/pulumi-project
```

Choose a stack with the dropdown in the header, then explore its resources.

| Option | Description |
|---|---|
| `-C`, `--cwd` | Run as if started in this Pulumi project directory, like `pulumi -C`. Defaults to the current directory. |
| `-V`, `--version` | Show the version and exit. |
| `-h`, `--help` | Show the help and exit. |


### Keybindings

**Actions**

| Key | Action |
|---|---|
| `Ctrl+P` | `pulumi preview` |
| `Ctrl+U` | `pulumi up` |
| `Ctrl+R` | `pulumi refresh` |
| `Ctrl+X` | `pulumi destroy` |
| `Ctrl+D` | Delete the selected resources from the state only (`pulumi state delete`) |
| `Ctrl+L` | Protect the selected resources. Needs at least one unprotected resource selected. |
| `Ctrl+O` | Unprotect the selected resources. Needs at least one protected resource selected. |
| `Ctrl+\` | Command palette |
| `Ctrl+Q` | Quit |

**Resource tree**

| Key | Action |
|---|---|
| `Space` | Select or deselect the focused resource |
| `A` / `D` | Select all / deselect all resources matching the filters |
| `E` | Expand or collapse the focused branch |
| `Enter` or double-click | Open the resource details |


### Resource selection

Select all and Deselect all affect only resources matching the current filters, including matches in collapsed branches. Parents shown only for context are not selected. Selections hidden by filters stay selected and are counted in the title.

Selection survives reloads of the same stack, dropping resources that no longer exist, and is cleared when a different stack is loaded.

## Try it locally

`examples/local` is a real Pulumi Python project on a local filesystem backend. It creates only component resources, so no cloud credentials, providers or billable infrastructure are needed.

```bash
make setup         # install dependencies
make example-init  # create the dev and sandbox stacks with sample state
make run           # open pltui against the example project
```

`make example-init` is safe to re-run. Use `make example-clean` to remove the local state and start over.

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](https://github.com/SharpEdgeMarshall/pulumi-tui/blob/main/CONTRIBUTING.md) for setup, project layout and conventions.

## License

Apache-2.0. See [LICENSE](https://github.com/SharpEdgeMarshall/pulumi-tui/blob/main/LICENSE).
