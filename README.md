
<h1 align="center">PLTUI</h1>

<p align="center">
  A terminal UI to explore and operate on your Pulumi stacks.<br>
  Built with <a href="https://textual.textualize.io">Textual</a> and the Pulumi Automation API.
</p>

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

### Requirements

- Python 3.11 or newer
- The [Pulumi CLI](https://www.pulumi.com/docs/iac/download-install/)

### As a command (recommended)

Install `pulumi-tui` (which provides the `pltui` command) in its own isolated environment, using [pipx](https://pipx.pypa.io) or [uv](https://docs.astral.sh/uv/):

```bash
pipx install pulumi-tui
# or
uv tool install pulumi-tui
```

Upgrade with `pipx upgrade pulumi-tui` or `uv tool upgrade pulumi-tui`. To try it without installing, run `uvx --from pulumi-tui pltui`.

### From source

Requires [Poetry](https://python-poetry.org/docs/#installation).

```bash
git clone https://github.com/SharpEdgeMarshall/pulumi-tui.git
cd pulumi-tui
poetry install
```

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

**Modals**

| Key | Action |
|---|---|
| `Y` | Confirm |
| `T` | Toggle "Target dependents" |
| `A` / `R` | Apply / re-preview |
| `Esc` | Cancel or close |


### Resource selection

Select all and Deselect all affect only resources matching the current filters, including matches in collapsed branches. Parents shown only for context are not selected. Selections hidden by filters stay selected and are counted in the title.

Selection survives reloads of the same stack, dropping resources that no longer exist, and is cleared when a different stack is loaded.

## Try it locally

`examples/local` is a real Pulumi Python project on a local filesystem backend. It creates only component resources, so no cloud credentials, providers or billable infrastructure are needed.

```bash
poetry install
mkdir -p examples/local/.pulumi-state
export PULUMI_CONFIG_PASSPHRASE=''
poetry run pulumi -C examples/local stack init dev
poetry run pulumi -C examples/local up --yes
poetry run pulumi -C examples/local stack init sandbox
poetry run pulumi -C examples/local up --yes
poetry run pltui -C examples/local
```

The empty passphrase is only for this non-sensitive example. Backend files and stack configuration are ignored by Git. Run `stack init` once per stack; afterwards use `stack select dev` or `stack select sandbox` before `up`.

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](https://github.com/SharpEdgeMarshall/pulumi-tui/blob/main/CONTRIBUTING.md) for setup, project layout and conventions.

## License

Apache-2.0. See [LICENSE](https://github.com/SharpEdgeMarshall/pulumi-tui/blob/main/LICENSE).
