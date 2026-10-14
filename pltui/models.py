from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, model_validator


class PulumiResource(BaseModel):

    urn: str
    type: str
    id: Optional[str] = None

    parent_urn: Optional[str] = Field(alias="parent", default=None)
    parent_resource: Optional["PulumiResource"] = Field(default=None, exclude=True)
    children: list["PulumiResource"] = Field(default_factory=list, exclude=True)

    # Resource properties
    properties: dict[str, Any] = Field(alias="outputs", default_factory=dict)
    inputs: dict[str, Any] = Field(default_factory=dict)
    dependencies: list[str] = Field(default_factory=list)

    modified: Optional[datetime] = Field(default=None)
    sourcePosition: Optional[str] = Field(default=None)

    @property
    def name(self) -> str:
        return self.urn.split("::")[-1]


class PulumiStack(BaseModel):

    name: str
    root_resources: list[PulumiResource]
    stack_resource: PulumiResource

    resources_by_urn: dict[str, PulumiResource]

    @model_validator(mode="before")
    def build_resource_tree(cls, data):
        """
        This is the core logic. It transforms the flat list of resources
        into a hierarchical tree and populates the helper dictionary.
        """
        pending_resources = [PulumiResource.model_validate(res) for res in data]

        # 1. Create a dictionary for fast URN lookups
        resources_by_urn = {res.urn: res for res in pending_resources}
        root_resources = []
        stack_resource = None

        while pending_resources:
            resource = pending_resources.pop(0)

            if resource.parent_urn is None:
                # This is a root resource
                root_resources.append(resource)
                if resource.type == "pulumi:pulumi:Stack":
                    stack_resource = resource
            elif resource.parent_urn in resources_by_urn:
                parent_resource = resources_by_urn[resource.parent_urn]
                parent_resource.children.append(resource)
                resource.parent_resource = parent_resource
            else:
                pending_resources.append(resource)

        if not stack_resource:
            raise ValueError("No stack resource found in the provided data.")

        return {
            "name": stack_resource.name,
            "root_resources": root_resources,
            "stack_resource": stack_resource,
            "resources_by_urn": resources_by_urn,
        }


# This model represents the main 'deployment' object
class PulumiDeployment(BaseModel):
    manifest: dict[str, Any]
    secrets_providers: Optional[dict[str, Any]] = Field(
        alias="secretsProviders", default=None
    )
    resources: list[dict] = []


# This is the top-level model that matches the entire JSON file
class PulumiStackExport(BaseModel):
    version: int
    deployment: PulumiDeployment
