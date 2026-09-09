# DevLens

AI-powered GitHub repository analysis and engineering insights platform.

## Current Status: Phase 5B (GitHub OAuth Authentication & User Accounts)

DevLens is currently in **Phase 5B: GitHub OAuth Authentication & User Accounts**.
* **GitHub OAuth 2.0 Integration:** Secure authentication flow using GitHub OAuth 2.0 with state-based CSRF protection, exchange of authorization codes, and automated retrieval of verified email and user profiles.
* **Database-Backed Session Management:** PostgreSQL-backed sessions with SHA-256 token hashing (`user_sessions` table). Raw session tokens are never stored in the database. Supports immediate server-side revocation on logout, automatic expiration, and strict cookie security attributes (`HttpOnly`, `SameSite=Lax`, configurable `Secure` flag).
* **Multi-Tenant Repository Ownership:** Repositories and analysis runs are scoped to authenticated users with cascade deletion and isolated composite uniqueness (`uq_repositories_user_id_github_url`), allowing multiple users to independently analyze the same repository without cross-user leakage.
* **Strict Ownership Authorization:** Strict resource authorization preventing ID enumeration (returns 404 for unauthorized repositories and analysis runs). Legacy repositories with `user_id = NULL` are strictly quarantined from user-scoped APIs until ownership is explicitly established (no NULL ownership bypass).
* **PostgreSQL Persistence Foundation (Phase 5A):** Enterprise persistence backed by PostgreSQL 16, SQLAlchemy 2.x ORM, Alembic migrations, and psycopg 3 native binary driver.
* **UUID-based Relational Data Model:** 
  * `users`: Authenticated user accounts with unique indexed GitHub user IDs, logins, emails, avatar URLs, and timestamps.
  * `user_sessions`: Database-backed sessions storing SHA-256 token digests, user references, expiration timestamps, and revocation flags.
  * `repositories`: Ingested GitHub repositories scoped by user ownership, owner/name indices, star/fork/issue metrics, and timestamps.
  * `analysis_runs`: Granular execution tracking with execution statuses (`pending`, `running`, `completed`, `failed`), analysis types (`deterministic`, `ai`, `full`), lifecycle timestamps, safe error messages, and native `JSONB` payloads for deterministic and AI reports.
* **AI Intelligence Layer (Phase 4):** Leverages Google Gemini via the official `google-genai` SDK with strict JSON schema enforcement to produce structured engineering reviews.
* **Deterministic Analysis Engine (Phase 3):** Measures code line metrics, classifies repo files, detects languages by extension, and runs code quality and security scanners.
* **Intelligent Evidence Selector:** Deterministically ranks and curates high-relevance source code files while strictly enforcing token limits and redacting sensitive credentials.
* **Defense-in-Depth Security:** Zero client secret exposure, HttpOnly session handling, pre-submission secret redaction, and prompt-injection defenses.
* **100% Offline Test Isolation:** Comprehensive 103-test backend test suite running with isolated database sessions, mocked OAuth/Gemini services, and full Alembic migration coverage.

> [!NOTE]
> **Advisory Disclaimer:** DevLens AI recommendations, ratings, and assessments are advisory and should be reviewed and verified by human engineering teams prior to making production changes.

---

## Tech Stack

* **Frontend:** React (v19), Vite (v8), TypeScript, Tailwind CSS (v4), Lucide Icons
* **Backend:** Python (3.13), FastAPI, Uvicorn, Pydantic v2, `google-genai`
* **Authentication & Security:** GitHub OAuth 2.0, Database-backed sessions with SHA-256 digests, HttpOnly/SameSite cookies
* **Persistence:** PostgreSQL 16, SQLAlchemy 2.x, Alembic 1.13+, psycopg 3
* **Containerization:** Docker, Docker Compose
* **Testing:** Pytest (103 tests), HTTPX, AnyIO, SQLite in-memory test harness

---

## Project Structure

