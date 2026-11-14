"""Small synchronous Psycopg boundary; each context commits or rolls back atomically."""

from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row

from bola_lab.config import Settings


@contextmanager
def connect(settings: Settings) -> Iterator[psycopg.Connection]:
    with psycopg.connect(
        settings.database_url.get_secret_value(),
        row_factory=dict_row,
        connect_timeout=5,
        options="-c timezone=UTC -c statement_timeout=5000 -c lock_timeout=5000",
    ) as connection:
        yield connection
