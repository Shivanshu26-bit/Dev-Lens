import pytest
from app.analyzers.evidence_selector import redact_secrets


def test_redact_private_key():
    raw = """
-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEA04wX4u
fakePrivateKeyPayload123456789==
-----END RSA PRIVATE KEY-----
def connect():
    pass
"""
    result = redact_secrets(raw)
    assert "-----BEGIN RSA PRIVATE KEY-----" not in result
    assert "fakePrivateKeyPayload" not in result
    assert "[REDACTED_PRIVATE_KEY]" in result
    assert "def connect():" in result


def test_redact_api_keys_and_tokens():
    raw = """
API_KEY = "sk-proj-9999888877776666"
SECRET_TOKEN = 'ghp_abcdefghijklmnopqrstuvwxyz123456'
bearer = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.doNotLeakThisSignature"
"""
    result = redact_secrets(raw)
    assert "sk-proj-9999888877776666" not in result
    assert "ghp_abcdefghijklmnopqrstuvwxyz123456" not in result
    assert "doNotLeakThisSignature" not in result
    assert "[REDACTED_SECRET]" in result or "[REDACTED_JWT_TOKEN]" in result


def test_redact_password_assignments():
    raw = """
db_password = "SuperSecretPassword123!"
user_passwd: 'AnotherSecretPass123'
"""
    result = redact_secrets(raw)
    assert "SuperSecretPassword123!" not in result
    assert "AnotherSecretPass123" not in result
    assert "[REDACTED_SECRET]" in result


def test_masked_values_remain_masked():
    raw = """
API_KEY = "sk-***"
TOKEN = "[MASKED]"
SECRET = "[REDACTED_SECRET]"
"""
    result = redact_secrets(raw)
    assert "sk-***" in result
    assert "[MASKED]" in result
    assert "[REDACTED_SECRET]" in result


def test_redact_aws_key():
    raw = 'aws_access_key = "AKIAIOSFODNN7EXAMPLE"'
    result = redact_secrets(raw)
    assert "AKIAIOSFODNN7EXAMPLE" not in result