```text
devlens/
├── .github/
│   └── workflows/
│       └── ci.yml                     # GitHub Actions CI workflow
├── backend/
│   ├── alembic.ini                    # Alembic migration configuration
│   ├── migrations/                    # Alembic database migration scripts
│   │   ├── env.py                     # Dynamic DB URL and metadata binding
│   │   └── versions/
│   │       ├── 0001_initial_schema.py # Initial DDL for repositories & analysis_runs
│   │       └── 0002_add_users_and_auth.py # Users, user_sessions & repository ownership schema
│   ├── app/
│   │   ├── api/                       # API endpoints & route handlers
│   │   │   ├── auth.py                # GitHub OAuth login, callback, logout, me
│   │   │   ├── repositories.py        # Ingestion, analysis runs, and repo queries
│   │   │   └── analyses.py            # GET /api/analyses/{analysis_id}
│   │   ├── core/                      # Config, security, and global settings
│   │   │   ├── config.py              # Env variables, OAuth credentials, CORS
│   │   │   └── security.py            # Token generation, SHA-256 hashing, OAuth CSRF state
│   │   ├── db/                        # Database session & base declarative models
│   │   │   ├── base.py                # Base(DeclarativeBase)
│   │   │   └── session.py             # Engine, SessionLocal, get_db dependency
│   │   ├── models/                    # SQLAlchemy & Pydantic models
│   │   │   ├── user.py                # User entity model (UUID PK, GitHub user ID)
│   │   │   ├── user_session.py        # UserSession entity model (token_hash, revocation, expiration)
│   │   │   ├── repository.py          # Repository entity model (user_id FK, composite unique index)
│   │   │   ├── analysis.py            # AnalysisRun entity model & status/type enums
│   │   │   └── ai_models.py           # AIAnalysisReport Pydantic schema
│   │   ├── schemas/                   # Pydantic persistence schemas
│   │   │   ├── auth_schemas.py        # UserResponse, AuthStatusResponse
│   │   │   └── persistence_schemas.py # RepositoryResponse, AnalysisRunResponse
│   │   ├── services/                  # Business logic & persistence services
│   │   │   ├── user_service.py        # User profile CRUD & lookup operations
│   │   │   ├── session_service.py     # Database session creation, verification & revocation
│   │   │   ├── repository_persistence.py # Repository CRUD & ownership validation
│   │   │   ├── analysis_persistence.py   # Analysis run lifecycle & parent authorization
│   │   │   ├── github_url.py          # URL Parser Utility
│   │   │   ├── github_service.py      # GitHub API Client (metadata, tree, file contents)
│   │   │   ├── ai_prompts.py          # System prompts & injection defense boundaries
│   │   │   └── ai_service.py          # Gemini client wrapper & schema validation
│   │   ├── analyzers/                 # Deterministic static analysis scanners
│   │   │   ├── language_detector.py   # Matches extensions to language
│   │   │   ├── file_classifier.py     # Groups files into source, test, docs, etc.
│   │   │   ├── metrics_analyzer.py    # Counts total, code, comment, and blank lines
│   │   │   ├── security_analyzer.py   # Checks for credentials & masks values
│   │   │   ├── code_quality_analyzer.py # Audits TODOs, print statements, exceptions
│   │   │   ├── evidence_selector.py   # Curates, ranks, and redacts evidence for AI
│   │   │   └── repository_analyzer.py # Orchestrates analysis compile pipeline
│   │   └── main.py                    # FastAPI entrypoint and router registration
│   ├── tests/                         # Pytest test suite (103 tests)
│   │   ├── conftest.py                # In-memory SQLite session fixture & auth overrides
│   │   ├── test_auth_oauth.py         # GitHub OAuth login & callback tests
│   │   ├── test_auth_session.py       # Session token lifecycle, revocation & cookie tests
│   │   ├── test_authorization.py      # Cross-user isolation, NULL user_id quarantine & multi-tenancy tests
│   │   ├── test_security_auth.py      # Secret leakage & cookie security attribute tests
│   │   ├── test_user_model.py         # User & UserSession model uniqueness & cascade delete tests
│   │   ├── test_database_config.py    # DB URL normalization & config validation
│   │   ├── test_models.py             # Model constraints, validations, cascade deletes
│   │   ├── test_repository_persistence.py # Repository CRUD service tests
│   │   ├── test_analysis_persistence.py   # AnalysisRun lifecycle & payload tests
│   │   ├── test_api_persistence.py    # Endpoints persistence integration tests
│   │   ├── test_ai_models.py          # Pydantic AI schema tests
│   │   ├── test_ai_redaction.py       # Secret redaction tests
│   │   ├── test_evidence_selector.py  # Evidence ranking & limits tests
│   │   ├── test_ai_service.py         # Mocked Gemini AI client tests
│   │   ├── test_api_ai.py             # POST /analyze/ai endpoint tests
│   │   ├── test_api_report.py         # POST /analyze/report endpoint tests
│   │   ├── test_health.py             # Backend health test
│   │   ├── test_url_parser.py         # URL validation tests
│   │   └── ...                        # Analyzer unit tests
│   ├── Dockerfile                     # Container image configuration
│   ├── requirements.txt               # Production & development requirements
│   └── .env.example                   # Backend environment variables template
├── frontend/
│   ├── src/
│   │   ├── App.tsx                    # Main dashboard with authentication status & user profile
│   │   ├── index.css                  # Main Tailwind stylesheet
│   │   ├── types.ts                   # TypeScript type declarations (including User)
│   │   └── main.tsx                   # React entry point
│   ├── package.json                   # Frontend dependencies and scripts
│   └── vite.config.ts                 # Vite bundler configuration
├── docker-compose.yml                 # PostgreSQL 16 + Backend + Frontend
└── README.md                          # Project documentation (this file)
```

