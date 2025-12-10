# Copilot Instructions for Projection-2

## Architecture Overview

**Projection-2** is a microservices application with a React frontend, dual backend services (Python FastAPI + Go), PostgreSQL database, and comprehensive observability via Traefik, Loki, Vector, and Grafana.

### Service Topology
- **Frontend** (React + Vite): Served via NGINX, accessible at `app.test` through Traefik
- **Backend-Python** (FastAPI): Main API service at `api.test/api`, communicates with Go service internally
- **Backend-Go** (HTTP server): Internal-only service (port 9000), no public exposure, called by Python via `http://backend-go:9000`
- **PostgreSQL 16**: Shared database for all services via `DATABASE_URL`
- **Traefik v3.6.4**: Reverse proxy/load balancer routing via Host headers (`.test` domains only)
- **Loki + Vector + Grafana**: Centralized logging infrastructure (Loki on 3100, Grafana on 3001)

### Network Communication Pattern
```
HTTP Client → Traefik (Host router) → Frontend/API
Python API → (httpx.get) → Go Service (internal only)
Both services → PostgreSQL (psycopg2/pq driver)
All logs → Vector → Loki (real-time ingestion)
```

## Critical Workflows

### Local Development
```bash
# .env.dev used; services have hot-reload volumes
docker compose -f docker-compose.dev.yml --env-file .env.dev up --build

# Frontend dev server runs at http://localhost:3000 with Vite HMR
# Python API runs at http://localhost:8000 (direct access)
# Go service at http://localhost:9000 (direct access)
# Database at localhost:5432 with live SQL initialization
```

### Production Build
```bash
# Uses .env file (not .env.dev), no hot-reload
docker compose -f docker-compose.yml --env-file .env up --build -d

# Access via Traefik-routed domains:
# - Frontend: http://app.test
# - API: http://api.test/api
# - Traefik dashboard: http://traefik.test
```

**Prerequisites:** Add to `/etc/hosts` (requires sudo):
```
127.0.0.1   app.test
127.0.0.1   api.test
127.0.0.1   traefik.test
127.0.0.1   mermaid.test
```
Without host entries, browsers won't send `Host` headers; Traefik won't match routes → 404 errors.

### Database Initialization
- `db/00-init.sql`: Runs once on container startup (extensions, schemas, example tables)
- `db/01-audit.sql`: Immutable audit log table with triggers preventing updates/deletes
- Both files mounted as Docker entry-point scripts; re-initializes on volume recreation

## Key Conventions & Patterns

### Audit Logging (Cross-Language Pattern)
Every request logs to `audit_log` table via middleware:
- **Python** (`backend-python/audit.py`): `audit_log()` function, called in FastAPI middleware
- **Go** (`backend-go/audit.go`): `AuditLog()` function, accepts `*sql.DB`
- Schema: timestamp, service name, user_id, action, entity, entity_id, request_ip, details (JSONB)
- **Immutable by design**: Database triggers prevent updates/deletes (compliance: SOC2, ISO, HIPAA, POPIA)

### Inter-Service Communication
- Python FastAPI uses **httpx** (async HTTP) to call Go at `GO_SERVICE_URL` env var
- Example: `backend-python/main.py` `call_go()` endpoint → `GET http://backend-go:9000/internal`
- Go runs on port 9000 (not exposed publicly, only internal network)
- Connection strings use Docker service names (`backend-go`, `db`), not IPs

### Environment & Configuration
- `.env.example`: Template for required vars (POSTGRES_*, GO_SERVICE_URL, PYTHON_SERVICE_URL)
- `.env.dev`: Development overrides (used by dev compose)
- `.env`: Production secrets (git-ignored)
- Both Python and Go read via `os.getenv()`; no config files

