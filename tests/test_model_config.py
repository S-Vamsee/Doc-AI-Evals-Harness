"""The model endpoint is set in configuration, recorded in each run, and never leaks a private name."""

import io
import json
from types import SimpleNamespace

import pymupdf
import pytest

from src import core_pipeline
from src.core_pipeline import run_text_page
from src.model_check import check_model
from src.model_config import (endpoint_summary, load_model_config, public_model_label,
                              request_options, usage_cost)

OPENROUTER = {"HARNESS_MODEL_BASE_URL": "https://openrouter.ai/api/v1",
              "HARNESS_MODEL_API_KEY": "fake-or-key", "HARNESS_MODEL": "vendor/some-model"}


def test_new_settings_win_and_old_settings_still_work():
    both = {**OPENROUTER, "DEEPSEEK_API_KEY": "old-key", "DEEPSEEK_MODEL": "old-model"}
    config = load_model_config(both)
    assert (config.api_key, config.model, config.provider) == ("fake-or-key", "vendor/some-model",
                                                               "openrouter")
    old = load_model_config({"DEEPSEEK_API_KEY": "old-key",
                             "DEEPSEEK_BASE_URL": "https://example.services.ai.azure.com/models",
                             "DEEPSEEK_MODEL": "private-deployment-name"})
    assert old.provider == "azure" and old.api_key == "old-key"


@pytest.mark.parametrize("env", [{}, {"HARNESS_MODEL_API_KEY": "your_key_here"},
                                 {"HARNESS_MODEL_BASE_URL": "https://openrouter.ai/api/v1",
                                  "HARNESS_MODEL_API_KEY": "k"}])
def test_missing_key_or_model_stops_before_any_call(env):
    with pytest.raises(RuntimeError):
        load_model_config(env)


def test_private_deployment_names_never_become_the_public_label():
    private = {"DEEPSEEK_BASE_URL": "https://example.services.ai.azure.com/models",
               "DEEPSEEK_MODEL": "private-deployment-name"}
    assert public_model_label(private) == "deepseek-flash"
    assert public_model_label(OPENROUTER) == "vendor/some-model"
    assert public_model_label({**private, "HARNESS_MODEL_LABEL": "chosen-label"}) == "chosen-label"
    assert "private-deployment-name" not in json.dumps(endpoint_summary(private))


def test_openrouter_requests_ask_for_real_cost_and_json_capable_providers():
    options = request_options(load_model_config(OPENROUTER))
    assert options["extra_body"]["usage"] == {"include": True}
    assert options["extra_body"]["provider"] == {"require_parameters": True}
    assert options["extra_body"]["reasoning"] == {"enabled": False}
    deepseek = load_model_config({"HARNESS_MODEL_API_KEY": "k"})
    assert request_options(deepseek)["extra_body"] == {"thinking": {"type": "disabled"}}


def test_provider_cost_is_read_from_the_usage_object():
    assert usage_cost(SimpleNamespace(cost=0.00042)) == 0.00042
    assert usage_cost(SimpleNamespace(model_extra={"cost": "0.001"})) == 0.001
    assert usage_cost(SimpleNamespace()) is None and usage_cost(None) is None


def test_live_request_sends_the_configured_model_and_returns_its_cost(monkeypatch):
    seen = {}

    class FakeClient:
        def __init__(self, **kwargs):
            seen["client"] = kwargs
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

        def create(self, **request):
            seen["request"] = request
            usage = SimpleNamespace(prompt_tokens=10, completion_tokens=4, cost=0.0002)
            choice = SimpleNamespace(message=SimpleNamespace(content='{"ok": true}'),
                                     finish_reason="stop")
            return SimpleNamespace(choices=[choice], usage=usage, created=1790000000)

    for name, value in OPENROUTER.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setattr(core_pipeline, "OpenAI", FakeClient)
    reply = core_pipeline._live_request([{"role": "user", "content": "hi"}])
    assert seen["client"]["base_url"] == OPENROUTER["HARNESS_MODEL_BASE_URL"]
    assert seen["request"]["model"] == "vendor/some-model"
    assert seen["request"]["temperature"] == 0
    assert reply["cost_usd"] == 0.0002 and reply["provider"] == "openrouter"


def test_each_run_records_provider_label_and_reported_cost(tmp_path, monkeypatch):
    for name, value in OPENROUTER.items():
        monkeypatch.setenv(name, value)
    pdf = pymupdf.open()
    pdf.new_page().insert_text((72, 72), "Invoice number A-17 for the supplies delivered")
    path = tmp_path / "page.pdf"
    pdf.save(path)
    pdf.close()

    def reply(messages):
        return {"content": json.dumps({"facts": [{"kind": "identifier", "subject": None,
                                                  "relation": "invoice_number", "value": "A-17",
                                                  "origin": "extracted",
                                                  "quote": "Invoice number A-17"}]}),
                "usage": {"prompt_tokens": 40, "completion_tokens": 10}, "cost_usd": 0.0003,
                "api_created_at": 1790000000, "latency_seconds": 0.1, "finish_reason": "stop"}

    run = run_text_page("sample", path, 1, "https://example.org/page.pdf",
                        output_root=tmp_path / "runs", model_request=reply)
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    result = json.loads((run / "result.json").read_text(encoding="utf-8"))
    report = (run / "report.md").read_text(encoding="utf-8")
    assert manifest["provider"] == "openrouter" and manifest["provider_host"] == "openrouter.ai"
    assert manifest["model_label"] == "vendor/some-model" == result["model_label"]
    assert result["provider_cost_usd"] == 0.0003
    assert "provider-reported cost: $0.000300" in report
    assert "fake-or-key" not in json.dumps(manifest) + json.dumps(result) + report


def test_cost_is_not_reported_when_a_reply_lacks_it(tmp_path):
    pdf = pymupdf.open()
    pdf.new_page().insert_text((72, 72), "Invoice number A-17 for the supplies delivered")
    path = tmp_path / "page.pdf"
    pdf.save(path)
    pdf.close()
    run = run_text_page("sample", path, 1, "https://example.org/page.pdf",
                        output_root=tmp_path / "runs",
                        model_request=lambda m: {"content": '{"facts": []}',
                                                 "usage": {"prompt_tokens": 5,
                                                           "completion_tokens": 2},
                                                 "api_created_at": 1790000000})
    result = json.loads((run / "result.json").read_text(encoding="utf-8"))
    assert result["provider_cost_usd"] is None
    assert "provider-reported" not in (run / "report.md").read_text(encoding="utf-8")


def test_connection_check_passes_only_on_the_expected_reply():
    out = io.StringIO()
    good = check_model(lambda m: {"content": '{"ok": true}', "usage": {}, "cost_usd": 0.00001},
                       out=out)
    assert good == 0 and "Connection works." in out.getvalue()
    assert check_model(lambda m: {"content": "hello", "usage": {}}, out=io.StringIO()) == 1

    def refused(messages):
        raise RuntimeError("Error code: 401")

    out = io.StringIO()
    assert check_model(refused, out=out) == 1 and "401" in out.getvalue()