---

## API Endpoints

### 1. Authentication Endpoints (Phase 5B)

* **`GET /api/auth/github/login`**
  * Initiates GitHub OAuth flow. Generates signed CSRF state, stores it in an HttpOnly cookie, and redirects to GitHub's authorization URL.
  * Response: `302 Found` (redirect to `github.com/login/oauth/authorize`)

* **`GET /api/auth/github/callback`**
  * Handles OAuth redirect from GitHub. Validates CSRF state, exchanges authorization code for an access token, fetches the user's GitHub profile and verified email, creates or updates the local `User` record, sets a signed HttpOnly session cookie, and redirects back to the frontend.
  * Query Params: `code`, `state` (or `error`, `error_description`)
  * Response: `302 Found` (redirect to `FRONTEND_URL`)

* **`POST /api/auth/logout`**
  * Clears the HttpOnly session cookie.
  * Response: `{"message": "Logged out successfully"}`

* **`GET /api/auth/me`**
  * Returns the authenticated user's profile. Requires valid session cookie. Never exposes tokens or secrets.
  * Response: `UserResponse` (`id`, `github_login`, `name`, `email`, `avatar_url`, `created_at`)

### 2. Persistence & History Endpoints (Phase 5A/5B)

* **`GET /api/repositories/{repository_id}`**
  * Retrieves persisted repository record by UUID. Requires authentication and user ownership (returns `404 Not Found` if unowned or owned by another user to prevent ID enumeration).
  * Response: `RepositoryResponse`

* **`GET /api/repositories/{repository_id}/analyses?limit=20`**
  * Retrieves chronological execution history of analysis runs for a repository. Requires authentication and user ownership.
  * Response: `List[AnalysisRunSummaryResponse]`

* **`GET /api/analyses/{analysis_id}`**
  * Retrieves full analysis run record, including complete deterministic and AI JSONB payloads. Enforces user ownership via parent repository.
  * Response: `AnalysisRunResponse`

### 3. Analysis Execution Endpoints

* **`POST /api/repositories/analyze/ai`**
  * Requires authentication. Ingests repository, executes deterministic analysis, curates redacted evidence, runs Gemini AI evaluation, persists repository and completed/failed analysis run record scoped to the authenticated user in PostgreSQL, and returns validated AI assessment.
  * Request: `{"url": "https://github.com/owner/repository"}`
  * Response: `AIAnalyzeResponse`

