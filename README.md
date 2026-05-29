# carpix-images

FastAPI microservice that serves car images by brand, model, and year. First request fetches a CC-licensed image from Wikimedia Commons and caches it locally; all subsequent requests are served from disk.

## How it works

```
GET /v1/images/{brand}/{model}/{year}
```

1. Check PostgreSQL cache for a stored image path
2. Cache hit → serve from `/images/{brand}/{model}/{year}/image.jpg`
3. Cache miss → query Wikimedia Commons API, download 800px thumbnail, store on disk, record in DB, serve

Response always includes `X-Cache: HIT` or `X-Cache: MISS`.

Extraction failures return `404`. No `500`s.

## API

| Endpoint | Description |
|---|---|
| `GET /v1/images/{brand}/{model}/{year}` | Returns JPEG image |
| `GET /health` | Health check |

**Example:**
```
GET /v1/images/toyota/camry/2020
```

## Quick start

```bash
docker compose up
```

Service available at `http://localhost:8001`.

Runs DB migrations automatically on startup via `alembic upgrade head`.

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | required | PostgreSQL DSN (`postgresql+asyncpg://...`) |
| `IMAGES_DIR` | `/images` | Filesystem path for image cache |

## Development

**Requirements:** Python 3.12+, [uv](https://docs.astral.sh/uv/)

```bash
# Install deps
uv sync

# Run linters
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy src

# Run tests
uv run pytest tests -v
```

Integration tests use [testcontainers](https://testcontainers-python.readthedocs.io/) — Docker must be running.

## Storage layout

```
/images/
  {brand_key}/
    {model_key}/
      {year}/
        image.jpg
```

Keys are normalized (lowercased, spaces → underscores).

## Stack

- **FastAPI** — async HTTP framework
- **asyncpg** + **SQLAlchemy 2.0** — async PostgreSQL
- **httpx** — async Wikimedia API client
- **respx** — httpx mock transport for tests
- **Alembic** — DB migrations
- **ruff** + **mypy** — lint and type checking
- **uv** — dependency management

## CI

GitHub Actions runs lint (`ruff`, `mypy`) and tests on every push and PR to `main`.
