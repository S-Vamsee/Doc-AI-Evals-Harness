"""The offline and live entry points keep keys, network, and results separated."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.environments import child_environment, frozen_heldback


ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / "scripts" / "offline_guard"


def test_offline_environment_removes_keys_and_sets_network_guard():
    env = child_environment("offline", {"DEEPSEEK_API_KEY": "fake-key",
                                        "QWEN_API_KEY": "fake-qwen-key"})
    assert "DEEPSEEK_API_KEY" not in env
    assert "QWEN_API_KEY" not in env
    assert env["PYTHON_DOTENV_DISABLED"] == "1"
    assert env["HARNESS_ENV"] == "offline"
    assert str(GUARD) in env["PYTHONPATH"].split(os.pathsep)


def test_guard_blocks_socket_even_if_key_is_present():
    env = os.environ.copy()
    env["PYTHONPATH"] = str(GUARD) + os.pathsep + env.get("PYTHONPATH", "")
    env["DEEPSEEK_API_KEY"] = "fake-present-key"
    probe = subprocess.run(
        [sys.executable, "-c", "import socket; socket.socket().connect(('127.0.0.1', 1))"],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=10,
    )
    assert probe.returncode != 0
    assert "offline network disabled" in probe.stderr


def test_live_results_and_caches_have_distinct_roots():
    dev = child_environment("live-dev", {})
    heldback = child_environment("live-heldback", {})
    assert dev["HARNESS_RESULTS_DIR"] != heldback["HARNESS_RESULTS_DIR"]
    assert "offline_guard" not in dev.get("PYTHONPATH", "")
    assert "offline_guard" not in heldback.get("PYTHONPATH", "")


def test_heldback_refuses_unfrozen_set(tmp_path):
    with pytest.raises(RuntimeError, match="frozen"):
        frozen_heldback(tmp_path)


def test_core_run_uses_environment_result_root_and_records_it(tmp_path, monkeypatch):
    import json
    import pymupdf
    from src.core_pipeline import run_text_page

    pdf_path = tmp_path / "sample.pdf"
    pdf = pymupdf.open()
    pdf.new_page().insert_text((72, 72),
                               "Invoice number INV-4102; amount $128.40; vendor Northvale")
    pdf.save(pdf_path)
    pdf.close()
    result_root = tmp_path / "live-dev"
    monkeypatch.setenv("HARNESS_RESULTS_DIR", str(result_root))
    monkeypatch.setenv("HARNESS_ENV", "live-dev")

    def recorded(_messages):
        return {"content": '{"facts": []}', "usage": {},
                "api_created_at": None, "latency_seconds": 0.0}

    run = run_text_page("sample", pdf_path, 1, "https://example.org/sample.pdf",
                        model_request=recorded)
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    assert result_root in run.parents
    assert manifest["environment"] == "live-dev"

