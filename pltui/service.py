import os
from abc import ABC
from typing import Optional

import yaml
from pulumi.automation import LocalWorkspace, StackSummary

from .models import PulumiStack, PulumiStackExport


class StateService(ABC):
    def get_state(self, stack_name: str) -> PulumiStack:
        raise NotImplementedError

    def list_stacks(self) -> list[StackSummary]:
        raise NotImplementedError

    @property
    def project_name(self) -> str:
        raise NotImplementedError


class PulumiService(StateService):
    def __init__(self, project_dir: Optional[str] = None):
        self.project_dir = project_dir

        self.workspace = LocalWorkspace(work_dir=project_dir or os.getcwd())

    @property
    def project_name(self) -> str:
        return self.workspace.project_settings().name

    def list_stacks(self) -> list[StackSummary]:
        return self.workspace.list_stacks()

    def get_state(self, stack_name: str) -> PulumiStack:
        raw_state = self.get_raw_state(stack_name=stack_name)

        return PulumiStack.model_validate(raw_state.deployment.resources)

    def get_raw_state(self, stack_name: str) -> PulumiStackExport:

        deployment = self.workspace.export_stack(stack_name=stack_name)

        return PulumiStackExport.model_validate(
            {"version": deployment.version, "deployment": deployment.deployment}
        )


class PulumiFakeService(StateService):

    @property
    def project_name(self) -> str:
        return "fake-project"

    def get_state(self, stack_name: str) -> PulumiStack:
        with open("state.json", "r") as f:
            state = yaml.safe_load(f.read())
        stack = PulumiStackExport.model_validate(
            {"version": state["version"], "deployment": state["deployment"]}
        )

        return PulumiStack.model_validate(stack.deployment.resources)

    def list_stacks(self) -> list[StackSummary]:
        return []
