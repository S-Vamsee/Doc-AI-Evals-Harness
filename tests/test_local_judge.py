"""The selected judge is local, distinct, and unavailable until installed."""

import pytest

from src.judge import judge_pair


def test_judge_checks_installed_model_before_call():
    calls = []

    def request(path, payload=None):
        calls.append(path)
        return {"models": [{"name": "qwen3-vl:2b-instruct"}]}

    with pytest.raises(RuntimeError, match="not installed"):
        judge_pair("Acme Corp", "Acme Corporation", request_json=request)
    assert calls == ["/api/tags"]


def test_local_judge_returns_a_valid_boolean_only():
    calls = []

    def request(path, payload=None):
        calls.append((path, payload))
        if path == "/api/tags":
            return {"models": [{"name": "gemma3:4b"}]}
        return {"message": {"content": '{"match":true,"reason":"Equivalent name."}'}}

    result = judge_pair("Acme Corp", "Acme Corporation", request_json=request)
    assert result == {"match": True, "reason": "Equivalent name."}
    assert calls[1][0] == "/api/chat"
    assert calls[1][1]["model"] == "gemma3:4b"
    assert calls[1][1]["options"]["temperature"] == 0


def test_judge_receives_field_context_and_owner_comparison_rules():
    import json

    calls = []

    def request(path, payload=None):
        calls.append((path, payload))
        if path == "/api/tags":
            return {"models": [{"name": "gemma3:4b"}]}
        return {"message": {"content": '{"match":false,"reason":"Currency marker differs."}'}}

    judge_pair(53.78, "$53.78", field="total_due", source_excerpt="Total due: $53.78",
               request_json=request)
    messages = calls[1][1]["messages"]
    system = messages[0]["content"].casefold()
    assert "currency marker" in system
    assert "different" in system
    assert "suffix" in system and "year" in system and "job title" in system
    assert "specimen marking" in system
    payload = json.loads(messages[1]["content"])
    assert payload["field"] == "total_due"
    assert payload["source_excerpt"] == "Total due: $53.78"
    assert "human_label" not in payload
