import pytest
from app.analyzers.evidence_selector import EvidenceSelector, is_excluded_file


@pytest.mark.anyio
async def test_vendor_and_generated_files_excluded():
    excluded_samples = [
        "node_modules/react/index.js",
        ".venv/lib/site-packages/pkg.py",
        "venv/bin/activate",
        "dist/bundle.js",
        "build/static/main.js",
        "package-lock.json",
        "yarn.lock",
        "poetry.lock",
        ".env",
        ".env.local",
        "assets/hero.png",
        "public/logo.svg",
        "static/style.min.css",
        "certs/server.pem"
    ]
    for path in excluded_samples:
        assert is_excluded_file(path) is True, f"Expected {path} to be excluded"

    valid_samples = [
        "src/app.py",
        "backend/services/auth.ts",
        "internal/handler.go",
        "README.md",
        "src/components/Dashboard.tsx"
    ]
    for path in valid_samples:
        assert is_excluded_file(path) is False, f"Expected {path} to be allowed"


@pytest.mark.anyio
async def test_security_findings_prioritized_over_other_files():
    selector = EvidenceSelector(max_files=3)

    mock_report = {
        "findings": [
            {
                "file": "src/auth.py",
                "category": "security",
                "severity": "critical",
                "title": "Hardcoded Key",
                "description": "Secret found",
                "line": 10,
                "recommendation": "Use env var"
            },
            {
                "file": "src/utils.py",
                "category": "quality",
                "severity": "low",
                "title": "Debug print",
                "description": "Print statement found",
                "line": 42,
                "recommendation": "Remove print"
            }
        ],
        "metrics": {
            "largest_files_by_lines": [{"path": "src/large.py", "line_count": 500}],
            "largest_files_by_size": [{"path": "src/large.py", "size_bytes": 10000}]
        },
        "files": [
            {"path": "src/auth.py", "category": "source"},
            {"path": "src/utils.py", "category": "source"},
            {"path": "src/large.py", "category": "source"},
            {"path": "src/random.py", "category": "source"}
        ]
    }

    candidates = selector.rank_file_candidates(mock_report)
    ranked_paths = [c[0] for c in candidates]

    # Security file must be ranked first
    assert ranked_paths[0] == "src/auth.py"
    # Quality finding file should come next
    assert ranked_paths[1] == "src/utils.py"
    # Large file should follow
    assert "src/large.py" in ranked_paths


@pytest.mark.anyio
async def test_evidence_limits_and_truncation():
    selector = EvidenceSelector(
        max_files=2,
        max_chars_per_file=50,
        max_total_chars=120
    )

    mock_report = {
        "findings": [],
        "metrics": {},
        "files": [
            {"path": "src/entry.py", "category": "source"},
            {"path": "src/second.py", "category": "source"},
            {"path": "src/third.py", "category": "source"}
        ]
    }

    cached_contents = {
        "src/entry.py": "x = 1\n" * 20,      # ~120 chars
        "src/second.py": "y = 2\n" * 20,     # ~120 chars
        "src/third.py": "z = 3\n" * 20
    }

    bundle = await selector.select_evidence(
        deterministic_report=mock_report,
        owner="test-owner",
        repo="test-repo",
        default_branch="main",
        cached_file_contents=cached_contents
    )

    evidence_files = bundle["evidence_files"]
    # Enforces max_files = 2
    assert len(evidence_files) == 2

    # First file should be truncated to max_chars_per_file = 50
    first = evidence_files[0]
    assert first["truncated"] is True
    assert "Truncated" in first["content"]

    # Limits record reflects truncation
    assert bundle["limits"]["truncated"] is True
    assert bundle["limits"]["total_files_selected"] == 2
    assert bundle["limits"]["total_evidence_chars"] <= 120
