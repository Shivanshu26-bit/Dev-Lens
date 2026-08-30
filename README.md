# DevLens

AI-powered GitHub repository analysis and engineering insights platform.

## Current Status: Phase 3 (Repository Analysis Engine)

DevLens is currently in **Phase 3: Repository Analysis Engine**.
* **Backend:** Features a deterministic, AST-free analysis engine that measures code line metrics, classifies repo files, detects languages by extension, and runs code quality and security scanners.
* **Frontend:** Features a comprehensive Deep Scan report dashboard comprising Overview stats, Lines composition metrics, Language distribution percentage charts, filterable Findings lists, and indented File trees.
* **Security & Limits:** Enforces strict limitations on file size (200KB), content volume (5MB), and files processed (100 files). Masking filters hide passwords and private key segments. No repository code is ever executed locally or containerized.

*Note: Large Language Models (LLM/Gemini), PostgreSQL databases, and OAuth login are scheduled for subsequent phases.*

---

## Tech Stack

* **Frontend:** React (v19), Vite, TypeScript, Tailwind CSS (v4), Lucide Icons
* **Backend:** Python (3.13), FastAPI, Uvicorn, Pydantic v2
* **Containerization:** Docker, Docker Compose
* **Testing:** Pytest, HTTPX

---

## Project Structure

```text
devlens/
├── .github/
│   └── workflows/
│       └── ci.yml             # GitHub Actions CI workflow
├── backend/
│   ├── app/
│   │   ├── api/               # API endpoints & route handlers
│   │   │   └── repositories.py # POST /analyze and POST /analyze/report endpoints
│   │   ├── core/              # Config, security, and global settings
│   │   │   └── config.py      # Env variables, CORS, and analysis limits
│   │   ├── models/            # SQLAlchemy / Database models
│   │   ├── services/          # Business logic services
│   │   │   ├── github_url.py  # URL Parser Utility
│   │   │   └── github_service.py # GitHub API Client (metadata, tree, file contents)
│   │   ├── analyzers/         # Deterministic static analysis scanners
│   │   │   ├── language_detector.py # Matches extensions to language
│   │   │   ├── file_classifier.py  # Groups files into source, test, docs, etc.
│   │   │   ├── metrics_analyzer.py # Counts total, code, comment, and blank lines
│   │   │   ├── security_analyzer.py # Checks for credentials & masks values
│   │   │   ├── code_quality_analyzer.py # Audits TODOs, print statements, and exceptions
│   │   │   └── repository_analyzer.py # Orchestrates compile pipeline
│   │   └── main.py            # FastAPI entrypoint and global setup
│   ├── tests/
│   │   ├── test_health.py     # Backend health test
│   │   ├── test_url_parser.py # URL validation tests
│   │   ├── test_language_detector.py # Language match tests
│   │   ├── test_file_classifier.py # File categorizer tests
│   │   ├── test_metrics_analyzer.py # Line counter tests
│   │   ├── test_security_analyzer.py # Secret scanner tests
│   │   ├── test_code_quality.py # Quality audit tests
│   │   ├── test_repository_analyzer.py # Orchestrator integration tests
│   │   └── test_api_report.py # API endpoints tests
│   ├── Dockerfile             # Container image configuration
│   ├── requirements.txt       # Production & development requirements
│   └── .env.example           # Backend environment variables template
├── frontend/
│   ├── src/
│   │   ├── App.tsx            # Main dashboard interface (Quick Scan & Deep Scan tabs)
│   │   ├── index.css          # Main Tailwind stylesheet
│   │   ├── types.ts           # TypeScript type declarations
│   │   └── main.tsx           # React entry point
│   ├── index.html             # Application entry template
│   ├── vite.config.ts         # Vite bundler configuration
│   ├── Dockerfile             # Frontend development Dockerfile
│   └── package.json           # Frontend dependencies and scripts
├── docker-compose.yml         # Container multi-service orchestration
├── .gitignore                 # Workspace version control exclusions
└── README.md                  # Project documentation (this file)
```

---

## Static Analysis Engine Architecture

```text
GitHub Repository
       ↓
Repository Tree
       ↓
File Selection (Filter Source/Test categories)
       ↓
Source File Retrieval (Asynchronously download files under size limits)
       ↓
Language Detection (Map extensions deterministically)
       ↓
Code Metrics (Lines of code, comments, blanks counts)
       ↓
Static Analysis & Security (Obvious secrets scanning + Quality check audits)
       ↓
Structured Analysis Report (JSON payload returned to user)
```

---

## Configuration & Limits

Analysis limits are defined inside `backend/app/core/config.py` and can be customized via environment variables:
* **`MAX_FILES_ANALYZED`**: Default is `100` files.
* **`MAX_FILE_SIZE_BYTES`**: Default is `204800` bytes (200 KB).
* **`MAX_TOTAL_CONTENT_BYTES`**: Default is `5242880` bytes (5 MB).

