import os

# Must run before any carpix_images module — Settings() reads env at import time.
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/testdb"
)
