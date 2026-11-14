"""Organization membership provisioning is a local lab command, never an HTTP endpoint."""

from psycopg.errors import ForeignKeyViolation, UniqueViolation

from bola_lab.config import Settings
from bola_lab.db import connect


def add_organization_member(settings: Settings, organization_id: int, user_id: int) -> None:
    if settings.environment != "lab" or not settings.lab_opt_in:
        raise ValueError(
            "Organization provisioning requires environment=lab and explicit lab_opt_in"
        )
    if not (0 < organization_id <= 9223372036854775807 and 0 < user_id <= 9223372036854775807):
        raise ValueError("Use positive bigint organization and user identifiers")
    try:
        with connect(settings) as conn:
            conn.execute(
                "INSERT INTO organization_memberships VALUES (%s,%s)", (organization_id, user_id)
            )
    except ForeignKeyViolation:
        raise ValueError("Organization or registered user does not exist") from None
    except UniqueViolation:
        raise ValueError("User already belongs to the organization") from None
