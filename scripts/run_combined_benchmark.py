#!/usr/bin/env python3
"""Run the serving suite, then a pinned tool-use evaluation, without publishing raw data."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE = ROOT / "configs" / "tool-eval-standard-v1.json"
RAW_ROOT = ROOT / ".bench-runs"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class CombinedRunError(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CombinedRunError(f"cannot read JSON from {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise CombinedRunError(f"expected a JSON object in {path}")
    return value


def load_profile(path: Path) -> dict[str, Any]:
    profile = load_json(path)
    required = {
        "protocol_id", "repository", "commit", "smoke_scenarios",
        "standard_scenarios", "scenario_categories", "trials", "seed",
        "temperature", "parallel",
        "max_turns", "timeout_seconds", "system_prompt", "hard_mode",
    }
    missing = required - profile.keys()
    if missing:
        raise CombinedRunError(f"tool-eval profile missing: {sorted(missing)}")
    if not re.fullmatch(r"[0-9a-f]{40}", str(profile["commit"])):
        raise CombinedRunError("tool-eval commit must be a full lowercase SHA")
    if profile["hard_mode"] is not False:
        raise CombinedRunError("the standard profile must not enable Hard Mode")
    if len(profile["scenario_categories"]) != int(profile["standard_scenarios"]):
        raise CombinedRunError("tool-eval category map does not cover the standard suite")
    return profile


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9._-]+", "-", value.casefold()).strip("-.")
    return (slug or "run")[:80]


def _run_id(label: str) -> str:
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{stamp}-{_slug(label)}"


def validate_baseline(catalog_path: Path, baseline_id: str) -> None:
    catalog = load_json(catalog_path)
    if catalog.get("schema_version") != 6:
        raise CombinedRunError("results/catalog.json must use schema_version 6")
    ids = {item.get("id") for item in catalog.get("baselines", [])}
    if baseline_id not in ids:
        raise CombinedRunError(f"unknown baseline id: {baseline_id}")


def preflight_endpoint(base_url: str, model: str, api_key: str | None) -> None:
    from llm_serving_bench.client import OpenAIClient

    client = OpenAIClient(base_url, model, api_key, timeout=30)
    payload = client.models()
    served = [item.get("id") for item in payload.get("data", [])]
    if model not in served:
        raise CombinedRunError(
            f"requested model is not present in /v1/models; available model count={len(served)}"
        )


def serving_command(args: argparse.Namespace, output: Path) -> list[str]:
    command = [
        sys.executable,
        "-m",
        "llm_serving_bench",
        "--base-url",
        args.base_url,
        "--model",
        args.model,
        "--suite",
        str(args.suite),
        "--output",
        str(output),
        "--label",
        args.label,
        "--server-label",
        args.server_label,
        "--timeout",
        str(args.serving_timeout),
    ]
    if args.api_key_env:
        command.extend(["--api-key-env", args.api_key_env])
    for mapping in args.monitor_host:
        command.extend(["--monitor-host", mapping])
    command.extend(["--monitor-interval", str(args.monitor_interval)])
    return command


def tool_eval_command(
    binary: Path,
    profile: dict[str, Any],
    args: argparse.Namespace,
    output_name: str,
    *,
    smoke: bool,
) -> list[str]:
    command = [
        str(binary),
        "run",
        "--base-url",
        args.base_url,
        "--model",
        args.model,
        "--seed",
        str(profile["seed"]),
        "--temperature",
        str(profile["temperature"]),
        "--parallel",
        str(profile["parallel"]),
        "--max-turns",
        str(profile["max_turns"]),
        "--timeout",
        str(profile["timeout_seconds"]),
        "--label",
        args.label,
        "--no-live",
        "--json-file",
        output_name,
    ]
    if smoke:
        command.append("--short")
    else:
        command.extend(["--trials", str(profile["trials"])])
    return command


def _run_logged(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    log_path: Path,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    with log_path.open("w", encoding="utf-8") as log:
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
    if check and completed.returncode != 0:
        raise CombinedRunError(
            f"command failed with exit {completed.returncode}; private log: {log_path}"
        )
    return completed


def _cache_root() -> Path:
    configured = os.environ.get("LLM_SERVING_BENCH_CACHE_DIR")
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".cache" / "llm-serving-bench"


def ensure_tool_eval(
    profile: dict[str, Any], raw_dir: Path, supplied_binary: Path | None
) -> Path:
    if supplied_binary:
        binary = supplied_binary.expanduser().resolve()
        if not binary.is_file() or not os.access(binary, os.X_OK):
            raise CombinedRunError(f"tool-eval binary is not executable: {binary}")
        return binary

    uv = shutil.which("uv")
    git = shutil.which("git")
    if not uv or not git:
        raise CombinedRunError(
            "automatic tool-eval setup requires git and uv; use --tool-eval-bin for an existing install"
        )

    commit = str(profile["commit"])
    checkout = _cache_root() / "tool-eval-bench" / commit
    checkout.parent.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env.update({"GIT_TERMINAL_PROMPT": "0", "UV_NO_PROGRESS": "1"})
    log_path = raw_dir / "tool-eval-install.log"

    if not (checkout / ".git").is_dir():
        if checkout.exists():
            raise CombinedRunError(f"tool-eval cache path is not a git checkout: {checkout}")
        _run_logged(
            [git, "clone", "--filter=blob:none", "--no-checkout", str(profile["repository"]), str(checkout)],
            cwd=checkout.parent,
            env=env,
            log_path=log_path,
        )
    with log_path.open("a", encoding="utf-8") as log:
        for command in (
            [git, "-C", str(checkout), "fetch", "--depth", "1", "origin", commit],
            [git, "-C", str(checkout), "checkout", "--detach", commit],
            [uv, "sync", "--frozen", "--no-dev"],
        ):
            completed = subprocess.run(
                command,
                cwd=checkout,
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                text=True,
                check=False,
            )
            if completed.returncode != 0:
                raise CombinedRunError(
                    f"tool-eval setup failed with exit {completed.returncode}; private log: {log_path}"
                )
    binary = checkout / ".venv" / "bin" / "tool-eval-bench"
    if not binary.is_file():
        raise CombinedRunError("tool-eval setup completed without an executable")
    return binary


def _validate_serving_result(path: Path) -> None:
    run = load_json(path)
    failures = sum(
        int(item.get("summary", {}).get("failed_requests", 0))
        for item in run.get("scenarios", [])
    )
    if failures:
        raise CombinedRunError(
            f"serving suite recorded {failures} failed requests; tool evaluation was not started"
        )


def _completion_rate(result: dict[str, Any]) -> float:
    total = int(result.get("total_scenarios") or 0)
    scenario_results = result.get("scores", {}).get("scenario_results", [])
    if total <= 0 or not isinstance(scenario_results, list):
        return 0.0
    graded = sum(
        1
        for item in scenario_results
        if isinstance(item, dict) and not item.get("is_infrastructure_failure", False)
    )
    return 100.0 * graded / total


def _validate_tool_identity(result: dict[str, Any], profile: dict[str, Any]) -> None:
    metadata = result.get("metadata") or {}
    observed = str(metadata.get("git_sha") or "").removesuffix("-dirty")
    expected = str(profile["commit"])
    if observed != expected and not (
        7 <= len(observed) < len(expected) and expected.startswith(observed)
    ):
        raise CombinedRunError(
            "tool-eval result does not identify the pinned commit; refusing a non-comparable run"
        )


def _standard_completion_rate(
    result: dict[str, Any], profile: dict[str, Any]
) -> float:
    trial = result.get("trial_statistics") or {}
    trials = int(trial.get("trials") or 0)
    scenarios = int(profile["standard_scenarios"])
    if trials != int(profile["trials"]):
        raise CombinedRunError("tool-eval standard result has the wrong trial count")
    per_scenario = trial.get("per_scenario") or {}
    if not isinstance(per_scenario, dict):
        raise CombinedRunError("tool-eval standard result has no scenario statistics")
    expected_ids = set(profile["scenario_categories"])
    if not set(per_scenario).issubset(expected_ids):
        raise CombinedRunError("tool-eval standard result contains unknown scenarios")
    if any(
        len(item.get("points", [])) > trials
        for item in per_scenario.values()
        if isinstance(item, dict)
    ):
        raise CombinedRunError("tool-eval standard result contains excess trial points")
    graded = sum(
        len(item.get("points", []))
        for item in per_scenario.values()
        if isinstance(item, dict)
    )
    return round(100.0 * graded / (scenarios * trials), 1)


def _validate_resume(
    raw_dir: Path, args: argparse.Namespace, profile: dict[str, Any]
) -> None:
    try:
        raw_dir.relative_to(RAW_ROOT.resolve())
    except ValueError as exc:
        raise CombinedRunError("--resume-raw-dir must be inside the ignored .bench-runs directory") from exc
    manifest = load_json(raw_dir / "manifest.json")
    expected = {
        "baseline_id": args.baseline_id,
        "model": args.model,
        "label": args.label,
        "tool_eval_profile": profile,
    }
    if any(manifest.get(key) != value for key, value in expected.items()):
        raise CombinedRunError("resume manifest does not match the requested run identity")
    _validate_serving_result(raw_dir / "serving.json")


def _write_manifest(
    raw_dir: Path, args: argparse.Namespace, profile: dict[str, Any], status: str
) -> None:
    manifest = {
        "schema_version": 1,
        "status": status,
        "baseline_id": args.baseline_id,
        "model": args.model,
        "label": args.label,
        "server_label": args.server_label,
        "serving_suite": str(args.suite),
        "tool_eval_profile": profile,
    }
    (raw_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )


def execute(args: argparse.Namespace) -> Path:
    args.suite = args.suite.resolve()
    args.tool_eval_profile = args.tool_eval_profile.resolve()
    profile = load_profile(args.tool_eval_profile)
    validate_baseline(ROOT / "results" / "catalog.json", args.baseline_id)
    if not args.suite.is_file():
        raise CombinedRunError(f"serving suite does not exist: {args.suite}")
    api_key = None
    if args.api_key_env:
        api_key = os.environ.get(args.api_key_env)
        if not api_key:
            raise CombinedRunError(f"API-key environment variable is unset: {args.api_key_env}")
    try:
        preflight_endpoint(args.base_url, args.model, api_key)
    except CombinedRunError:
        raise
    except Exception as exc:
        raise CombinedRunError(
            f"endpoint preflight failed ({type(exc).__name__}); benchmark was not started"
        ) from exc

    if args.resume_raw_dir:
        raw_dir = args.resume_raw_dir.resolve()
        _validate_resume(raw_dir, args, profile)
        print(f"RESUME validated serving evidence in {raw_dir}", flush=True)
    else:
        raw_dir = RAW_ROOT / _run_id(args.label)
        raw_dir.mkdir(parents=True, exist_ok=False)
    _write_manifest(raw_dir, args, profile, "running")
    env = dict(os.environ)

    failure_status = "failed"
    try:
        if not args.resume_raw_dir:
            serving_output = raw_dir / "serving.json"
            print("RUN serving benchmark", flush=True)
            _run_logged(
                serving_command(args, serving_output),
                cwd=ROOT,
                env=env,
                log_path=raw_dir / "serving.log",
            )
            _validate_serving_result(serving_output)

        binary = ensure_tool_eval(profile, raw_dir, args.tool_eval_bin)
        tool_env = {
            key: value for key, value in env.items() if not key.startswith("TOOL_EVAL_")
        }
        tool_env["TOOL_EVAL_PROVIDER"] = ""
        tool_env["TOOL_EVAL_API_KEY"] = api_key or ""
        tool_env.pop("PYTHONPATH", None)
        tool_env.pop("PYTHONHOME", None)

        smoke_name = "tool-eval-smoke.json"
        if not args.resume_raw_dir:
            print("RUN tool-eval smoke", flush=True)
            _run_logged(
                tool_eval_command(binary, profile, args, smoke_name, smoke=True),
                cwd=raw_dir,
                env=tool_env,
                log_path=raw_dir / "tool-eval-smoke.log",
            )
        else:
            print("RESUME validating completed tool-eval smoke", flush=True)
        smoke = load_json(raw_dir / smoke_name)
        _validate_tool_identity(smoke, profile)
        if int(smoke.get("total_scenarios") or 0) != int(profile["smoke_scenarios"]):
            raise CombinedRunError("tool-eval smoke returned an unexpected scenario count")
        if _completion_rate(smoke) < 100.0:
            failure_status = "tool-eval-unsupported-or-incomplete"
            raise CombinedRunError(
                f"tool-eval smoke completion was {_completion_rate(smoke):.1f}%; "
                "full run was not started"
            )

        print("RUN tool-eval standard x3", flush=True)
        standard_name = "tool-eval-standard.json"
        _run_logged(
            tool_eval_command(binary, profile, args, standard_name, smoke=False),
            cwd=raw_dir,
            env=tool_env,
            log_path=raw_dir / "tool-eval-standard.log",
        )
        standard = load_json(raw_dir / standard_name)
        _validate_tool_identity(standard, profile)
        completion = _standard_completion_rate(standard, profile)
        if completion < 100.0:
            _write_manifest(raw_dir, args, profile, "tool-eval-incomplete")
            print(f"INCOMPLETE tool-eval completion={completion:.1f}%", flush=True)
            print(f"RAW_RESULT_DIR {raw_dir}", flush=True)
            return raw_dir
    except CombinedRunError:
        _write_manifest(raw_dir, args, profile, failure_status)
        raise
    _write_manifest(raw_dir, args, profile, "complete")
    print(f"RAW_RESULT_DIR {raw_dir}", flush=True)
    return raw_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run serving and pinned tool-use benchmarks against an already-live endpoint."
    )
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--baseline-id", required=True)
    parser.add_argument("--suite", required=True, type=Path)
    parser.add_argument("--label", required=True)
    parser.add_argument("--server-label", default="redacted-direct-endpoint")
    parser.add_argument("--api-key-env")
    parser.add_argument("--monitor-host", action="append", default=[])
    parser.add_argument("--monitor-interval", type=float, default=5.0)
    parser.add_argument("--serving-timeout", type=float, default=900.0)
    parser.add_argument("--tool-eval-profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--tool-eval-bin", type=Path)
    parser.add_argument(
        "--resume-raw-dir",
        type=Path,
        help="Continue a failed private run after revalidating its serving and smoke evidence.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        execute(args)
    except CombinedRunError as exc:
        print(f"combined benchmark failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
