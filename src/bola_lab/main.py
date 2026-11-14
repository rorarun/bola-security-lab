from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from psycopg.errors import UniqueViolation

from bola_lab.auth import (
    HASHER,
    hash_password,
    new_token,
    token_digest,
    verify_password,
)
from bola_lab.config import Settings
from bola_lab.db import connect
from bola_lab.endpoint_api import router as resource_router
from bola_lab.identity import authenticated_user, unauthorized
from bola_lab.migrations import verify_schema
from bola_lab.schemas import Credentials, TokenResponse, UserResponse


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        verify_schema(settings)
        # Unknown-user login still performs an Argon2 verification.
        app.state.dummy_hash = hash_password("unusable-" + new_token())
        yield

    app = FastAPI(title="BOLA Security Lab", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings

    @app.exception_handler(RequestValidationError)
    async def safe_validation_error(request: Request, exc: RequestValidationError):
        # Pydantic's default errors may echo password/token input; expose no input values.
        return JSONResponse(
            status_code=422,
            content={
                "detail": [
                    {"loc": error["loc"], "type": error["type"], "msg": "Invalid request field"}
                    for error in exc.errors()
                ]
            },
        )

    @app.middleware("http")
    async def no_store(request: Request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.get("/health/live")
    def live():
        return {"status": "ok"}

    @app.get("/health/ready")
    def ready():
        try:
            with connect(settings) as conn:
                conn.execute("SELECT 1")
        except Exception:
            raise HTTPException(status_code=503, detail="Database unavailable") from None
        return {"status": "ready"}

    @app.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
    def register(body: Credentials):
        password_hash = hash_password(body.password.get_secret_value())
        try:
            with connect(settings) as conn:
                user = conn.execute(
                    "INSERT INTO users (email, password_hash) VALUES (%s, %s) RETURNING id, email",
                    (body.email, password_hash),
                ).fetchone()
        except UniqueViolation:
            raise HTTPException(status_code=409, detail="Account already exists") from None
        return user

    @app.post("/auth/token", response_model=TokenResponse)
    def login(body: Credentials):
        with connect(settings) as conn:
            user = conn.execute("SELECT * FROM users WHERE email = %s", (body.email,)).fetchone()
            candidate_hash = user["password_hash"] if user else app.state.dummy_hash
            valid = verify_password(candidate_hash, body.password.get_secret_value())
            if user is None or not valid:
                raise unauthorized()
            if HASHER.check_needs_rehash(user["password_hash"]):
                conn.execute(
                    "UPDATE users SET password_hash = %s WHERE id = %s",
                    (
                        hash_password(body.password.get_secret_value()),
                        user["id"],
                    ),
                )
            token = new_token()
            conn.execute(
                """INSERT INTO auth_sessions (token_digest, user_id, expires_at)
                   VALUES (%s, %s, now() + (%s * interval '1 second'))""",
                (token_digest(token), user["id"], settings.token_ttl_seconds),
            )
        return TokenResponse(access_token=token, expires_in=settings.token_ttl_seconds)

    @app.get("/users/me", response_model=UserResponse)
    def me(user: Annotated[dict, Depends(authenticated_user)]):
        return user

    @app.delete("/auth/token", status_code=status.HTTP_204_NO_CONTENT)
    def logout(user: Annotated[dict, Depends(authenticated_user)]):
        with connect(settings) as conn:
            conn.execute(
                "UPDATE auth_sessions SET revoked_at = now() WHERE token_digest = %s",
                (user["token_digest"],),
            )
        return Response(status_code=204)

    app.state.authorization_implementation = "endpoint-specific"
    app.include_router(resource_router)
    return app
