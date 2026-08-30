from app.analyzers.security_analyzer import scan_security

def test_scan_security_private_key():
    content = """# Some configuration
-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEA0Yc6...
-----END RSA PRIVATE KEY-----
"""
    findings = scan_security(content, "config.py")
    assert len(findings) == 1
    assert findings[0]["severity"] == "critical"
    assert findings[0]["title"] == "Hardcoded Private Key"

def test_scan_security_hardcoded_secrets():
    content = """
# Test configuration settings
DATABASE_URL = "postgresql://localhost:5432"
API_KEY = "sk-proj-abc123xyz789SECRET"
password = "super-secret-password-assignment"
dummy_key = "fake-key-placeholder" # dummy keyword, should be skipped
"""
    findings = scan_security(content, "app/settings.py")
    
    # Matches API_KEY and password. Skipped dummy_key.
    assert len(findings) == 2
    
    # Verify API_KEY finding
    api_finding = next(f for f in findings if "API_KEY" in f["description"])
    assert api_finding["severity"] == "high"
    assert api_finding["title"] == "Potential Hardcoded Credential"
    # Ensure masked
    assert "sk-proj-abc123xyz789SECRET" not in api_finding["description"]
    assert "sk-********" in api_finding["description"] or "sk-proj-********" in api_finding["description"]

    # Verify password finding
    pwd_finding = next(f for f in findings if "password" in f["description"])
    assert "super-secret-password-assignment" not in pwd_finding["description"]
    assert "********" in pwd_finding["description"]
