# Contributing

Contributions are welcome.

1. Fork the repository and create a branch.
2. Install dependencies with `make setup`.
3. Use the local example project as a test bench: `make example-init`, then `make run`. See [Try it locally](README.md#try-it-locally) for the manual steps.
4. Run `make check` (metadata, lint, format and type checks) before opening a pull request describing what and why.

Run `make help` to list all tasks.

## Project layout

| Path | Contents |
|---|---|
| `pltui/app.py` | App, key bindings and action flow |
| `pltui/service.py` | Pulumi Automation API and CLI wrapper |
| `pltui/models.py` | Pydantic models of the exported state |
| `pltui/selection.py` | Resource selection model |
| `pltui/components/` | Header, footer, state tree/inspector and modals |
| `pltui/theme.py`, `pltui/ui.tcss` | Themes and styling |
| `examples/local` | Local Pulumi project for development |

## Conventions

- Use Textual's standard semantic theme variables (such as `$primary`, `$error`, and `$background`) instead of hardcoded colours.
- Keep theme-specific styling in `pltui/theme.py`; avoid app-specific theme-variable aliases so built-in Textual themes remain compatible.
- Rely on Textual's `Footer` for key hints, and keep buttons and shortcuts consistent.
- Format with `ruff` and type-check with `mypy` (both are dev dependencies). `make check` runs them, and `make format` fixes formatting and lint issues.

## Pull requests and releases

Release notes are drafted automatically from merged pull requests. Titles starting with `feat`, `fix`, `chore`, `ci`, `docs` or `refactor` are labelled automatically; add the `skip-changelog` label to leave a change out of the notes.

## Refreshing the preview image

The files in `docs/screenshots/` are Textual screenshots, exported with `app.save_screenshot()` from a headless `run_test` session against `examples/local`.
