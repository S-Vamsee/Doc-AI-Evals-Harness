"""Changing the development runner must change the recorded code version."""

from src.core_pipeline import _code_version


def test_code_version_covers_runner_and_review_policy(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "scripts").mkdir()
    (tmp_path / "data" / "calibration").mkdir(parents=True)
    (tmp_path / "run_eval.py").write_text("entry", encoding="utf-8")
    (tmp_path / "src" / "development_run.py").write_text("runner v1", encoding="utf-8")
    (tmp_path / "scripts" / "environments.py").write_text("launcher", encoding="utf-8")
    policy = tmp_path / "data" / "calibration" / "REVIEW.md"
    policy.write_text("ruling v1", encoding="utf-8")
    first = _code_version(tmp_path)
    (tmp_path / "src" / "development_run.py").write_text("runner v2", encoding="utf-8")
    assert _code_version(tmp_path) != first
    second = _code_version(tmp_path)
    policy.write_text("ruling v2", encoding="utf-8")
    assert _code_version(tmp_path) != second

