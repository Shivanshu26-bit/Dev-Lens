import re
from typing import List, Dict, Any

# Pattern for assignment variables: api_key = "...", secret: "...", etc.
SECRET_ASSIGNMENT_PATTERN = re.compile(
    r"(?i)\b(api_key|apikey|secret|password|passwd|token|private_key|auth_token|access_token|client_secret)\b\s*[:=]\s*['\"]([^'\"]{8,})['\"]"
)

# Pattern for raw private keys
PRIVATE_KEY_HEADER_PATTERN = re.compile(
    r"-----BEGIN\s+[A-Z ]+\s+PRIVATE\s+KEY-----"
)

# Placeholders that represent false positives
DUMMY_CREDENTIAL_KEYWORDS = {
    "placeholder", "dummy", "your_", "enter_", "here", "fake", "test", 
    "token_val", "env", "default", "xxxx", "123456", "my_password"
}

def scan_security(content: str, file_path: str) -> List[Dict[str, Any]]:
    """
    Scans file content line-by-line for potential hardcoded credentials and secrets.
    
    Args:
        content: The text content of the file.
        file_path: The file path in the repository.
        
    Returns:
        A list of Finding dictionary objects.
    """
    findings = []
    if not content:
        return findings

    lines = content.splitlines()
    for line_idx, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("//"):
            continue # Skip comment-only lines

        # Check 1: Plaintext Private Key Headers
        if PRIVATE_KEY_HEADER_PATTERN.search(stripped):
            findings.append({
                "id": f"SEC-001-{file_path.replace('/', '-')}-{line_idx}",
                "severity": "critical",
                "category": "security",
                "title": "Hardcoded Private Key",
                "description": "Detected what appears to be a plaintext private key header inside source code.",
                "file": file_path,
                "line": line_idx,
                "recommendation": "Remove plaintext private keys from repository code. Inject them at runtime using environment variables."
            })
            continue

        # Check 2: Secret Variable Assignments
        match = SECRET_ASSIGNMENT_PATTERN.search(stripped)
        if match:
            var_name = match.group(1)
            raw_secret = match.group(2)
            
            # Strip outer quotes and spaces to check value
            secret_val_clean = raw_secret.strip()
            
            # Skip obvious placeholders/dummy credentials to avoid noise
            if any(keyword in secret_val_clean.lower() for keyword in DUMMY_CREDENTIAL_KEYWORDS):
                continue
                
            # Perform masking (do not expose raw values in logs or responses)
            masked_secret = "********"
            # If the secret has a prefix divider like sk-proj-12345, keep key prefix to help identify the type
            if "-" in secret_val_clean[:10]:
                prefix = secret_val_clean.split("-")[0] + "-"
                masked_secret = f"{prefix}********"
                
            masked_line = line.replace(raw_secret, masked_secret).strip()

            findings.append({
                "id": f"SEC-002-{file_path.replace('/', '-')}-{line_idx}",
                "severity": "high",
                "category": "security",
                "title": "Potential Hardcoded Credential",
                "description": f"Variable '{var_name}' appears to be assigned a hardcoded secret. Masked reference: '{masked_line}'",
                "file": file_path,
                "line": line_idx,
                "recommendation": "Remove hardcoded credentials from files. Utilize environment configuration files (.env) or secret vaults."
            })
            
    return findings