Files exceeding limits are skipped and documented inside the `analysis_metadata.skip_reasons` response block.

---

## API Endpoints

### 1. Quick Ingestion (Phase 2)
* **Endpoint:** `POST /api/repositories/analyze`
* **Request:** `{"url": "https://github.com/owner/repo"}`
* **Response:** Returns repository metadata and the directory tree structure.

### 2. Deep Analysis Report (Phase 3)
* **Endpoint:** `POST /api/repositories/analyze/report`
* **Request:**
  ```json
  {
    "url": "https://github.com/fastapi/fastapi"
  }
  ```
* **Response:**
  ```json
  {
    "repository": {
      "owner": "fastapi",
      "name": "fastapi",
      "full_name": "fastapi/fastapi",
      "description": "FastAPI framework, high performance, easy to learn...",
      "default_branch": "master",
      "language": "Python",
      "stars": 75200,
      "forks": 6100,
      "open_issues": 120,
      "url": "https://github.com/fastapi/fastapi"
    },
    "summary": {
      "total_files": 340,
      "analyzed_files": 100,
      "skipped_files": 42,
      "source_files": 115,
      "test_files": 27,
      "documentation_files": 54,
      "configuration_files": 12,
      "asset_files": 8,
      "unknown_files": 124
    },
    "languages": [
      {
        "language": "Python",
        "file_count": 92,
        "percentage": 92.0
      },
      {
        "language": "Shell",
        "file_count": 8,
        "percentage": 8.0
      }
    ],
    "files": [
      {
        "path": "fastapi/main.py",
        "language": "Python",
        "category": "source",
        "size_bytes": 1420,
        "line_count": 52,
        "code_lines": 40,
        "comment_lines": 4,
        "blank_lines": 8
      }
    ],
    "metrics": {
      "total_lines": 4820,
      "code_lines": 3950,
      "comment_lines": 420,
      "blank_lines": 450,
      "largest_files_by_size": [
        { "path": "fastapi/applications.py", "size_bytes": 48200 }
      ],
      "largest_files_by_lines": [
        { "path": "fastapi/applications.py", "line_count": 840 }
      ]
    },
    "findings": [
      {
        "id": "SEC-002-fastapi-config-py-18",
        "severity": "high",
        "category": "security",
        "title": "Potential Hardcoded Credential",
        "description": "Variable 'secret' appears to be assigned a hardcoded secret. Masked reference: 'secret = \"********\"'",
        "file": "fastapi/config.py",
        "line": 18,
        "recommendation": "Remove hardcoded credentials. Load values from environment variables."
      }
    ],
    "analysis_metadata": {
      "files_analyzed": 100,
      "files_skipped": 42,
      "skip_reasons": {
        "too_large": 5,
        "unsupported": 0,
        "limit_exceeded": 37
      }
    },
    "tree": [
      { "path": "fastapi", "type": "directory" },
      { "path": "fastapi/main.py", "type": "file" }
    ]
  }
  ```

---

## Security Model

* **No Code Execution:** Source contents are downloaded strictly as text strings. No package installation (`pip install`, `npm install`) or script execution takes place.
* **Secret Protection:** Suspicious strings matching credentials and API tokens are masked with `********` placeholder variables inside findings logs. Raw values are never logged, returned, or persisted.
* **Sandboxed Limits:** Capping processed code prevent Denial-of-Service constraints on host memory or thread operations.

---

## Local Setup Instructions

### Option A: Using Docker Compose
1. Spin up all services:
   ```bash
   docker compose up --build
   ```
2. Inspect:
   * **Frontend Dashboard:** [http://localhost:5173](http://localhost:5173)
   * **Backend REST API:** [http://localhost:8000](http://localhost:8000)

### Option B: Manual Local Setup
1. **Backend:**
   ```bash
   cd backend
   python -m venv venv
   .\venv\Scripts\Activate.ps1   # (Windows)
   pip install -r requirements.txt
   copy .env.example .env
   uvicorn app.main:app --reload
   ```
2. **Frontend:**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

---

## Testing Instructions

To run the complete test suite (unit and mocked integration pipelines):
```bash
cd backend
python -m pytest
```

---

## Roadmap

- [x] **Phase 1: Project Scaffolding** — Scaffolding foundations, FastAPI CORS configurations, basic dashboard layout, Docker and Actions setup.
- [x] **Phase 2: Ingestion layer** — Branch trees matching, repository metadata, error structures.
- [x] **Phase 3: Repository Analysis Engine** — AST-free line metrics calculation, extensions language detector, quality audit logs, secret masks, and Deep Scan reporting dashboards.
- [ ] **Phase 4: AI Analysis & Gemini Integration** — LLM-driven vulnerability checking, automated code recommendations, and documentation generation.
- [ ] **Phase 5: Databases & OAuth** — Scans history persistence and secure user login handlers.
