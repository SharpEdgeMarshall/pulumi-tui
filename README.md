# PLTUI

Pulumi Textual User Interface (`pltui`) is a terminal app focused on exploring Pulumi state interactively.

## What Works Today

- Stack discovery from the current Pulumi project via Automation API.
- State tree visualization grouped by parent/child resource relationships.
- Live search/filter by resource type, name, URN, ID, and parent URN.
- Resource detail modal with full structured payload view.
- Fallback local mode from `state.json` when a Pulumi workspace is unavailable.

## Run

```bash
poetry install
poetry run pltui
```

## Optional Environment Variables

- `PLTUI_PROJECT_DIR`: Pulumi project directory to load (defaults to current working directory).
- `PLTUI_FAKE_STATE=1`: force loading state from local `state.json`.

## Keybindings

- `Ctrl+S`: open stack selector.
- `Ctrl+R`: refresh stack list.
- `Ctrl+L`: reload state for selected stack.
- `/`: focus search input.
- `Ctrl+C`: quit.

## Product Direction

Current focus is a production-ready state explorer.
Next planned capabilities are interactive Pulumi operations (preview/update/actions) from the same TUI.
