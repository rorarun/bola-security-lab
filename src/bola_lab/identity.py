"""Shared authentication dependencies; no project permission decisions."""

from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from bola_lab.auth import TOKEN_PATTERN, token_digest
from bola_lab.db import connect

BEARER = HTTPBearer(auto_error=False)


def unauthorized() -> HTTPException:
    return HTTPException(
        status_code=401, detail="Invalid credentials", headers={"WWW-Authenticate": "Bearer"}
    )


def authenticated_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(BEARER)],
) -> dict:
    if credentials is None or not TOKEN_PATTERN.fullmatch(credentials.credentials):
        raise unauthorized()
    digest = token_digest(credentials.credentials)
    with connect(request.app.state.settings) as conn:
        user = conn.execute(
            """SELECT u.id, u.email FROM auth_sessions s JOIN users u ON u.id = s.user_id
               WHERE s.token_digest=%s AND s.revoked_at IS NULL AND s.expires_at > now()""",
            (digest,),
        ).fetchone()
    if user is None:
        raise unauthorized()
    return {**user, "token_digest": digest}
