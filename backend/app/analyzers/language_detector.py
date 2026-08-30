import os

# Map of lowercased extensions to language names
EXTENSION_MAP = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".jsx": "React JSX",
    ".tsx": "React TSX",
    ".java": "Java",
    ".c": "C",
    ".cpp": "C++",
    ".cc": "C++",
    ".cxx": "C++",
    ".hpp": "C++",
    ".cs": "C#",
    ".go": "Go",
    ".rs": "Rust",
    ".php": "PHP",
    ".rb": "Ruby",
    ".html": "HTML",
    ".htm": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".json": "JSON",
    ".yml": "YAML",
    ".yaml": "YAML",
    ".md": "Markdown",
    ".sql": "SQL",
    ".sh": "Shell"
}

def detect_language(path: str) -> str:
    """
    Detects the programming or markup language of a file based on its extension.
    
    Args:
        path: The file path.
        
    Returns:
        The matched language name string, or "Unknown".
    """
    _, ext = os.path.splitext(path.lower())
    return EXTENSION_MAP.get(ext, "Unknown")
