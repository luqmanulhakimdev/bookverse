# BookVerse

BookVerse is a book discovery app that searches Open Library and Google Books through a normalized FastAPI API and a responsive React interface. It is being built as a modular monolith; the initial release focuses on public catalog search.

## Implemented features

- Async Open Library and Google Books adapters with explicit connection/request timeouts.
- Unified book response schema, defensive handling for incomplete catalog records, concurrent provider requests, per-provider status, deterministic deduplication and sorting.
- Partial results when a provider fails and HTTP 502 when all enabled providers fail.
- Search validation, bounded pagination inputs, CORS configuration, health endpoints, and generated OpenAPI docs.
- Responsive React search interface with debounced real API requests, source links, preview/reading labels, provider filter, loading/empty/error states, and accessible controls.
- Internal book detail and source comparison pages, secure account flows, a private rated/progress-tracking library, and personalized/similar-book pages.
- Mocked provider and orchestration tests; normal tests make no live requests.
- Project Gutenberg catalog results through Gutendex, with source-reported ebook links and rights notes that distinguish US public-domain signals from worldwide rights.

## Persistence and accounts

The PostgreSQL schema is managed by Alembic. Search records are upserted by `(provider, external_id)`; `Book` is an internal UUID, and each external catalog record remains a separate source record. Run `cd backend && alembic upgrade head` after PostgreSQL is available. Book detail and availability endpoints read the persisted records.

Registration uses Argon2id password hashing. Access tokens are short-lived JWTs returned to the client for in-memory use. Refresh tokens are random opaque values stored only as SHA-256 digests and delivered in an HttpOnly, SameSite=Strict cookie; each refresh rotates the token, and reuse revokes the session family. Set `REFRESH_COOKIE_SECURE=true` behind HTTPS and replace `JWT_SECRET` with a long random secret before deployment. The browser must not persist access tokens in localStorage. Library endpoints always scope reads and writes to the authenticated user and record reading events.

Recommendations use deterministic content features (genre, author, language, and title/description overlap) and return human-readable reasons. Personal recommendations require a signed-in user and never inspect another user's library. The scoring weights and limitations are documented in `docs/architecture.md`.

## Requirements

- Python 3.11 or newer
- Node.js 20 or newer and npm

## Run locally

Start the database and cache first, either by starting everything in containers:

```sh
docker compose up --build
```

or by starting only PostgreSQL and Redis, then running the API and Vite development server with the commands below:

```sh
docker compose up -d db redis
```

```sh
cd backend
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
uvicorn bookverse.main:app --reload
```

Compose applies the migrations before starting the API. The frontend is at `http://localhost:8080`, the API at `http://localhost:8000`, and API docs at `http://localhost:8000/docs`. Its default database password and JWT secret are development-only. Set strong `POSTGRES_PASSWORD` and `JWT_SECRET`, configure the public frontend in `CORS_ORIGINS`, and set `REFRESH_COOKIE_SECURE=true` when serving over HTTPS before deployment.

In another terminal:

```sh
cd frontend
cp .env.example .env
npm install
npm run dev
```

Open the Vite URL (normally `http://localhost:5173`). API docs are at `http://localhost:8000/docs`.

## Configuration

Backend variables are listed in `backend/.env.example`. Provider base URLs, timeout and explicit CORS origins are configurable; CORS origins are comma-separated. The frontend uses `VITE_API_BASE_URL` and contains no private credentials. Do not commit local `.env` files.

## Example requests

```sh
curl 'http://localhost:8000/api/v1/books?q=the%20left%20hand%20of%20darkness&page=1&limit=10'
curl 'http://localhost:8000/api/v1/books?q=earthsea&provider=open_library'
curl 'http://localhost:8000/health'
curl 'http://localhost:8000/ready'
```

The `total` field is null because totals from different provider catalogs are not reliably additive. `fetched_count` describes the unique results fetched for this request, not a global count. Each response includes provider status so partial results are visible to clients.

## Development checks

```sh
cd backend && pytest
cd backend && ruff check .
cd frontend && npm test
cd frontend && npm run build
cd frontend && npm audit --audit-level=high
```

CI runs Ruff, the backend test suite, Alembic migration application against PostgreSQL, frontend tests/build, and npm audit. Redis outages are reported as degraded readiness and bypassed by the cache, while PostgreSQL is required for readiness and persisted endpoints. Provider retries are bounded to one retry for transient failures. Rate limits are process-local; place a shared gateway or distributed limiter in front when horizontally scaling.

## Architecture and limitations

See [docs/architecture.md](docs/architecture.md) for the search flow, conservative title/author matching, and planned data model. This phase does not yet persist catalog records, users, or libraries and does not provide authentication, recommendations, Gutenberg, Redis caching, rate limiting, or container deployment. Open Library's public-scan marker and Google Books preview metadata are source signals, not legal advice or blanket redistribution permissions. Links always lead to their source.

Provider tests use mocked HTTP payloads. If an upstream service is unreachable in development, the UI reports partial provider failure or an actionable error; no synthetic successful results are returned.
