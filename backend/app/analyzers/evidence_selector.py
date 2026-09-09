import re
from typing import Dict, Any, List, Optional, Tuple, Set
from app.core.config import settings
from app.services.github_service import GitHubService


# Patterns for lightweight pre-AI redaction
_PRIVATE_KEY_PATTERN = re.compile(
    r"-----BEGIN [A-Z0-9_-]+ PRIVATE KEY-----[\s\S]*?-----END [A-Z0-9_-]+ PRIVATE KEY-----",
    re.IGNORECASE
)
_AWS_KEY_PATTERN = re.compile(r"\bAKIA[0-9A-Z]{16}\b")
_JWT_PATTERN = re.compile(r"\beyJ[A-Za-z0-9-_]+\.eyJ[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\b")
_GENERIC_SECRET_ASSIGNMENT = re.compile(
    r"(?i)\b([a-z0-9_]*(?:api[_-]?key|secret|token|password|passwd|auth|bearer)[a-z0-9_]*)\b\s*([:=])\s*(['\"][^'\"]{6,}['\"])",
)

# Common application entrypoint patterns
ENTRYPOINT_PATTERNS = {
    "main.py", "app.py", "server.py", "index.py", "wsgi.py", "asgi.py",
    "index.ts", "index.tsx", "index.js", "main.ts", "main.tsx", "main.js",
    "app.ts", "app.tsx", "app.js", "server.ts", "server.js",
    "src/main.py", "src/app.py", "src/index.ts", "src/index.tsx", "src/App.tsx",
    "main.go", "main.rs", "Program.cs"
}

# Directories and files to strictly exclude from AI evidence
EXCLUDED_DIR_PARTS = {
    "node_modules", ".venv", "venv", "env", "dist", "build", "target",
    ".git", ".github", ".pytest_cache", "__pycache__", ".next", ".nuxt",
    "vendor", "coverage"
}

EXCLUDED_FILENAMES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock",
    "Pipfile.lock", "Cargo.lock", "composer.lock", "mix.lock",
    ".env", ".env.local", ".env.production", ".env.development"
}

EXCLUDED_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".webp",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    ".mp4", ".webm", ".mp3", ".wav",
    ".zip", ".tar", ".gz", ".rar", ".7z",
    ".pdf", ".exe", ".dll", ".so", ".dylib",
    ".pem", ".key", ".crt", ".der", ".p12", ".pfx",
    ".min.js", ".min.css", ".map"
}


def redact_secrets(text: str) -> str:
    """
    Lightweight redaction layer to scrub raw secrets, tokens, credentials,
    and private keys from evidence text before AI submission.
    Preserves already-masked patterns (e.g. '***' or '[MASKED]').
    """
    if not text:
        return ""

    # Redact PEM private keys
    redacted = _PRIVATE_KEY_PATTERN.sub("[REDACTED_PRIVATE_KEY]", text)

    # Redact AWS access keys
    redacted = _AWS_KEY_PATTERN.sub("[REDACTED_AWS_KEY]", redacted)

    # Redact JWT tokens
    redacted = _JWT_PATTERN.sub("[REDACTED_JWT_TOKEN]", redacted)

    # Redact secret and password assignments: keep the variable name, mask the value
    def _mask_assignment(match):
        var_name = match.group(1)
        sep = match.group(2)
        val = match.group(3)
        # If already masked, leave it
        if "***" in val or "REDACTED" in val or "MASKED" in val:
            return match.group(0)
        return f'{var_name} {sep} "[REDACTED_SECRET]"'

    redacted = _GENERIC_SECRET_ASSIGNMENT.sub(_mask_assignment, redacted)

    return redacted


def is_excluded_file(path: str) -> bool:
    """
    Checks if a file path belongs to excluded directories, lockfiles,
    secret credentials, or binary/generated assets.
    """
    lower_path = path.lower().replace("\\", "/")
    parts = lower_path.split("/")

    # Check directory parts
    for part in parts[:-1]:
        if part in EXCLUDED_DIR_PARTS:
            return True

    filename = parts[-1]

    # Check excluded filenames
    if filename in EXCLUDED_FILENAMES:
        return True

    # Check .env variants
    if filename.startswith(".env"):
        return True

    # Check extensions
    for ext in EXCLUDED_EXTENSIONS:
        if filename.endswith(ext):
            return True

    return False


