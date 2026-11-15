"""The live extractor permits long pages and names a truncated response."""

import json
from types import SimpleNamespace

import pymupdf

from src import core_pipeline


def test_live_request_uses_long_output_budget(monkeypatch):
    captured = {}

    def create(**request):
        captured.update(request)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content='{"facts": []}'),
                                     finish_reason="stop")],
            usage=None, created=1,
        )

    client = SimpleNamespace(chat=SimpleNamespace(
        completions=SimpleNamespace(create=create)))
    monkeypatch.setenv("DEEPSEEK_API_KEY", "fake-key")
    monkeypatch.setattr(core_pipeline, "OpenAI", lambda **_kwargs: client)
    reply = core_pipeline._live_request([{"role": "user", "content": "test"}])
    assert captured["max_tokens"] >= 10000
    assert reply["finish_reason"] == "stop"


def test_truncated_json_is_saved_as_named_extraction_failure(tmp_path):
    path = tmp_path / "sample.pdf"
    pdf = pymupdf.open()
    pdf.new_page().insert_text((72, 72),
                               "Invoice number A-17 and vendor Northvale and total $128.40")
    pdf.save(path)
    pdf.close()

    def truncated(_messages):
        return {"content": '{"facts": [{"kind": "amount", "value": "',
                "finish_reason": "length", "usage": {},
                "api_created_at": None, "latency_seconds": 0.0}

    run = core_pipeline.run_text_page("sample", path, 1,
                                      "https://example.org/sample.pdf",
                                      output_root=tmp_path / "runs", model_request=truncated)
    result = json.loads((run / "result.json").read_text(encoding="utf-8"))
    assert result["complete"] is False
    assert result["failures"][0]["stage"] == "extraction"
    assert "output limit" in result["failures"][0]["reason"]
    assert (run / "extraction.raw.json").is_file()

