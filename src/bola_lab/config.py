"""Fail-closed startup settings. No request can select an authorization mode."""

import os
from typing import Literal, Self

from psycopg.conninfo import conninfo_to_dict
from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    database_url: SecretStr
    environment: Literal["lab", "test", "production"] = "production"
    authorization_mode: Literal["hardened", "endpoint", "baseline"] = "hardened"
    lab_opt_in: bool = False
    bind_host: Literal["127.0.0.1", "0.0.0.0", "::1"] = "127.0.0.1"
    publish_host: Literal["127.0.0.1", "::1"] = "127.0.0.1"
    port: int = Field(default=8000, ge=1024, le=65535)
    token_ttl_seconds: int = Field(default=900, ge=60, le=900)

    @model_validator(mode="after")
    def validate_safety(self) -> Self:
        try:
            parameters = conninfo_to_dict(self.database_url.get_secret_value())
            if not parameters.get("dbname") or not parameters.get("host"):
                raise ValueError
        except Exception:
            raise ValueError("database_url must specify a PostgreSQL host and database") from None
        if self.authorization_mode != "hardened":
            if self.environment != "lab" or not self.lab_opt_in:
                raise ValueError(
                    "non-hardened modes require environment=lab and explicit lab_opt_in"
                )
            if self.authorization_mode == "baseline":
                if self.bind_host not in {"127.0.0.1", "::1"}:
                    raise ValueError("baseline requires a loopback bind")
                raise ValueError("baseline is unavailable in M2")
            # Endpoint mode is defensive. Docker may bind internally to 0.0.0.0;
            # the shipped host publication is still literal loopback.
        return self

    @classmethod
    def from_env(cls) -> Self:
        keys = {
            "database_url": "BOLA_DATABASE_URL",
            "environment": "BOLA_ENVIRONMENT",
            "authorization_mode": "BOLA_AUTHORIZATION_MODE",
            "lab_opt_in": "BOLA_LAB_OPT_IN",
            "bind_host": "BOLA_BIND_HOST",
            "publish_host": "BOLA_PUBLISH_HOST",
            "port": "BOLA_PORT",
            "token_ttl_seconds": "BOLA_TOKEN_TTL_SECONDS",
        }
        return cls.model_validate(
            {key: os.environ[name] for key, name in keys.items() if name in os.environ}
        )