class EvidenceSelector:
    """
    Intelligently selects and packages repository evidence for AI analysis
    using deterministic relevance ranking, strict size limits, and secret redaction.
    """

    def __init__(
        self,
        max_files: Optional[int] = None,
        max_chars_per_file: Optional[int] = None,
        max_total_chars: Optional[int] = None,
    ):
        self.max_files = max_files or settings.MAX_EVIDENCE_FILES
        self.max_chars_per_file = max_chars_per_file or settings.MAX_CHARS_PER_FILE
        self.max_total_chars = max_total_chars or settings.MAX_TOTAL_EVIDENCE_CHARS

    def rank_file_candidates(
        self,
        deterministic_report: Dict[str, Any]
    ) -> List[Tuple[str, str, int]]:
        """
        Ranks candidate file paths based on relevance:
        1. Security findings files (Priority 1)
        2. High/critical findings files (Priority 2)
        3. Code-quality findings files (Priority 3)
        4. Application entrypoints (Priority 4)
        5. Largest source files by line count / size (Priority 5)
        6. Other representative source files (Priority 6)

        Returns:
            List of tuples: (file_path, selection_reason, priority_weight)
            Ordered by priority (highest priority first).
        """
        findings = deterministic_report.get("findings", [])
        metrics = deterministic_report.get("metrics", {})
        all_files = deterministic_report.get("files", [])

        # Sets to track why files are prioritized
        security_files: Set[str] = set()
        high_crit_files: Set[str] = set()
        quality_files: Set[str] = set()

        for finding in findings:
            f_path = finding.get("file")
            if not f_path or is_excluded_file(f_path):
                continue

            sev = finding.get("severity", "").lower()
            cat = finding.get("category", "").lower()

            if cat == "security":
                security_files.add(f_path)
            if sev in ("critical", "high"):
                high_crit_files.add(f_path)
            elif cat == "quality":
                quality_files.add(f_path)

        # Largest files from metrics
        largest_by_lines = [
            m.get("path") for m in metrics.get("largest_files_by_lines", [])
            if m.get("path") and not is_excluded_file(m.get("path"))
        ]
        largest_by_size = [
            m.get("path") for m in metrics.get("largest_files_by_size", [])
            if m.get("path") and not is_excluded_file(m.get("path"))
        ]

        scored_candidates: Dict[str, Tuple[str, int]] = {}

        # 1. Security finding files
        for f in security_files:
            scored_candidates[f] = ("Contains security findings", 100)

        # 2. High/Critical finding files
        for f in high_crit_files:
            if f not in scored_candidates:
                scored_candidates[f] = ("Contains high/critical severity findings", 90)

        # 3. Quality finding files
        for f in quality_files:
            if f not in scored_candidates:
                scored_candidates[f] = ("Contains code quality findings", 80)

        # 4. Entrypoints
        for file_info in all_files:
            path = file_info.get("path", "")
            if is_excluded_file(path):
                continue
            norm_path = path.replace("\\", "/")
            base_name = norm_path.split("/")[-1]
            if base_name in ENTRYPOINT_PATTERNS or norm_path in ENTRYPOINT_PATTERNS:
                if path not in scored_candidates:
                    scored_candidates[path] = ("Application entrypoint", 70)

        # 5. Largest source files
        for path in largest_by_lines:
            if path not in scored_candidates:
                scored_candidates[path] = ("Primary large source file (by lines)", 60)

        for path in largest_by_size:
            if path not in scored_candidates:
                scored_candidates[path] = ("Primary large source file (by size)", 50)

        # 6. Remaining representative source files
        for file_info in all_files:
            path = file_info.get("path", "")
            cat = file_info.get("category", "")
            if cat in ("source", "test") and not is_excluded_file(path):
                if path not in scored_candidates:
                    scored_candidates[path] = (f"Representative {cat} file", 30)

        # Sort candidates by weight desc, then path alphabetically for determinism
        sorted_candidates = sorted(
            [(path, reason, weight) for path, (reason, weight) in scored_candidates.items()],
            key=lambda x: (-x[2], x[0])
        )

        return sorted_candidates

    async def select_evidence(
        self,
        deterministic_report: Dict[str, Any],
        owner: str,
        repo: str,
        default_branch: str,
        github_service: Optional[GitHubService] = None,
        cached_file_contents: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Selects prioritized evidence, redacting sensitive content and enforcing limits.
        """
        github = github_service or GitHubService()
        file_cache = cached_file_contents or {}

        ranked_candidates = self.rank_file_candidates(deterministic_report)

        selected_files: List[Dict[str, Any]] = []
        total_evidence_chars = 0
        files_truncated_count = 0

        for path, reason, _ in ranked_candidates:
            if len(selected_files) >= self.max_files:
                break

            # Fetch content if not in cache
            content: Optional[str] = None
            if path in file_cache:
                content = file_cache[path]
            else:
                try:
                    content = await github.get_file_content(owner, repo, path, default_branch)
                except Exception:
                    # Skip files that could not be retrieved
                    continue

            if not content:
                continue

            # Redact secrets
            redacted_content = redact_secrets(content)

            # Check per-file character limit
            is_truncated = False
            if len(redacted_content) > self.max_chars_per_file:
                notice = f"\n[... Truncated to {self.max_chars_per_file} chars by DevLens ...]"
                if self.max_chars_per_file > len(notice):
                    redacted_content = redacted_content[: self.max_chars_per_file - len(notice)] + notice
                else:
                    redacted_content = redacted_content[: self.max_chars_per_file]
                is_truncated = True
                files_truncated_count += 1

            # Check total evidence character limit
            remaining_quota = self.max_total_chars - total_evidence_chars
            if remaining_quota <= 0:
                break

            if len(redacted_content) > remaining_quota:
                notice = "\n[... Truncated by DevLens total evidence limit ...]"
                if remaining_quota > len(notice):
                    redacted_content = redacted_content[: remaining_quota - len(notice)] + notice
                else:
                    redacted_content = redacted_content[:remaining_quota]
                is_truncated = True
                files_truncated_count += 1

            char_count = len(redacted_content)
            total_evidence_chars += char_count

            selected_files.append({
                "path": path,
                "reason": reason,
                "content": redacted_content,
                "char_count": char_count,
                "truncated": is_truncated
            })

        # Redact findings recommendations/descriptions
        raw_findings = deterministic_report.get("findings", [])
        redacted_findings = []
        findings_by_severity: Dict[str, int] = {}
        findings_by_category: Dict[str, int] = {}

        for f in raw_findings:
            sev = f.get("severity", "unknown").lower()
            cat = f.get("category", "unknown").lower()
            findings_by_severity[sev] = findings_by_severity.get(sev, 0) + 1
            findings_by_category[cat] = findings_by_category.get(cat, 0) + 1

            redacted_findings.append({
                "id": f.get("id"),
                "severity": sev,
                "category": cat,
                "title": f.get("title"),
                "description": redact_secrets(f.get("description", "")),
                "file": f.get("file"),
                "line": f.get("line"),
                "recommendation": redact_secrets(f.get("recommendation", "")),
            })

        return {
            "repository": deterministic_report.get("repository", {}),
            "summary": deterministic_report.get("summary", {}),
            "languages": deterministic_report.get("languages", []),
            "metrics": deterministic_report.get("metrics", {}),
            "findings_summary": {
                "total": len(raw_findings),
                "by_severity": findings_by_severity,
                "by_category": findings_by_category,
            },
            "findings": redacted_findings,
            "evidence_files": selected_files,
            "limits": {
                "max_files": self.max_files,
                "max_chars_per_file": self.max_chars_per_file,
                "max_total_chars": self.max_total_chars,
                "total_evidence_chars": total_evidence_chars,
                "total_files_selected": len(selected_files),
                "files_truncated_count": files_truncated_count,
                "truncated": files_truncated_count > 0 or len(ranked_candidates) > len(selected_files),
            },
        }
