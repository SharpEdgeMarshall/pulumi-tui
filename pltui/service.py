import json
import os
from abc import ABC
from typing import Optional

from .models import PulumiStack, PulumiStackExport


class StateService(ABC):
    def get_state(self, stack_name: str) -> PulumiStack:
        raise NotImplementedError

    def list_stacks(self) -> list[str]:
        raise NotImplementedError

    @property
    def project_name(self) -> str:
        raise NotImplementedError


class PulumiService(StateService):
    def __init__(self, project_dir: Optional[str] = None):
        self.project_dir = project_dir

        try:
            from pulumi.automation import LocalWorkspace
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Pulumi SDK is not installed. Install dependencies to use live mode."
            ) from exc

        self.workspace = LocalWorkspace(work_dir=project_dir or os.getcwd())

    @property
    def project_name(self) -> str:
        return self.workspace.project_settings().name

    def list_stacks(self) -> list[str]:
        return [stack.name for stack in self.workspace.list_stacks()]

    def get_state(self, stack_name: str) -> PulumiStack:
        raw_state = self.get_raw_state(stack_name=stack_name)

        return PulumiStack.model_validate(raw_state.deployment.resources)

    def get_raw_state(self, stack_name: str) -> PulumiStackExport:

        deployment = self.workspace.export_stack(stack_name=stack_name)

        return PulumiStackExport.model_validate(
            {"version": deployment.version, "deployment": deployment.deployment}
        )


class PulumiFakeService(StateService):
    STACK_NAME = "local"

    @property
    def project_name(self) -> str:
        return "fake-project"

    def get_state(self, stack_name: str) -> PulumiStack:
        with open("state.json", "r", encoding="utf-8") as f:
            state = json.load(f)
        stack = PulumiStackExport.model_validate(
            {"version": state["version"], "deployment": state["deployment"]}
        )

        return PulumiStack.model_validate(stack.deployment.resources)

    def list_stacks(self) -> list[str]:
        return [self.STACK_NAME]
