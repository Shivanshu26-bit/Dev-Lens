from typing import List, Dict, Any

def scan_quality(content: str, file_path: str, language: str) -> List[Dict[str, Any]]:
    """
    Runs deterministic code quality audits on source file content.
    
    Args:
        content: The text contents of the file.
        file_path: The file path in the repository.
        language: The detected programming language of the file.
        
    Returns:
        A list of Finding dictionary objects.
    """
    findings = []
    if not content:
        return findings

    lines = content.splitlines()
    for line_idx, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped:
            continue

        # Check 1: Line length limit (greater than 120 chars)
        if len(line) > 120:
            findings.append({
                "id": f"QLT-001-{file_path.replace('/', '-')}-{line_idx}",
                "severity": "low",
                "category": "style",
                "title": "Line Too Long",
                "description": f"Line length exceeds the standard 120-character limit ({len(line)} chars).",
                "file": file_path,
                "line": line_idx,
                "recommendation": "Split the line or refactor nested expressions into helper variables to enhance readability."
            })

        # Check 2: Unresolved TODO/FIXME comments
        if "TODO" in stripped or "FIXME" in stripped:
            marker = "TODO" if "TODO" in stripped else "FIXME"
            findings.append({
                "id": f"QLT-002-{file_path.replace('/', '-')}-{line_idx}",
                "severity": "info",
                "category": "quality",
                "title": f"Unresolved {marker} Comment",
                "description": f"Found an outstanding '{marker}' developer marker: '{stripped}'",
                "file": file_path,
                "line": line_idx,
                "recommendation": "Review the associated code logic and resolve the outstanding task."
            })

        # Check 3: Python specific checks (broad excepts and print statements)
        if language == "Python":
            # Check for except: or except Exception: or except Exception as e:
            if (
                stripped.startswith("except:") or 
                stripped.startswith("except Exception:") or 
                stripped.startswith("except Exception as") or
                "except Exception " in stripped
            ):
                findings.append({
                    "id": f"QLT-003-{file_path.replace('/', '-')}-{line_idx}",
                    "severity": "medium",
                    "category": "quality",
                    "title": "Broad Exception Clause",
                    "description": "Caught a generic/broad exception clause handling all errors indiscriminately.",
                    "file": file_path,
                    "line": line_idx,
                    "recommendation": "Specify explicit exception classes (e.g. ValueError, KeyError) instead of catching all exceptions."
                })

            # Check for print() debug statements (skipping comments)
            if not stripped.startswith("#") and "print(" in stripped:
                findings.append({
                    "id": f"QLT-004-{file_path.replace('/', '-')}-{line_idx}",
                    "severity": "low",
                    "category": "quality",
                    "title": "Debug Print Statement",
                    "description": f"Obvious debug 'print()' statement detected: '{stripped}'",
                    "file": file_path,
                    "line": line_idx,
                    "recommendation": "Replace debugging prints with a structured Python logger (logging module) for production."
                })

        # Check 4: JavaScript/TypeScript specific checks (console.log statements)
        elif language in {"JavaScript", "TypeScript", "React JSX", "React TSX"}:
            # Check for console.log() statements (skipping comments)
            if not stripped.startswith("//") and not stripped.startswith("*") and "console.log(" in stripped:
                findings.append({
                    "id": f"QLT-005-{file_path.replace('/', '-')}-{line_idx}",
                    "severity": "low",
                    "category": "quality",
                    "title": "Console Debug Logger",
                    "description": f"Obvious debugging logger 'console.log()' statement detected: '{stripped}'",
                    "file": file_path,
                    "line": line_idx,
                    "recommendation": "Remove console.log statements before deployment or use a production logger library."
                })

    return findings
