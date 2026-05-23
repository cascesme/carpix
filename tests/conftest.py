import os
from collections.abc import Generator

import pytest
from testcontainers.postgres import PostgresContainer

# Must run before any carpix_images module — Settings() reads env at import time.
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/testdb"
)
os.environ.setdefault("IMAGES_DIR", "/tmp/carpix_test_images")


@pytest.fixture(scope="session")
def postgres_container() -> Generator[str, None, None]:
    with PostgresContainer("postgres:17", driver="asyncpg") as pg:
        url = pg.get_connection_url()
        os.environ["DATABASE_URL"] = url
        yield url
