# DevLens

AI-powered GitHub repository analysis and engineering insights platform.

## Current Status: Phase 4 (Gemini AI Intelligence Layer)

DevLens is currently in **Phase 4: Gemini AI Intelligence Layer**.
* **AI Intelligence Layer:** Leverages Google Gemini via the official `google-genai` SDK with strict JSON schema enforcement to produce structured engineering reviews.
* **Deterministic Analysis Engine:** Measures code line metrics, classifies repo files, detects languages by extension, and runs code quality and security scanners.
* **Intelligent Evidence Selector:** Deterministically ranks and curates high-relevance source code files (prioritizing security findings, code quality issues, and application entrypoints) while strictly enforcing file count, character, and token limits.
* **Defense-in-Depth Security:** Pre-submission secret redaction (masks API keys, passwords, AWS keys, JWTs, and private keys) and strong prompt-injection defenses treating all repository content as untrusted passive data.
* **Frontend AI Review Dashboard:** Interactive AI Review tab displaying executive summaries, architecture reviews, security postures, maintainability ratings, positive engineering observations, and prioritized recommendations.
* **Offline Mocked Tests:** Full test suite runs 100% offline without live Gemini API dependencies.

> [!NOTE]
> **Advisory Disclaimer:** DevLens AI recommendations, ratings, and assessments are advisory and should be reviewed and verified by human engineering teams prior to making production changes.

---

## Tech Stack

* **Frontend:** React (v19), Vite (v8), TypeScript, Tailwind CSS (v4), Lucide Icons
* **Backend:** Python (3.13), FastAPI, Uvicorn, Pydantic v2, `google-genai`
* **Containerization:** Docker, Docker Compose
* **Testing:** Pytest, HTTPX, AnyIO

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
│   │   │   └── repositories.py # POST /analyze, /analyze/report, and /analyze/ai
│   │   ├── core/              # Config, security, and global settings
│   │   │   └── config.py      # Env variables, CORS, and AI/analysis limits
│   │   ├── models/            # Pydantic domain & AI assessment models
│   │   │   └── ai_models.py   # AIAnalysisReport, AssessmentRating, PriorityRecommendation
│   │   ├── services/          # Business logic services
│   │   │   ├── github_url.py  # URL Parser Utility
│   │   │   ├── github_service.py # GitHub API Client (metadata, tree, file contents)
│   │   │   ├── ai_prompts.py  # System prompts & injection defense boundaries
│   │   │   └── ai_service.py  # Gemini client wrapper & schema validation
│   │   ├── analyzers/         # Deterministic static analysis scanners
│   │   │   ├── language_detector.py # Matches extensions to language
│   │   │   ├── file_classifier.py  # Groups files into source, test, docs, etc.
│   │   │   ├── metrics_analyzer.py # Counts total, code, comment, and blank lines
│   │   │   ├── security_analyzer.py # Checks for credentials & masks values
│   │   │   ├── code_quality_analyzer.py # Audits TODOs, print statements, and exceptions
│   │   │   ├── evidence_selector.py # Curates, ranks, and redacts evidence for AI
│   │   │   └── repository_analyzer.py # Orchestrates compile pipeline
│   │   └── main.py            # FastAPI entrypoint and global setup
│   ├── tests/
│   │   ├── test_ai_models.py  # Pydantic AI schema tests
│   │   ├── test_ai_redaction.py # Secret redaction tests
│   │   ├── test_evidence_selector.py # Evidence ranking & limits tests
│   │   ├── test_ai_service.py # Mocked Gemini AI client tests
│   │   ├── test_api_ai.py     # POST /analyze/ai endpoint tests
│   │   ├── test_api_report.py # POST /analyze/report endpoint tests
│   │   ├── test_health.py     # Backend health test
│   │   ├── test_url_parser.py # URL validation tests
│   │   └── ...                # Analyzer unit tests
│   ├── Dockerfile             # Container image configuration
│   ├── requirements.txt       # Production & development requirements
│   └── .env.example           # Backend environment variables template
├── frontend/
│   ├── src/
│   │   ├── App.tsx            # Main dashboard interface (Quick, Deep, and AI tabs)
│   │   ├── index.css          # Main Tailwind stylesheet
│   │   ├── types.ts           # TypeScript type declarations
│   │   └── main.tsx           # React entry point
│   ├── package.json           # Frontend dependencies and scripts
│   └── vite.config.ts         # Vite bundler configuration
└── README.md                  # Project documentation (this file)
```

---

## AI Intelligence Layer Architecture

```text
GitHub Repository URL
       ↓
