import os
from app.analyzers.language_detector import detect_language

# Documentation definitions
DOC_EXTENSIONS = {".md", ".txt", ".rst", ".adoc"}
DOC_NAMES = {"license", "contributing", "changelog", "readme", "copying", "authors"}

# Configuration definitions
CONFIG_EXTENSIONS = {".json", ".yaml", ".yml", ".ini", ".toml", ".conf", ".config", ".xml", ".gradle"}
CONFIG_NAMES = {".gitignore", ".dockerignore", "dockerfile", "package.json", "package-lock.json", "requirements.txt", "pyproject.toml", "makefile", "gemfile", "lock.json"}

# Asset definitions
ASSET_EXTENSIONS = {
    # Images
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp",
    # Fonts
    ".ttf", ".woff", ".woff2", ".eot", ".otf",
    # Media
    ".mp3", ".mp4", ".wav", ".webm", ".avi", ".mov",
    # Archives
    ".zip", ".tar", ".gz", ".rar", ".7z",
    # Binaries
    ".exe", ".dll", ".so", ".dylib", ".bin"
}

# Test folder names
TEST_DIRECTORIES = {"tests", "test", "spec", "specs", "__tests__"}

def classify_file(path: str) -> str:
    """
    Classifies a repository file into a functional category.
    
    Args:
        path: The file path.
        
    Returns:
        One of the categories: "source", "test", "documentation", 
        "configuration", "asset", or "unknown".
    """
    path_lower = path.lower()
    name = os.path.basename(path_lower)
    _, ext = os.path.splitext(name)
    
    name_no_ext, _ = os.path.splitext(name)
    
    # 1. Exact Name Matches (Highest Priority)
    if name in CONFIG_NAMES:
        return "configuration"
    if name_no_ext in DOC_NAMES:
        return "documentation"
        
    # 2. Extensions (Fallback Priority)
    if ext in CONFIG_EXTENSIONS:
        return "configuration"
    if ext in DOC_EXTENSIONS:
        return "documentation"
    if ext in ASSET_EXTENSIONS:
        return "asset"
        
    # 4. Test
    # Check if inside standard test directories
    path_segments = path_lower.replace("\\", "/").split("/")
    is_in_test_dir = any(segment in TEST_DIRECTORIES for segment in path_segments)
    
    # Check if filename matches test formats
    is_test_file_name = (
        name.startswith("test_") or
        name_no_ext.endswith("_test") or
        ".test." in name or
        ".spec." in name
    )
    
    lang = detect_language(path)
    
    if (is_in_test_dir or is_test_file_name) and lang != "Unknown":
        return "test"
        
    # 5. Source
    if lang != "Unknown":
        return "source"
        
    return "unknown"
