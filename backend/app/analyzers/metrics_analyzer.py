from typing import Tuple

# Language family definitions for comment parsing
C_STYLE_LANGUAGES = {
    "JavaScript", "TypeScript", "React JSX", "React TSX", 
    "Java", "C", "C++", "C#", "Go", "Rust", "PHP", "CSS", "SCSS"
}
HASH_STYLE_LANGUAGES = {
    "Python", "Ruby", "Shell", "YAML", "Markdown"
}
SQL_STYLE_LANGUAGES = {
    "SQL"
}

def calculate_metrics(content: str, language: str) -> Tuple[int, int, int, int]:
    """
    Calculates line metrics (total lines, blank lines, comment lines, code lines)
    for a given file content and language.
    
    Args:
        content: The text contents of the file.
        language: The detected programming language name.
        
    Returns:
        A tuple of (total_lines, blank_lines, comment_lines, code_lines).
    """
    if not content:
        return 0, 0, 0, 0

    lines = content.splitlines()
    total_lines = len(lines)
    blank_lines = 0
    comment_lines = 0
    
    in_block_comment = False
    block_quotes_char = None  # Tracks '"""' or "'''" for Python docstrings
    
    for line in lines:
        stripped = line.strip()
        if not stripped:
            blank_lines += 1
            continue
            
        # 1. C-Style Comment Parsing (JS, TS, C, Go, Java, Rust, etc.)
        if language in C_STYLE_LANGUAGES:
            if in_block_comment:
                comment_lines += 1
                if "*/" in stripped:
                    in_block_comment = False
                continue
            elif stripped.startswith("/*"):
                comment_lines += 1
                if "*/" not in stripped:
                    in_block_comment = True
                continue
            elif stripped.startswith("//"):
                comment_lines += 1
                continue
                
        # 2. SQL Comment Parsing
        elif language in SQL_STYLE_LANGUAGES:
            if in_block_comment:
                comment_lines += 1
                if "*/" in stripped:
                    in_block_comment = False
                continue
            elif stripped.startswith("/*"):
                comment_lines += 1
                if "*/" not in stripped:
                    in_block_comment = True
                continue
            elif stripped.startswith("--"):
                comment_lines += 1
                continue
                
        # 3. Python Docstrings and Hash Comments
        elif language == "Python":
            if stripped.startswith("#"):
                comment_lines += 1
                continue
                
            # Parse Docstring blocks
            if in_block_comment:
                comment_lines += 1
                if block_quotes_char and block_quotes_char in stripped:
                    in_block_comment = False
                    block_quotes_char = None
                continue
            elif stripped.startswith('"""') or stripped.startswith("'''"):
                comment_lines += 1
                quotes = '"""' if stripped.startswith('"""') else "'''"
                # If it doesn't open and close on the same line
                if stripped.count(quotes) < 2:
                    in_block_comment = True
                    block_quotes_char = quotes
                continue
                
        # 4. General Hash Comments
        elif language in HASH_STYLE_LANGUAGES:
            if stripped.startswith("#"):
                comment_lines += 1
                continue
                
    code_lines = total_lines - blank_lines - comment_lines
    code_lines = max(0, code_lines) # Guard against negative code counts
    
    return total_lines, blank_lines, comment_lines, code_lines
