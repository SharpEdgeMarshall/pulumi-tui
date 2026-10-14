import hashlib
import json
import os
from enum import Enum
from typing import Any, Callable, Optional, Sequence

import yaml  # type: ignore[import-untyped]
from pulumi.automation import LocalWorkspace, PulumiCommand, Stack

from .models import PulumiStack, PulumiStackExport


class PulumiAction(str, Enum):
    PREVIEW = "preview"
    UP = "up"
    REFRESH = "refresh"
    DESTROY = "destroy"
    STATE_DELETE = "state delete"
    PROTECT = "state protect"
    UNPROTECT = "state unprotect"

    @property
    def mutates_state(self) -> bool:
        return self is not PulumiAction.PREVIEW

    @property
    def requires_targets(self) -> bool:
        return self in _STATE_ACTIONS


# Low-level state edits: they need explicit targets and have no preview.
_STATE_ACTIONS = (
    PulumiAction.STATE_DELETE,
    PulumiAction.PROTECT,
    PulumiAction.UNPROTECT,
)


class PulumiService:
    def __init__(self) -> None:
        self._cmd: Optional[PulumiCommand] = None
        self._workspace: Optional[LocalWorkspace] = None
        self.stack_name: Optional[str] = None

    @property
    def ready(self) -> bool:
        return self._workspace is not None

    @property
    def cmd(self) -> PulumiCommand:
        if self._cmd is None:
            raise RuntimeError("The Pulumi CLI is not available.")
        return self._cmd

    @property
    def workspace(self) -> LocalWorkspace:
        if self._workspace is None:
            raise RuntimeError("No Pulumi workspace initialized.")
        return self._workspace

    @property
    def project_name(self) -> str:
        try:
            return self.workspace.project_settings().name
        except Exception:
            # The SDK parser crashes on some valid Pulumi.yaml files (e.g. an
            # empty `template.config`); only the name is needed here.
            return self._read_project_name()

    def _read_project_name(self) -> str:
        for ext in (".yaml", ".yml", ".json"):
            path = os.path.join(self.project_dir, f"Pulumi{ext}")
            if not os.path.exists(path):
                continue
            with open(path, encoding="utf-8") as file:
                settings = json.load(file) if ext == ".json" else yaml.safe_load(file)
            if isinstance(settings, dict) and settings.get("name"):
                return str(settings["name"])
            break
        raise RuntimeError(
            f"No project name found in Pulumi.yaml at {self.project_dir}"
        )

    def setup(self, project_dir: str) -> None:
        """Slow: runs the Pulumi CLI. Call it from a worker thread."""
        self.project_dir = project_dir
        self.stack_name = None
        self._cmd = PulumiCommand.install()
        self._workspace = LocalWorkspace(work_dir=project_dir, pulumi_command=self._cmd)

    def list_stacks(self) -> list[str]:
        return [stack.name for stack in self.workspace.list_stacks()]

    def select_stack(self, stack_name: str):
        self.workspace.select_stack(stack_name=stack_name)
        self.stack_name = stack_name

    def _selected_stack_name(self) -> str:
        if self.stack_name is None:
            raise RuntimeError("No stack is currently selected.")
        return self.stack_name

    def get_state(self) -> PulumiStack:
        stack_name = self._selected_stack_name()
        raw_state = self.get_raw_state()

        return PulumiStack.model_validate(
            {"name": stack_name, "resources": raw_state.deployment.resources}
        )

    def get_raw_state(self) -> PulumiStackExport:
        stack_name = self._selected_stack_name()
        deployment = self.workspace.export_stack(stack_name=stack_name)

        return PulumiStackExport.model_validate(
            {"version": deployment.version, "deployment": deployment.deployment}
        )

    def state_fingerprint(self) -> str:
        """Hash of the exported stack state, used to detect concurrent changes."""
        stack_name = self._selected_stack_name()
        deployment = self.workspace.export_stack(stack_name=stack_name)
        payload = json.dumps(
            {"version": deployment.version, "deployment": deployment.deployment},
            sort_keys=True,
            default=str,
        )
        return hashlib.sha256(payload.encode()).hexdigest()

    def run_action(
        self,
        action: PulumiAction,
        urns: Sequence[str] = (),
        on_output: Optional[Callable[[str], None]] = None,
        dry_run: bool = False,
        target_dependents: bool = False,
    ) -> None:
        """Run a Pulumi action on the selected stack.

        An empty ``urns`` runs the action against the whole stack, as the Pulumi
        CLI does by default. With ``dry_run`` the action only previews its changes.
        ``target_dependents`` also includes the dependents of the targeted resources.
        """
        stack_name = self._selected_stack_name()
        if action.requires_targets and not urns:
            raise ValueError(f"'{action.value}' requires at least one resource.")

        emit = on_output or (lambda _: None)
        if action is PulumiAction.STATE_DELETE:
            self._state_delete(urns, emit, target_dependents)
            return
        if action in (PulumiAction.PROTECT, PulumiAction.UNPROTECT):
            self._state_protect(action, urns, emit)
            return

        stack = Stack.select(stack_name, self.workspace)
        options: dict[str, Any] = {
            "color": "always",
            "suppress_progress": True,
            "on_output": emit,
        }
        if urns:
            options["target"] = list(urns)
            options["target_dependents"] = target_dependents
        match action:
            case PulumiAction.PREVIEW:
                stack.preview(**options)
            case PulumiAction.UP if dry_run:
                stack.preview(diff=True, **options)
            case PulumiAction.UP:
                stack.up(**options)
            case PulumiAction.REFRESH if dry_run:
                self._refresh_diff(stack_name, urns, emit, target_dependents)
            case PulumiAction.REFRESH:
                stack.refresh(**options)
            case PulumiAction.DESTROY:
                stack.destroy(preview_only=dry_run, **options)

    def _refresh_diff(
        self,
        stack_name: str,
        urns: Sequence[str],
        emit: Callable[[str], None],
        target_dependents: bool,
    ) -> None:
        # Stack.refresh has no diff option, so call the CLI directly.
        args = [
            "refresh",
            "--preview-only",
            "--diff",
            "--stack",
            stack_name,
            "--color",
            "always",
            "--non-interactive",
            "--suppress-progress",
        ]
        for urn in urns:
            args += ["--target", urn]
        if urns and target_dependents:
            args.append("--target-dependents")
        self.cmd.run(
            args,
            self.project_dir,
            self.workspace.env_vars,
            on_output=emit,
            on_error=emit,
        )

    def _state_protect(
        self,
        action: PulumiAction,
        urns: Sequence[str],
        emit: Callable[[str], None],
    ) -> None:
        stack_name = self._selected_stack_name()
        verb = action.value.split()[-1]
        args = ["state", verb, *urns, "--stack", stack_name, "--yes"]
        emit(f"$ pulumi state {verb} ({len(urns)} resource(s))\n")
        self.cmd.run(
            args,
            self.project_dir,
            self.workspace.env_vars,
            on_output=emit,
            on_error=emit,
        )

    def _state_delete(
        self,
        urns: Sequence[str],
        emit: Callable[[str], None],
        target_dependents: bool,
    ) -> None:
        stack_name = self._selected_stack_name()
        # Delete in reverse state order so dependents are removed first.
        order = {urn: i for i, urn in enumerate(self.get_state().resources_by_urn)}
        for urn in sorted(urns, key=lambda u: order.get(u, 0), reverse=True):
            args = ["state", "delete", urn, "--stack", stack_name, "--yes"]
            if target_dependents:
                args.append("--target-dependents")
            emit(f"$ pulumi {' '.join(args[:3])}\n")
            self.cmd.run(
                args,
                self.project_dir,
                self.workspace.env_vars,
                on_output=emit,
                on_error=emit,
            )
