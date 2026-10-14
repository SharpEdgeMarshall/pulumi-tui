from dataclasses import dataclass, field
from typing import Iterable


@dataclass
class ResourceSelection:
    """Operation-independent selection of resource URNs within a stack."""

    stack_name: str | None = None
    urns: set[str] = field(default_factory=set)

    def reconcile(self, stack_name: str | None, available: Iterable[str]) -> None:
        if stack_name != self.stack_name:
            self.urns.clear()
        self.stack_name = stack_name
        self.urns.intersection_update(available)

    def toggle(self, urn: str) -> None:
        if urn in self.urns:
            self.urns.remove(urn)
        else:
            self.urns.add(urn)

    def select(self, urns: Iterable[str]) -> None:
        self.urns.update(urns)

    def deselect(self, urns: Iterable[str]) -> None:
        self.urns.difference_update(urns)

    def clear(self) -> None:
        self.urns.clear()
