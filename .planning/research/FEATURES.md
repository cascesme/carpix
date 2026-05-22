# Features Research: Vehicle Image Cache Microservice

**Domain:** Image proxy/cache microservice (internal, read-only, single upstream source)
**Researched:** 2026-05-22
**Confidence:** HIGH for table stakes (well-established HTTP/cache conventions); MEDIUM for differentiator scope

---

## Table Stakes (Must Have v1)

These are the features without which the service cannot fulfill its core contract or will confuse callers.

- **Cache-hit path returns stored file immediately**: Any request for a previously fetched vehicle must bypass Wikimedia entirely and serve from local disk. The entire value proposition collapses without this. — Complexity: Low
- **Cache-miss path fetches, stores, then serves**: A miss must atomically fetch from Wikimedia, write to disk, insert the DB row, and return the file in the same request — no "come back later" pattern. — Complexity: Med
- **Correct Content-Type header (`image/jpeg`)**: FastAPI FileResponse infers media type from the `.jpg` extension automatically, but it must be `image/jpeg` (IANA standard) not `image/jpg`. Browsers use this header — not file extension — to decode the response. — Complexity: Low
- **Deterministic input normalization**: `brand` and `model` path parameters must be normalized (lowercase + strip non-alphanumeric) before cache lookup so `/v1/images/Toyota/Corolla/2023` and `/v1/images/toyota/corolla/2023` hit the same cache row. Must match parent project's `domain/vehicle_identity.py` logic exactly. — Complexity: Low
- **Clean 404 on no-results or download failure**: Any Wikimedia failure — no search results, URL resolution fails, thumbnail download fails — returns `{"detail": "No image found for this vehicle"}` with HTTP 404. The service must never return a 500 to callers. — Complexity: Low
- **GET /health liveness endpoint**: Returns HTTP 200 when the process is alive. Required for Docker/Compose health checks and any orchestrator probe. Minimal response body (empty or `{"status": "ok"}`). Industry standard for containerized services (imgproxy, every k8s-deployed service). — Complexity: Low
- **Persistent storage across restarts**: Images must survive container restarts via a Docker volume mount at `/images`. Without this, every restart triggers a full re-fetch for all previously warmed keys, which defeats the cache entirely. — Complexity: Low
- **Filesystem path structure is stable**: The path `/images/{brand_key}/{model_key}/{year}/image.jpg` must be consistent — the DB stores this path and the FileResponse reads it. A change breaks all existing rows. Lock this in v1 and do not vary it. — Complexity: Low
- **DB row insert is idempotent**: If two concurrent requests race for the same cold key, the second insert must not raise a constraint error. Use `INSERT ... ON CONFLICT DO NOTHING` on the composite PK `(brand_key, model_key, year)`. — Complexity: Low

---

## Differentiators (Nice to Have, Could Defer)

These add observable value but are not required for the service to be correct or useful in v1.

- **`X-Cache: HIT` / `X-Cache: MISS` response header**: A lightweight debug header that lets callers and developers instantly tell whether a response was served from disk or triggered a Wikimedia fetch. Industry convention (Nginx, Varnish, Fastly all use this). Zero cost to add; high diagnostic value. — Complexity: Low
- **Structured health check with dependency status**: `/health` returns `{"status": "ok", "db": "ok"}` by making a cheap DB probe (e.g., `SELECT 1`). Distinguishes between "process alive" and "process alive but cannot reach Postgres". Useful once the service is deployed alongside a DB. — Complexity: Low
- **`ETag` + `Last-Modified` cache headers on FileResponse**: FastAPI FileResponse sets `ETag` and `Last-Modified` automatically from the file metadata. Callers (e.g., the parent carpix app) can send `If-None-Match` / `If-Modified-Since` and receive 304 Not Modified, halving network traffic for repeated hot requests. Zero implementation cost — these headers are already emitted. — Complexity: Low
- **`Cache-Control: public, max-age=…` response header**: Tells any intermediate proxy or CDN how long to cache the image response. Since images in this system are permanent (no TTL), a long max-age (e.g., 1 year) is safe and reduces repeat hits to this service. — Complexity: Low
- **Concurrent-request deduplication (singleflight)**: If 10 requests arrive simultaneously for the same cold key, only one should trigger the Wikimedia fetch; the others should wait and share the result. Prevents thundering-herd against Wikimedia and duplicate DB inserts. Python: asyncio.Event or a per-key lock dict. Relevant at any traffic volume because Wikimedia fetch takes ~1–3s. — Complexity: Med
- **Prometheus metrics endpoint (`/metrics`)**: Expose hit/miss counter, Wikimedia fetch latency histogram, active in-flight fetches. Useful for observability once the service is running in production. Not needed in v1 where traffic is low and behavior is observable via logs. — Complexity: Med

---

