# DevLens

AI-powered GitHub repository analysis and engineering insights platform.

## Current Status: Phase 5A (Production PostgreSQL Persistence Layer)

DevLens is currently in **Phase 5A: Production PostgreSQL Persistence Layer**.
* **PostgreSQL Persistence Foundation:** Enterprise persistence backed by PostgreSQL 16, SQLAlchemy 2.x ORM, Alembic migrations, and psycopg 3 native binary driver.
* **UUID-based Relational Data Model:** 
  * `repositories`: Ingested GitHub repositories with unique indexed URLs, owner/name indices, star/fork/issue metrics, and timestamps.
  * `analysis_runs`: Granular execution tracking with execution statuses (`pending`, `running`, `completed`, `failed`), analysis types (`deterministic`, `ai`, `full`), lifecycle timestamps, safe error messages, and native `JSONB` payloads for deterministic and AI reports.
* **Cascade Lifecycle & Audit History:** Foreign key relationships with cascade deletion ensure automated cleanup, with dedicated APIs for historical analysis queries.
* **Dual-Dialect Compatibility:** Seamless cross-dialect `JSONB` support ensuring full PostgreSQL native features in production and lightning-fast in-memory SQLite isolation for automated unit tests.
* **AI Intelligence Layer:** Leverages Google Gemini via the official `google-genai` SDK with strict JSON schema enforcement to produce structured engineering reviews.
* **Deterministic Analysis Engine:** Measures code line metrics, classifies repo files, detects languages by extension, and runs code quality and security scanners.
* **Intelligent Evidence Selector:** Deterministically ranks and curates high-relevance source code files (prioritizing security findings, code quality issues, and application entrypoints) while strictly enforcing file count, character, and token limits.
* **Defense-in-Depth Security:** Pre-submission secret redaction (masks API keys, passwords, AWS keys, JWTs, and private keys) and strong prompt-injection defenses treating all repository content as untrusted passive data.
* **Frontend AI Review Dashboard:** Interactive AI Review tab displaying executive summaries, architecture reviews, security postures, maintainability ratings, positive engineering observations, and prioritized recommendations.
* **100% Offline Test Isolation:** Comprehensive 75-test backend test suite running with isolated database sessions and mocked external services.

> [!NOTE]
> **Advisory Disclaimer:** DevLens AI recommendations, ratings, and assessments are advisory and should be reviewed and verified by human engineering teams prior to making production changes.

---

## Tech Stack

* **Frontend:** React (v19), Vite (v8), TypeScript, Tailwind CSS (v4), Lucide Icons
* **Backend:** Python (3.13), FastAPI, Uvicorn, Pydantic v2, `google-genai`
* **Persistence:** PostgreSQL 16, SQLAlchemy 2.x, Alembic 1.13+, psycopg 3
* **Containerization:** Docker, Docker Compose
* **Testing:** Pytest, HTTPX, AnyIO, SQLite in-memory test harness

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
│   │       └── 0001_initial_schema.py # Initial DDL for repositories & analysis_runs
│   ├── app/
│   │   ├── api/                       # API endpoints & route handlers
│   │   │   ├── repositories.py        # Ingestion, analysis runs, and repo queries
│   │   │   └── analyses.py            # GET /api/analyses/{analysis_id}
│   │   ├── core/                      # Config, security, and global settings
│   │   │   └── config.py              # Env variables, DATABASE_URL normalization, CORS
│   │   ├── db/                        # Database session & base declarative models
│   │   │   ├── base.py                # Base(DeclarativeBase)
│   │   │   └── session.py             # Engine, SessionLocal, get_db dependency
│   │   ├── models/                    # SQLAlchemy & Pydantic models
│   │   │   ├── repository.py          # Repository entity model
│   │   │   ├── analysis.py            # AnalysisRun entity model & status/type enums
│   │   │   └── ai_models.py           # AIAnalysisReport Pydantic schema
│   │   ├── schemas/                   # Pydantic persistence schemas
│   │   │   └── persistence_schemas.py # RepositoryResponse, AnalysisRunResponse
│   │   ├── services/                  # Business logic & persistence services
│   │   │   ├── repository_persistence.py # Repository CRUD & last_analyzed tracking
│   │   │   ├── analysis_persistence.py   # Analysis run lifecycle, payloads, history
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
│   ├── tests/                         # Pytest test suite (75 tests)
│   │   ├── conftest.py                # In-memory SQLite session fixture & get_db override
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
│   │   ├── App.tsx                    # Main dashboard interface (Quick, Deep, and AI tabs)
│   │   ├── index.css                  # Main Tailwind stylesheet
│   │   ├── types.ts                   # TypeScript type declarations
│   │   └── main.tsx                   # React entry point
│   ├── package.json                   # Frontend dependencies and scripts
│   └── vite.config.ts                 # Vite bundler configuration
├── docker-compose.yml                 # PostgreSQL 16 + Backend + Frontend
└── README.md                          # Project documentation (this file)
```

---

## API Endpoints

### 1. Persistence & History Endpoints (Phase 5A)

* **`GET /api/repositories/{repository_id}`**
  * Retrieves persisted repository record by UUID.
  * Response: `RepositoryResponse`

* **`GET /api/repositories/{repository_id}/analyses?limit=20`**
  * Retrieves chronological execution history of analysis runs for a repository.
  * Response: `List[AnalysisRunSummaryResponse]`

* **`GET /api/analyses/{analysis_id}`**
  * Retrieves full analysis run record, including complete deterministic and AI JSONB payloads.
  * Response: `AnalysisRunResponse`

### 2. Analysis Execution Endpoints

* **`POST /api/repositories/analyze/ai`**
  * Ingests repository, executes deterministic analysis, curates redacted evidence, runs Gemini AI evaluation, persists repository and completed/failed analysis run record in PostgreSQL, and returns validated AI assessment.
  * Request: `{"url": "https://github.com/owner/repository"}`
  * Response: `AIAnalyzeResponse`

* **`POST /api/repositories/analyze/report`**
  * Ingests repository, runs deterministic static analysis engine, persists repository and analysis run record in PostgreSQL, and returns structured engineering report.
  * Request: `{"url": "https://github.com/owner/repository"}`
  * Response: `AnalysisReport`

* **`POST /api/repositories/analyze`**
  * Ingests repository metadata and file tree, persists repository record in PostgreSQL, and returns metadata and tree.
  * Request: `{"url": "https://github.com/owner/repository"}`
  * Response: `AnalyzeResponse`

---

## Local Setup & Testing

### 1. Database Setup (PostgreSQL 16)

Using Docker Compose:
```bash
docker compose up -d db
```

Or using an existing local PostgreSQL instance:
```bash
# Set environment variable in backend/.env:
DATABASE_URL=postgresql+psycopg://devlens:devlens@localhost:5432/devlens
```

Apply database migrations:
```bash
cd backend
alembic upgrade head
```

### 2. Backend Setup
```bash
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1   # (Windows)
pip install -r requirements.txt
copy .env.example .env
```

To enable live Gemini AI reviews:
Edit `backend/.env` and supply your Gemini API key:
```ini
GEMINI_API_KEY=your_gemini_api_key_here
```

Start the API server:
```bash
uvicorn app.main:app --reload
```

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### 4. Running Automated Tests
The automated test suite runs completely offline with mocked Gemini calls and in-memory SQLite database isolation:
```bash
cd backend
python -m pytest
```

### 5. Running Frontend Build
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
- [ ] **Phase 5B: User Authentication & OAuth** — GitHub/Google OAuth, user accounts, JWT sessions.