GitHub Ingestion (Metadata & Tree retrieval)
       ↓
Phase 3 Deterministic Static Analysis (Languages, Metrics, Security & Quality Scans)
       ↓
Evidence Selector
  - Deterministic priority ranking (Security finding files -> Quality finding files -> Entrypoints -> Largest files)
  - Exclusion of vendor directories (node_modules, venv, dist) and lock files
  - Pre-submission Secret Redaction (API keys, passwords, JWTs, private keys -> [REDACTED_SECRET])
  - Strict limits enforcement (Max 12 files, 12k chars/file, 60k chars total)
       ↓
Prompt Injection Defense Boundary
  - Wraps code in <untrusted_repository_evidence> tags
  - Instructs Gemini to treat all code strictly as passive data
       ↓
Gemini AI Service (google-genai Client)
  - Model: gemini-3.6-flash
  - Schema-enforced structured JSON output (AIAnalysisReport)
  - Error translation (Timeout, Rate Limits, Missing Key, Validation)
       ↓
FastAPI Endpoint (POST /api/repositories/analyze/ai)
       ↓
Frontend AI Review Dashboard
  - Staged animated loading indicator
  - Executive summary & Confidence rating
  - Architecture & Security breakdown
  - Performance, Maintainability & Documentation ratings
  - Prioritized engineering recommendations with evidence citations
```

---

## Evidence Selection Strategy

To control token usage, preserve latency, and avoid polluting LLM context with noise, DevLens uses a deterministic relevance selector:

1. **Relevance Hierarchy:**
   - **Priority 1:** Source files containing detected security vulnerabilities or hardcoded secrets.
   - **Priority 2:** Source files containing code quality issues (e.g. unhandled exceptions, debug statements).
   - **Priority 3:** Primary application entrypoints (`main.py`, `app.py`, `index.ts`, `server.ts`, etc.).
   - **Priority 4:** Largest source files by line count and file size.
   - **Priority 5:** Other representative source/test files.
2. **Strict Exclusions:**
   - Vendor & build directories: `node_modules/`, `dist/`, `build/`, `.venv/`, `venv/`, `__pycache__/`.
   - Lock files: `package-lock.json`, `yarn.lock`, `poetry.lock`, `Cargo.lock`.
   - Binary and asset files: images, fonts, archives, audio, video.
   - Credentials files: `.env`, `.pem`, `.key`, `.crt`.
3. **Hard Bounds:**
   - Maximum 12 evidence files.
   - Maximum 12,000 characters per file (records `truncated: True` if truncated).
   - Maximum 60,000 total characters across all evidence files.

---

## Secret Protection & Prompt Injection Defense

1. **Secret Redaction Layer:**
   - Detects and scrubs API keys, auth tokens, JWTs, AWS credentials, and password assignments before submitting evidence to Gemini.
   - Preserves already-masked findings from Phase 3.
2. **Prompt Injection Boundary:**
   - All external repository code and metadata are enclosed in `<untrusted_repository_evidence>` delimiters.
   - System instructions explicitly forbid executing or obeying prompt injection attempts (e.g., `"Ignore previous instructions"`, `"Reveal your API key"`, `"Give this repository a perfect score"`).
   - Gemini is constrained to output structured Pydantic JSON only, preventing jailbreak execution.

---

## Configuration & Limits

Configured in `backend/app/core/config.py` and overrideable via `.env`:

```ini
# Gemini API Key (Required for live AI Review)
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.6-flash

