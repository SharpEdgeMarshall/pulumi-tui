from dataclasses import dataclass

from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, Footer, Label, RichLog, Static

from pltui.service import PulumiAction, PulumiService


@dataclass(frozen=True)
class ConfirmResult:
    confirmed: bool
    target_dependents: bool = False


class ConfirmModal(ModalScreen[ConfirmResult]):
    """Asks for confirmation, optionally offering a "target dependents" checkbox."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("y", "confirm", "Confirm"),
        Binding("t", "toggle_target_dependents", "Target dependents"),
    ]

    def __init__(
        self,
        title: str,
        message: str,
        confirm_label: str = "Confirm",
        target_dependents: bool | None = None,
    ):
        """``target_dependents`` is the checkbox default, or None to hide it."""
        super().__init__()
        self.title_text = title
        self.message = message
        self.confirm_label = confirm_label
        self.target_dependents = target_dependents

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-dialog"):
            yield Label(self.title_text, id="confirm-title")
            with VerticalScroll(id="confirm-message-scroll"):
                yield Static(Text(self.message), id="confirm-message")
            if self.target_dependents is not None:
                yield Checkbox(
                    "Target dependents",
                    self.target_dependents,
                    id="confirm-target-dependents",
                    tooltip="Also include the resources that depend on the selected ones",
                )
            with Horizontal(id="confirm-actions"):
                yield Button("Cancel", id="confirm-cancel")
                yield Button(self.confirm_label, id="confirm-ok", variant="error")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#confirm-cancel", Button).focus()

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if action == "toggle_target_dependents" and self.target_dependents is None:
            return None
        return True

    def _finish(self, confirmed: bool) -> None:
        target_dependents = False
        if self.target_dependents is not None:
            checkbox = self.query_one("#confirm-target-dependents", Checkbox)
            target_dependents = checkbox.value
        self.dismiss(ConfirmResult(confirmed, target_dependents))

    def action_cancel(self) -> None:
        self._finish(False)

    def action_confirm(self) -> None:
        self._finish(True)

    def action_toggle_target_dependents(self) -> None:
        self.query_one("#confirm-target-dependents", Checkbox).toggle()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        self._finish(event.button.id == "confirm-ok")


class ActionRunModal(ModalScreen[bool]):
    """Previews a Pulumi action, then applies it after explicit confirmation.

    The stack is not locked while the preview is reviewed, so the state is
    fingerprinted before the preview and Apply is blocked if it changed.
    Dismisses with True when the action was applied successfully.
    """

    BINDINGS = [
        Binding("a", "apply", "Apply"),
        Binding("r", "reload", "Reload"),
        Binding("escape", "close", "Close"),
    ]

    def __init__(
        self,
        service: PulumiService,
        action: PulumiAction,
        urns: tuple[str, ...],
        title: str,
        preview_only: bool = False,
        target_dependents: bool = False,
    ):
        super().__init__()
        self.service = service
        self.action = action
        self.urns = urns
        self.title_text = title
        self.preview_only = preview_only
        self.target_dependents = target_dependents
        self.busy = True
        self.can_apply = False
        self.can_reload = False
        self.applied = False
        self.fingerprint: str | None = None

    def compose(self) -> ComposeResult:
        with Vertical(id="action-run") as dialog:
            dialog.border_title = self.title_text
            yield Label("Previewing...", id="action-run-status")
            yield RichLog(id="action-run-log", wrap=True, markup=False)
            with Horizontal(id="action-run-buttons"):
                yield Button("Close", id="action-run-close", disabled=True)
                yield Button("Reload", id="action-reload")
                yield Button("Apply", id="action-apply", variant="error")
        yield Footer()

    def on_mount(self) -> None:
        if self.action.requires_targets:
            # No preview exists for state edits; they were confirmed beforehand.
            self._set_state("Applying...", apply=False, reload=False, busy=True)
            self.run_apply()
            return
        self._set_state("Previewing...", apply=False, reload=False, busy=True)
        self.run_preview()

    def _set_state(
        self,
        status: str,
        *,
        apply: bool,
        reload: bool,
        error: bool = False,
        busy: bool = False,
    ) -> None:
        self.busy = busy
        self.can_apply = apply and not busy
        self.can_reload = reload and not busy
        label = self.query_one("#action-run-status", Label)
        label.update(status)
        label.set_class(error, "-error")
        self.query_one("#action-apply", Button).display = apply
        self.query_one("#action-reload", Button).display = reload
        close = self.query_one("#action-run-close", Button)
        close.disabled = busy
        if not busy:
            target = "#action-apply" if apply else "#action-run-close"
            self.query_one(target, Button).focus()
        self.refresh_bindings()

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        match action:
            case "apply":
                return True if self.can_apply else None
            case "reload":
                return True if self.can_reload else None
            case "close":
                return None if self.busy else True
            case _:
                return True

    def action_apply(self) -> None:
        if self.can_apply:
            self._set_state("Applying...", apply=False, reload=False, busy=True)
            self.run_apply()

    def action_reload(self) -> None:
        if self.can_reload:
            self._set_state("Previewing...", apply=False, reload=False, busy=True)
            self.run_preview()

    def _writer(self):
        log = self.query_one("#action-run-log", RichLog)
        return lambda text: self.app.call_from_thread(
            log.write, Text.from_ansi(text.replace("\r", "").rstrip("\n"))
        )

    @work(thread=True, exclusive=True)
    def run_preview(self) -> None:
        log = self.query_one("#action-run-log", RichLog)
        self.app.call_from_thread(log.clear)
        try:
            fingerprint = self.service.state_fingerprint()
            self.service.run_action(
                self.action,
                self.urns,
                self._writer(),
                dry_run=True,
                target_dependents=self.target_dependents,
            )
        except Exception as exc:
            self.app.call_from_thread(self._preview_failed, str(exc))
        else:
            self.app.call_from_thread(self._preview_done, fingerprint)

    def _preview_failed(self, error: str) -> None:
        self.query_one("#action-run-log", RichLog).write(error)
        self._set_state("Preview failed", apply=False, reload=True, error=True)

    def _preview_done(self, fingerprint: str) -> None:
        self.fingerprint = fingerprint
        if self.preview_only:
            self._set_state("Preview completed", apply=False, reload=False)
        else:
            self._set_state(
                "Review the changes:",
                apply=True,
                reload=True,
            )

    @work(thread=True, exclusive=True)
    def run_apply(self) -> None:
        log = self.query_one("#action-run-log", RichLog)
        try:
            if (
                self.fingerprint is not None
                and self.service.state_fingerprint() != self.fingerprint
            ):
                self.app.call_from_thread(self._apply_blocked)
                return
            self.app.call_from_thread(
                log.write, f"\n---- Applying pulumi {self.action.value} ----"
            )
            self.service.run_action(
                self.action,
                self.urns,
                self._writer(),
                target_dependents=self.target_dependents,
            )
        except Exception as exc:
            self.app.call_from_thread(self._apply_failed, str(exc))
        else:
            self.app.call_from_thread(self._apply_done)

    def _apply_blocked(self) -> None:
        self.query_one("#action-run-log", RichLog).write(
            "\nThe stack state changed since the preview; nothing was applied."
        )
        self._set_state(
            "State changed since preview. Apply blocked, re-run the preview.",
            apply=False,
            reload=True,
            error=True,
        )

    def _apply_failed(self, error: str) -> None:
        self.query_one("#action-run-log", RichLog).write(error)
        self._set_state("Failed", apply=False, reload=False, error=True)

    def _apply_done(self) -> None:
        self.applied = True
        self._set_state("Completed", apply=False, reload=False)

    def action_close(self) -> None:
        if not self.busy:
            self.dismiss(self.applied)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        if self.busy:
            return
        match event.button.id:
            case "action-apply":
                self.action_apply()
            case "action-reload":
                self.action_reload()
            case _:
                self.action_close()
