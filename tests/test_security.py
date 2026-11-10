import json

from evidenceflow.trace_writer import redact
from scripts.security_scan import scan


def test_scan_detects_configured_value_without_returning_secret(tmp_path, monkeypatch):
    key = "unit-test-private-" + "9" * 24
    monkeypatch.setenv("LLM_API_KEY", key)
    (tmp_path / "leak.txt").write_text(key, encoding="utf-8")
    result = scan(tmp_path)
    assert result["status"] == "FAIL"
    assert key not in json.dumps(result)


def test_trace_redacts_key_field_and_known_token_patterns():
    token = "sk-" + "a" * 32
    result = redact({"api_key": "private", "text": "echo " + token})
    assert result["api_key"] == "[REDACTED]"
    assert token not in result["text"]