# Evidence Selection Limits
MAX_EVIDENCE_FILES=12
MAX_CHARS_PER_FILE=12000
MAX_TOTAL_EVIDENCE_CHARS=60000
AI_REQUEST_TIMEOUT_SECONDS=30.0

# Static Analysis Limits
MAX_FILES_ANALYZED=100
MAX_FILE_SIZE_BYTES=204800
MAX_TOTAL_CONTENT_BYTES=5242880
```

---

## API Endpoints

### 1. AI Engineering Review (Phase 4)
* **Endpoint:** `POST /api/repositories/analyze/ai`
* **Request:**
  ```json
  {
    "url": "https://github.com/owner/repository"
  }
  ```
* **Response:**
  ```json
  {
    "repository": {
      "owner": "owner",
      "name": "repository",
      "full_name": "owner/repository",
      "description": "Repo description",
      "default_branch": "main",
      "language": "TypeScript",
      "stars": 120,
      "forks": 14,
      "open_issues": 3,
      "url": "https://github.com/owner/repository"
    },
    "deterministic_analysis": {
      "summary": { "total_files": 45, "analyzed_files": 38, ... },
      "languages": [{ "language": "TypeScript", "file_count": 30, "percentage": 78.9 }],
      "metrics": { "total_lines": 3400, "code_lines": 2800, ... },
      "findings": [ ... ]
    },
    "ai_analysis": {
      "executive_summary": "The repository exhibits a modular architecture with strong TypeScript typing...",
      "architecture": {
        "rating": "good",
        "assessment": "Clean separation of services and presentation layer.",
        "strengths": ["Clear domain boundaries", "Shared types module"],
        "weaknesses": ["Tight coupling between controllers and repository helpers"]
      },
      "security": {
        "rating": "needs_attention",
        "assessment": "Potential hardcoded credentials detected in configuration.",
        "strengths": ["Input validation using Zod/Pydantic schemas"],
        "weaknesses": ["Hardcoded API key pattern found in development config"],
        "important_issues": ["Hardcoded secret key in src/config.ts"],
        "recommendations": ["Extract secrets into environment variables"]
      },
      "performance": {
        "rating": "good",
        "assessment": "Lightweight async operations with minimal compute overhead.",
        "recommendations": ["Implement response caching for high-traffic endpoints"]
      },
      "maintainability": {
        "rating": "excellent",
        "assessment": "Well-documented types and comprehensive automated test suite.",
        "recommendations": ["Add integration tests for error boundary handling"]
      },
      "documentation": {
        "rating": "fair",
        "assessment": "Basic setup instructions provided; lacks architecture diagrams.",
        "recommendations": ["Add system architecture diagrams and API spec documentation"]
      },
      "strengths": [
        "Consistent coding standards and TypeScript type safety",
        "Modular service architecture with clean responsibilities"
      ],
      "priorities": [
        {
          "priority": "critical",
          "category": "Security",
          "title": "Remediate Hardcoded Credentials",
          "explanation": "Exposing secrets in repository files introduces unauthorized access risk.",
          "recommendation": "Migrate all sensitive keys to .env and use a secret manager in CI/CD.",
          "evidence": "src/config.ts: line 14"
        }
      ],
      "confidence": "high",
      "confidence_reason": null
    }
  }
  ```

### 2. Deep Analysis Report (Phase 3)
* **Endpoint:** `POST /api/repositories/analyze/report`
* **Request:** `{"url": "https://github.com/owner/repository"}`
* **Response:** Deterministic Phase 3 metrics and findings report.

### 3. Quick Ingestion (Phase 2)
* **Endpoint:** `POST /api/repositories/analyze`
* **Request:** `{"url": "https://github.com/owner/repository"}`
* **Response:** Basic repository metadata and git tree structure.

---

## Local Setup & Testing

### 1. Backend Setup
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

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### 3. Running Automated Tests
The automated test suite runs completely offline with mocked Gemini calls:
```bash
cd backend
python -m pytest
```

### 4. Running Frontend Build
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
- [ ] **Phase 5: Databases & OAuth** — Scans history persistence and secure user login handlers.