## Anti-Features (Deliberately Exclude from v1)

Features to explicitly not build. Each entry names the exclusion reason and whether it belongs in a future version or never.

- **TTL / cache expiration**: Vehicle images on Wikimedia Commons are stable — a 2023 Toyota Corolla photo does not change. TTL adds background invalidation jobs, stale-while-revalidate complexity, and DB schema changes (expires_at column). Project constraint: cache is permanent. — Defer to v2? Only if a specific requirement for freshness emerges; currently "never" is correct.
- **Image resizing (local PIL/Pillow)**: Wikimedia CDN handles 800px thumbnail server-side via the `/thumb/` URL pattern. Local resize adds a dependency (Pillow), CPU overhead, and a failure mode (corrupt source → resize crash). — Never for this service; the CDN already solves it.
- **Multiple image sizes per vehicle**: Callers get 800px. Serving 400px, 1200px, etc. requires either local resize (anti-feature above) or multiple Wikimedia fetches and DB rows per vehicle. No stated consumer need for this. — Defer to v2 only if a specific size requirement from a consumer is validated.
- **Authentication / API key enforcement**: This is an internal sibling service in a private Docker network. Auth adds a shared-secret management problem across two repos. No security requirement justifies the coupling. — Never for this architecture; network isolation is the security boundary.
- **Rate limiting**: Wikimedia imposes no enforced rate limit per the project spec. Internal callers are known and bounded. Implementing rate limiting before observing any actual abuse is premature. — Defer to v2 only if Wikimedia requests or internal misuse become a real problem.
- **Pagination or batch endpoints**: The API contract is single vehicle → single image. A batch endpoint (`POST /v1/images/batch`) would complicate the response contract (partial success, mixed 200/404), the DB write pattern, and testing. No consumer need stated. — Defer to v2 only if the parent app needs bulk prefetching.
- **Admin or cache-management endpoints**: `DELETE /v1/images/{brand}/{model}/{year}` to invalidate a cache entry, or `POST /v1/cache/warm` to prefetch. These require operator auth, audit trail, and error semantics that are out of scope. The filesystem and DB can be managed directly in v1. — Defer to v2 if cache management becomes a recurring operational need.
- **Webhook or async notification on cache miss**: Returning a "processing" response and notifying via callback when the image is ready adds an async job queue (Celery, ARQ), a callback registration mechanism, and retry/failure handling. Wikimedia fetches complete in under 5 seconds; synchronous is fine. — Never for this service.
- **CDN integration or edge caching layer**: Varnish/CloudFront in front of this service would be overkill for an internal sibling container. The parent app is the only caller. — Never for this deployment topology.
- **Image format conversion (JPEG → WebP/AVIF)**: Source images from Wikimedia are already JPEG. Format negotiation via `Accept: image/webp` adds content-type branching, conversion logic, and separate cache entries per format. No consumer requirement. — Defer to v2 only if a browser-facing consumer requires WebP.

---

## Feature Dependencies

```
Persistent storage (Docker volume)
  └─ Cache-hit path (FileResponse reads from disk)
  └─ Cache-miss path (writes to disk, then reads)
       └─ DB row insert (records local_path, source_url, etc.)
            └─ Idempotent insert (ON CONFLICT DO NOTHING)

Input normalization
  └─ Cache lookup (DB query uses brand_key, model_key)
  └─ Filesystem path construction (uses same normalized keys)

GET /health
  └─ (no dependencies — must succeed even if DB is down for basic liveness)
  └─ Structured health (DB reachability check — depends on DB connection pool)

X-Cache header
  └─ Cache-hit path (emits MISS on Wikimedia fetch, HIT on disk serve)

Concurrent deduplication
  └─ Cache-miss path (wraps the Wikimedia fetch + DB write in a per-key lock)
  └─ Idempotent insert (still needed as a safety net even with deduplication)
```

---

## Sources

- FastAPI FileResponse headers (Content-Length, Last-Modified, ETag, media_type inference): https://fastapi.tiangolo.com/advanced/custom-response/
- imgproxy health check pattern (HTTP 200, minimal body): https://docs.imgproxy.net/healthcheck
- X-Cache HIT/MISS header convention (Nginx, Varnish, IETF Cache-Status): https://http.dev/x-cache-status
- Cache stampede / thundering herd problem and singleflight mitigation: https://www.stanza.dev/courses/redis-caching/advanced-caching/redis-caching-request-coalescing
- Correct MIME type for JPEG (`image/jpeg`): https://httpref.tools/mime/image/jpeg
- Idempotency in microservices (ON CONFLICT pattern): https://oneuptime.com/blog/post/2026-01-24-idempotency-in-microservices/view
- HTTP caching headers (Cache-Control, ETag, Last-Modified): https://imagekit.io/blog/ultimate-guide-to-http-caching-for-static-assets/
