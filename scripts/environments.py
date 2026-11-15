"""One-command entry points for the five harness test environments."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / "scripts" / "offline_guard"
RESULTS = ROOT / "results" / "environments"


def child_environment(mode: str, source: dict[str, str] | None = None) -> dict[str, str]:
    if mode not in {"offline", "clean", "live-dev", "live-heldback", "ci"}:
        raise ValueError(f"Unknown environment: {mode}")
    env = dict(os.environ if source is None else source)
    env["HARNESS_ENV"] = mode
    if mode in {"offline", "clean", "ci"}:
        for name in list(env):
            if name.upper().endswith(("_API_KEY", "_TOKEN")) or name in {
                "DEEPSEEK_API_KEY", "AZURE_API_KEY", "QWEN_API_KEY"}:
                env.pop(name, None)
        env["PYTHON_DOTENV_DISABLED"] = "1"
        env["PYTHONPATH"] = str(GUARD) + os.pathsep + env.get("PYTHONPATH", "")
    else:
        current = [part for part in env.get("PYTHONPATH", "").split(os.pathsep)
                   if part and Path(part) != GUARD]
        env["PYTHONPATH"] = os.pathsep.join(current)
        env.pop("PYTHON_DOTENV_DISABLED", None)
        env["HARNESS_RESULTS_DIR"] = str(RESULTS / mode)
    return env


def frozen_heldback(root: Path = ROOT) -> dict:
    path = root / "data" / "heldback" / "freeze.json"
    if not path.is_file():
        raise RuntimeError("The held-back set is not frozen; live-heldback is disabled")
    record = json.loads(path.read_text(encoding="utf-8"))
    if record.get("frozen") is not True or not record.get("input_sha256"):
        raise RuntimeError("The held-back set has no valid frozen fingerprint")
    return record


def _run(command: list[str], env: dict[str, str]) -> int:
    return subprocess.run(command, cwd=ROOT, env=env, check=False).returncode


def _clean() -> int:
    external = Path("C:/venvs") if os.name == "nt" else Path(tempfile.gettempdir()) / "harness-venvs"
    external.mkdir(parents=True, exist_ok=True)
    wheelhouse = Path(os.getenv("HARNESS_WHEELHOUSE", str(external / "harness-wheels")))
    if not wheelhouse.is_dir():
        raise RuntimeError(f"Offline wheelhouse missing: {wheelhouse}. Prepare it first.")
    fresh = Path(tempfile.mkdtemp(prefix="harness-clean-", dir=external))
    if ROOT in fresh.parents or fresh == ROOT:
        raise RuntimeError("A clean virtual environment cannot be inside the repository")
    subprocess.run([sys.executable, "-m", "venv", str(fresh)], check=True)
    python = fresh / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    env = child_environment("clean")
    env["PIP_NO_INDEX"] = "1"
    for requirements in ("requirements.txt", "requirements-dev.txt"):
        code = _run([str(python), "-m", "pip", "install", "--no-index",
                     "--find-links", str(wheelhouse), "-r", requirements], env)
        if code:
            return code
    print(f"Clean environment: {fresh}", flush=True)
    for command in ([str(python), "run_eval.py", "--help"],
                    [str(python), "-m", "pytest", "-q"]):
        code = _run(command, env)
        if code:
            return code
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("offline", "clean", "live-dev",
                                         "live-heldback", "ci"))
    parser.add_argument("args", nargs=argparse.REMAINDER)
    selected = parser.parse_args()
    if selected.mode == "clean":
        if selected.args:
            parser.error("clean runs its fixed smoke test and full offline suite")
        return _clean()
    if selected.mode in {"offline", "ci"}:
        return _run([sys.executable, "-m", "pytest", "-q", *selected.args],
                    child_environment(selected.mode))
    if selected.mode == "live-heldback":
        frozen_heldback()
    args = selected.args[1:] if selected.args[:1] == ["--"] else selected.args
    if not args:
        parser.error("A live environment needs explicit run_eval.py arguments")
    return _run([sys.executable, "run_eval.py", *args],
                child_environment(selected.mode))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2)