* **`POST /api/repositories/analyze/report`**
  * Requires authentication. Ingests repository, runs deterministic static analysis engine, persists repository and analysis run record scoped to user, and returns structured engineering report.
  * Request: `{"url": "https://github.com/owner/repository"}`
  * Response: `AnalysisReport`

* **`POST /api/repositories/analyze`**
  * Requires authentication. Ingests repository metadata and file tree, persists repository record scoped to user, and returns metadata and tree.
  * Request: `{"url": "https://github.com/owner/repository"}`
  * Response: `AnalyzeResponse`

---

## Local Setup & Testing

### 1. GitHub OAuth App Configuration (Phase 5B)

To enable GitHub login in local development:
1. Navigate to **GitHub Settings > Developer settings > OAuth Apps > New OAuth App** (`https://github.com/settings/applications/new`).
2. Register the application:
   * **Application name:** `DevLens Local`
   * **Homepage URL:** `http://localhost:5173`
   * **Authorization callback URL:** `http://localhost:8000/api/auth/github/callback`
3. Generate a new Client Secret and record your **Client ID** and **Client Secret**.

### 2. Database Setup (PostgreSQL 16)

Using Docker Compose:
```bash
docker compose up -d devlens-postgres
```

Or using an existing local PostgreSQL instance:
```bash
# Set environment variable in backend/.env:
DATABASE_URL=postgresql+psycopg://devlens:devlens@localhost:5432/devlens
```

Apply database migrations (all revisions up to head):
```bash
cd backend
alembic upgrade head
```

### 3. Backend Setup
```bash
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1   # (Windows)
pip install -r requirements.txt
copy .env.example .env
```

Edit `backend/.env` to configure your credentials:
```ini
DATABASE_URL=postgresql+psycopg://devlens:devlens@localhost:5432/devlens
GEMINI_API_KEY=your_gemini_api_key_here

# GitHub OAuth (Phase 5B)
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret
GITHUB_REDIRECT_URI=http://localhost:8000/api/auth/github/callback
SECRET_KEY=generate_a_random_64_char_hex_secret_here
FRONTEND_URL=http://localhost:5173
SESSION_COOKIE_SECURE=False  # Set to True in production HTTPS
```

Start the API server:
```bash
uvicorn app.main:app --reload
```

### 4. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### 5. Running Automated Tests
The automated test suite runs completely offline with mocked Gemini calls, mocked OAuth exchanges, and in-memory SQLite database isolation:
```bash
cd backend
python -m pytest
```

### 6. Running Frontend Build
```bash
cd frontend
npm run build
```

---

## Roadmap

- [x] **Phase 1: Project Scaffolding** — Scaffolding foundations, FastAPI CORS configurations, basic dashboard layout, Docker and Actions setup.
- [x] **Phase 2: Ingestion Layer** — Branch trees matching, repository metadata, error structures.
- [x] **Phase 3: Repository Analysis Engine** — AST-free line metrics calculation, extensions language detector, quality audit logs, secret masks, and Deep Scan reporting dashboards.
- [x] **Phase 4: Gemini AI Intelligence Layer** — Structured AI engineering assessment, evidence selector with deterministic ranking, secret redaction, prompt injection defense, and frontend AI Review dashboard.
- [x] **Phase 5A: PostgreSQL Persistence Layer** — PostgreSQL 16 persistence, SQLAlchemy 2.x, Alembic migrations, psycopg3 driver, UUID models, JSONB payloads, and historical query endpoints.
- [x] **Phase 5B: User Authentication & OAuth** — GitHub OAuth 2.0, user accounts, secure signed session cookies (HMAC-SHA256), repository multi-tenancy & ownership isolation.
- [ ] **Phase 6: Analysis History & Dashboard** — User analysis dashboard, trend tracking, and multi-repo comparison.