### Frontend Build & Deployment
- **Vite + React 19** (no TypeScript, plain JS modules)
- Build output: `frontend/dist/` (served by NGINX from `/usr/share/nginx.html`)
- ESLint config: `eslint.config.js` (flat config, ignores `dist`, enforces no unused vars except ALL_CAPS)
- Dev: `npm run dev` starts Vite server; prod: multi-stage Docker build (Node 20 Alpine → NGINX 1.25)

### Python Backend Specifics
- **FastAPI** with **uvicorn** on port 8000
- Middleware pattern: request audit logging via `@app.middleware("http")`
- Dependencies: fastapi, uvicorn, httpx (cross-service), psycopg2-binary (PostgreSQL)
- Health check: `GET /ping` returns `{"message": "Python backend up"}`

### Go Backend Specifics
- Minimal stdlib HTTP server (no frameworks)
- Database: `github.com/lib/pq` driver (requires `go.mod` update if adding deps)
- Runs on port 9000; only exposes `/internal` endpoint
- Audit logging uses `time.Now().UTC()` and JSON marshaling for details

### Observability
- **Loki**: Centralized log storage (real-time, no auth required locally)
  - Access: `http://localhost:3100` (API) or via Grafana dashboard
  - Query logs by service name: `{service="backend-python"}` or `{service="backend-go"}`
  - Retention: Configured in `infra/loki/local-config.yaml` (default 30s chunk retain, 1h idle period)
- **Vector**: Collects all container logs via Docker socket, excludes itself/Grafana/Loki
  - Config: `infra/vector/vector.toml` — parses JSON, enriches with service field
  - Real-time streaming to Loki; no buffering issues on macOS (uses proper socket mount)
- **Traefik**: Configured for local `.test` domains, no HTTPS redirect (avoids TLS issues), no Let's Encrypt
  - Dashboard: `http://traefik.test` (shows routers, services, middleware)
  - Config: `infra/traefik/traefik.yml` — Docker provider auto-detects labels
- **Grafana**: Dashboard UI at `http://localhost:3001` (default credentials: admin/admin)
  - Pre-configured data source: Loki at `http://loki:3100`
  - Add panels by querying logs: e.g., `{service="backend-python"} | json`
  - Annotations: Track audit events via `action="http_request"` filter

### Mermaid Editor & Diagram Storage
- Mermaid Live Editor runs on `mermaid.test`, embedded in frontend via iframe
- **DiagramEditor component** (`frontend/src/DiagramEditor.jsx`): Full-featured diagram manager
  - Sidebar: Lists saved diagrams from PostgreSQL
  - Main area: Embedded Mermaid iframe for editing
  - PostMessage API: Parent window communicates with Mermaid iframe
- **Storage architecture**:
  - Diagram content → MinIO S3 storage (`.mmd` files)
  - Metadata → PostgreSQL `diagrams` table (title, description, s3_key, tags, timestamps)
- **Backend endpoints** (`backend-python/main.py`):
  - `POST /api/diagrams`: Save new diagram (uploads to S3, creates DB record)
  - `GET /api/diagrams`: List all diagrams with pagination
  - `GET /api/diagrams/{id}`: Get diagram metadata with presigned S3 URL
  - `GET /api/diagrams/{id}/content`: Fetch raw diagram content from S3
  - `DELETE /api/diagrams/{id}`: Remove diagram from both S3 and database
- **MinIO service**: S3-compatible storage on port 9000 (API), 9001 (console)
- **S3 module** (`backend-python/s3_storage.py`): Handles all MinIO operations

## Testing & Quality Assurance

### Test Structure
- **No existing test suite yet** — create tests in `backend-python/tests/` and `backend-go/tests/`
- **Python**: Use pytest with fixtures for database and httpx mocking
  - Example: `backend-python/tests/test_main.py` with `@pytest.fixture` for test DB connection
  - Add to `requirements.txt`: `pytest`, `pytest-asyncio`, `httpx` (for mocking)
  - Run: `pytest backend-python/tests/` from root
- **Go**: Use `testing` stdlib with `*testing.T`
  - Example: `backend-go/*_test.go` following Go convention
  - Test database: Create separate test DB or use Docker ephemeral container
  - Run: `go test ./...` from `backend-go/` directory
