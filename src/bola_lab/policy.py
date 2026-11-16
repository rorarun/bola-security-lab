"""Central deny-by-default action policy. No request body supplies roles or grants."""

from dataclasses import dataclass

from fastapi import HTTPException

ROLES = {
    "project.read": frozenset({"owner", "editor", "viewer"}),
    "project.update": frozenset({"owner"}),
    "project.delete": frozenset({"owner"}),
    "memberships.read": frozenset({"owner"}),
    "memberships.add": frozenset({"owner"}),
    "memberships.update": frozenset({"owner"}),
    "memberships.delete": frozenset({"owner"}),
    "tasks.read": frozenset({"owner", "editor", "viewer"}),
    "tasks.create": frozenset({"owner", "editor"}),
    "tasks.update": frozenset({"owner", "editor"}),
    "tasks.delete": frozenset({"owner"}),
}


@dataclass(frozen=True)
class ProjectScope:
    organization_id: int
    project_id: int
    actor_id: int
    role: str

    @property
    def parameters(self):
        return (self.organization_id, self.project_id, self.actor_id)


def authorize(scope: ProjectScope, action: str) -> None:
    if scope.role not in ROLES.get(action, frozenset()):
        raise HTTPException(403, "Insufficient project role")