- **Frontend**: Use Vitest (configured in Vite) for component tests
  - ESLint already enforces no unused vars (aids in test cleanup)
  - Place tests alongside components: `src/App.test.jsx`

### Audit Log Testing
- Verify `audit_log` table receives records after each endpoint call
- Test immutability: attempt UPDATE/DELETE on audit_log should raise exception
- Mock user_id via `X-User-ID` header in Python tests

### CI/CD Setup (Future)
- Add `.github/workflows/test.yml` to run pytest + go test + npm test on PR
- Ensure environment variables loaded from `.env.example` for test runs

## Implementation Guidance

### Adding a New Endpoint (Python)
1. Add route to `backend-python/main.py`
2. Middleware automatically logs all requests; no extra audit code needed
3. If calling Go: use `httpx.get(f"{GO_SERVICE_URL}/path")`
4. Test: `curl http://localhost:8000/your-route` (dev) or redeploy compose

### Adding a Database Feature
1. Create `.sql` file in `db/` directory
2. Prefix with sequence number (`02-feature.sql`)
3. Add mount to both docker-compose files: `- ./db/02-feature.sql:/docker-entrypoint-initdb.d/02-feature.sql`
4. Delete `db_data` volume to re-run init scripts: `docker volume rm <project>_db_data`

### Adding Python Dependencies
1. Update `backend-python/requirements.txt`
2. Rebuild: `docker compose -f docker-compose.yml build backend-python`
3. Restart: `docker compose up -d backend-python`

### Adding Go Dependencies
1. Update `go.mod` with `go get` or manual edit
2. Rebuild: `docker compose -f docker-compose.yml build backend-go`
3. Restart: `docker compose up -d backend-go`

### Frontend Changes
1. Edit files in `frontend/src/`
2. Dev: Vite HMR auto-reloads browser (via Vite dev server)
3. Prod: Run `npm run build` in container, output to `dist/` (NGINX serves this)

## Common Troubleshooting

**"404 Page not Found" from Traefik**
→ Check `/etc/hosts` has `.test` entries; verify `Host` header in browser request

**Python can't reach Go service**
→ Verify `GO_SERVICE_URL=http://backend-go:9000` in `.env` or `.env.dev`; ensure Go service is running

**Database initialization didn't run**
→ Delete volume: `docker volume rm <project>_db_data`; recreate with `docker compose up`

**Audit logs missing**
→ Check `audit_log` table exists; verify service name in audit_log() call matches expected value

## Deployment & Environments

### Development vs. Production
| Aspect | Dev | Prod |
|--------|-----|------|
| Compose file | `docker-compose.dev.yml` | `docker-compose.yml` |
| Env file | `.env.dev` | `.env` |
| Frontend | Vite dev server (port 3000, HMR) | NGINX (port 80) |
| Ports | All exposed (3000, 8000, 9000, 5432) | Only 80/443 via Traefik |
| Volumes | Live code mounts (hot-reload) | Immutable builds |
| Database | Fresh init on startup | Persistent `db_data` volume |

### Build & Push (Future Container Registry)
1. Tag image: `docker build -t <registry>/projection2-backend-python:v1.0.0 ./backend-python`
2. Push: `docker push <registry>/projection2-backend-python:v1.0.0`
3. Update compose: change `build:` to `image:` with new tag
4. Orchestrate: Add Kubernetes manifests or Docker Swarm stacks (not currently in repo)

### Environment Variables in Prod
- `.env` file (git-ignored) must have real credentials:
  - `POSTGRES_PASSWORD`: Strong password (min 16 chars, special chars)
  - `GO_SERVICE_URL`, `PYTHON_SERVICE_URL`: Use internal Docker service names (same as dev)
- Optionally use secrets management (Vault, AWS Secrets Manager) — update `os.getenv()` calls to fetch from external provider
