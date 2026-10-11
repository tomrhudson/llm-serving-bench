#!/usr/bin/env python3
"""Import an allowlisted tool-eval summary into the public catalog and report."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
CATALOG = RESULTS / "catalog.json"
PUBLISHED_PROFILE = ROOT / "configs" / "tool-eval-standard-v1.json"


class ImportError(RuntimeError):
    pass


def load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ImportError(f"cannot read JSON from {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ImportError(f"expected a JSON object in {path}")
    return value


def _number(value: Any, name: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ImportError(f"tool-eval field {name} must be numeric")
    return float(value)


def _safe_text(value: Any, name: str, pattern: str) -> str:
    text = str(value or "")
    if not re.fullmatch(pattern, text):
        raise ImportError(f"tool-eval field {name} has an unsafe or unexpected value")
    return text


def sanitize_tool_result(
    result: dict[str, Any], profile: dict[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if result.get("schema_version") != "1":
        raise ImportError("unsupported tool-eval output schema")
    metadata = result.get("metadata") or {}
    observed_commit = str(metadata.get("git_sha") or "").removesuffix("-dirty")
    commit = str(profile.get("commit") or "")
    if observed_commit != commit and not (
        7 <= len(observed_commit) < len(commit) and commit.startswith(observed_commit)
    ):
        raise ImportError("tool-eval commit does not match the pinned profile")

    scores = result.get("scores")
    trial = result.get("trial_statistics")
    if not isinstance(scores, dict) or not isinstance(trial, dict):
        raise ImportError("tool-eval result is missing scores or three-trial statistics")
    trials = int(trial.get("trials") or 0)
    scenarios = int(profile.get("standard_scenarios") or 0)
    if trials != int(profile.get("trials") or 0):
        raise ImportError("tool-eval result has the wrong trial count")

    per_scenario = trial.get("per_scenario")
    if not isinstance(per_scenario, dict):
        raise ImportError("tool-eval result has no per-scenario trial statistics")
    last_items = scores.get("scenario_results", [])
    if not isinstance(last_items, list):
        raise ImportError("tool-eval result has invalid scenario results")
    last_results = {
        str(item.get("scenario_id")): item
        for item in last_items
        if isinstance(item, dict) and item.get("scenario_id")
    }
    scenario_ids = set(per_scenario) | set(last_results)
    if len(scenario_ids) != scenarios:
        raise ImportError("tool-eval result has the wrong scenario count")
    incomplete = [
        scenario_id
        for scenario_id in scenario_ids
        for item in [per_scenario.get(scenario_id)]
        if not isinstance(item, dict)
        or len(item.get("points", [])) != trials
    ]
    graded_trials = sum(
        len(item.get("points", []))
        for item in per_scenario.values()
        if isinstance(item, dict)
    )
    completion = round(100.0 * graded_trials / (scenarios * trials), 1)
    status = "complete" if not incomplete and completion == 100.0 else "incomplete"

    categories_raw = trial.get("per_category")
    if not isinstance(categories_raw, dict):
        raise ImportError("tool-eval result is missing category statistics")
    categories = []
    for category_id in sorted(categories_raw):
        item = categories_raw[category_id]
        if not isinstance(item, dict):
            raise ImportError("invalid category statistics")
        safe_category = _safe_text(category_id, "category id", r"[A-O]")
        categories.append({
            "id": safe_category,
            "label": _safe_text(
                item.get("label") or category_id,
                "category label",
                r"[A-Za-z0-9 &/()_-]{1,80}",
            ),
            "mean_percent": _number(item.get("mean_percent"), "category mean"),
            "stddev_percent": _number(item.get("stddev_percent"), "category stddev"),
        })

    non_pass = []
    category_map = profile.get("scenario_categories") or {}
    if not isinstance(category_map, dict) or len(category_map) != scenarios:
        raise ImportError("pinned profile has no complete scenario category map")
    for scenario_id in sorted(scenario_ids):
        safe_scenario_id = _safe_text(scenario_id, "scenario id", r"TC-[0-9]{2}")
        scenario_stats = per_scenario.get(scenario_id) or {}
        points = scenario_stats.get("points", [])
        if any(
            not isinstance(point, int) or isinstance(point, bool) or point not in {0, 1, 2}
            for point in points
        ):
            raise ImportError("tool-eval scenario points must be integers from 0 to 2")
        if len(points) == trials and all(point == 2 for point in points):
            continue
        last = last_results.get(scenario_id, {})
        if len(points) != trials:
            outcome = "incomplete"
        elif 2 in points and any(point != 2 for point in points):
            outcome = "flaky"
        elif points and all(point == 1 for point in points):
            outcome = "partial"
        else:
            outcome = "fail"
        non_pass.append({
            "scenario_id": safe_scenario_id,
            "category": _safe_text(
                category_map.get(scenario_id), "scenario category", r"[A-O]"
            ),
            "status": outcome,
            "points": [int(point) for point in points],
            "infrastructure_failure": len(points) != trials,
        })

    ci = trial.get("final_score_ci95")
    if not isinstance(ci, (list, tuple)) or len(ci) != 2:
        raise ImportError("tool-eval result has no two-sided confidence interval")
    safety = result.get("safety_gate") or {}
    config = result.get("config") or {}
    summary = {
        "protocol_id": str(profile["protocol_id"]),
        "upstream_commit": commit,
        "version": _safe_text(
            result.get("tool_eval_bench_version"), "version", r"[A-Za-z0-9.+_-]{1,80}"
        ),
        "run_id": _safe_text(
            result.get("run_id"), "run id", r"[A-Za-z0-9._:-]{1,128}"
        ),
        "config_fingerprint": _safe_text(
            config.get("config_fingerprint"), "config fingerprint", r"[0-9a-f]{6,64}"
        ),
        "status": status,
        "trials": trials,
        "scenarios_per_trial": scenarios,
        "completion_rate": completion,
        "score_mean": _number(trial.get("final_score_mean"), "score mean"),
        "score_median": _number(trial.get("final_score_median"), "score median"),
        "score_stddev": _number(trial.get("final_score_stddev"), "score stddev"),
        "score_ci95": [_number(ci[0], "CI low"), _number(ci[1], "CI high")],
        "pass_at_3": _number(trial.get("pass_at_k"), "Pass@3"),
        "pass_hat_3": _number(trial.get("pass_hat_k"), "Pass^3"),
        "reliability_gap": _number(trial.get("reliability_gap"), "reliability gap"),
        "safety_passed": bool(safety.get("passed", not result.get("safety_warnings"))),
        "category_scores": categories,
    }
    return summary, non_pass


def render_report(
    baseline: dict[str, Any],
    model: dict[str, Any],
    summary: dict[str, Any],
    non_pass: list[dict[str, Any]],
) -> str:
    safety = "passed" if summary["safety_passed"] else "FAILED — review before recommendation"
    result_status = (
        "COMPLETE — directly comparable within this protocol cohort"
        if summary["status"] == "complete"
        else f'INCOMPLETE — {summary["completion_rate"]:.1f}% completion; not a comparative result'
    )
    categories = "\n".join(
        f'| {item["id"]} · {item["label"]} | {item["mean_percent"]:.1f}% | {item["stddev_percent"]:.1f} |'
        for item in summary["category_scores"]
    )
    failures = "\n".join(
        f'| {item["scenario_id"]} | {item["category"]} | {item["status"]} | '
        f'{"/".join(str(point) for point in item["points"]) or "—"} | '
        f'{"yes" if item["infrastructure_failure"] else "no"} |'
        for item in non_pass
    ) or "| — | — | All scenarios passed in all trials | — | no |"
    return f'''# Tool-use benchmark: {baseline["label"]}

This is a curated, sanitized `tool-eval-bench` report for the serving stack
described by the linked baseline. Raw conversations, generated text, tool
payloads, endpoint details, and credentials are not published.

- Serving baseline: [{baseline["label"]}]({baseline["report"]})
- Benchmarked checkpoint: {model["benchmarked_source"]}
- Runtime: `{baseline["runtime"]}`
- Recipe: {baseline["recipe_credit"]}
- Protocol: `{summary["protocol_id"]}`
- Upstream commit: [`{summary["upstream_commit"][:12]}`](https://github.com/SeraphimSerapis/tool-eval-bench/commit/{summary["upstream_commit"]})
- Tool-eval version: `{summary["version"]}`
- Run ID: `{summary["run_id"]}`
- Config fingerprint: `{summary["config_fingerprint"]}`
- Result status: **{result_status}**
- Completion: `{summary["completion_rate"]:.1f}%`
- Safety gate: **{safety}**

## Three-trial result

| Metric | Result |
|---|---:|
| Scenarios per trial | {summary["scenarios_per_trial"]} |
| Trials | {summary["trials"]} |
| Mean score | {summary["score_mean"]:.1f} |
| Median score | {summary["score_median"]:.1f} |
| Score standard deviation | {summary["score_stddev"]:.1f} |
| 95% bootstrap interval | {summary["score_ci95"][0]:.1f}–{summary["score_ci95"][1]:.1f} |
| Pass@3 (passed at least once) | {summary["pass_at_3"]:.1f}% |
| Pass^3 (passed every trial) | {summary["pass_hat_3"]:.1f}% |
| Reliability gap | {summary["reliability_gap"]:.1f} points |

## Categories

| Category | Mean | Trial stddev |
|---|---:|---:|
{categories}

## Non-passing or variable scenarios

Only deterministic identifiers and scores are retained here. Consult the private
raw run when diagnosing behavior.

| Scenario | Category | Aggregate status | Trial points | Infrastructure failure |
|---|---|---|---|---|
{failures}

## Evidence boundary

- These are public scenarios and may be represented in model training data.
- Mock tools test tool selection, parameters, chaining, recovery, and boundaries;
  they do not validate a production tool implementation.
- Each scenario is one assistant conversation. This does not test delegation,
  independent agents, or inter-agent handoffs.
- Chat templates, tool parsers, reasoning settings, and serving runtimes can
  materially change the result even when model weights are unchanged.
- This score is a serving-stack tool-use result, not a general intelligence or
  safety certification.
'''


def _matching_brace(text: str, start: int) -> int:
    depth = 0
    quoted = False
    escaped = False
    for index in range(start, len(text)):
        character = text[index]
        if quoted:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                quoted = False
            continue
        if character == '"':
            quoted = True
        elif character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                return index
    raise ImportError("catalog contains an unterminated object")


def _tool_eval_field(summary: dict[str, Any]) -> str:
    lines = json.dumps(summary, indent=2).splitlines()
    return '\n'.join(
        ['      "tool_eval": ' + lines[0]]
        + ['      ' + line for line in lines[1:]]
    )


def update_catalog_text(
    catalog_text: str, baseline_id: str, summary: dict[str, Any]
) -> str:
    marker = f'"id": {json.dumps(baseline_id)}'
    marker_at = catalog_text.find(marker)
    if marker_at < 0:
        raise ImportError(f"unknown baseline id: {baseline_id}")
    object_start = catalog_text.rfind("{", 0, marker_at)
    object_end = _matching_brace(catalog_text, object_start)
    baseline_text = catalog_text[object_start:object_end + 1]
    field = _tool_eval_field(summary)
    existing = baseline_text.find('"tool_eval":')
    if existing >= 0:
        field_start = baseline_text.rfind("\n", 0, existing) + 1
        value_start = baseline_text.find("{", existing)
        value_end = _matching_brace(baseline_text, value_start)
        updated = baseline_text[:field_start] + field + baseline_text[value_end + 1:]
    else:
        close_line = baseline_text.rfind("\n    }")
        if close_line < 0:
            updated = (
                baseline_text[:-1].rstrip()
                + ', "tool_eval": '
                + json.dumps(summary, separators=(",", ":"))
                + "}"
            )
        else:
            updated = (
                baseline_text[:close_line].rstrip()
                + ",\n"
                + field
                + baseline_text[close_line:]
            )
    return catalog_text[:object_start] + updated + catalog_text[object_end + 1:]


def import_result(
    raw_dir: Path, baseline_id: str, report_name: str
) -> tuple[Path, dict[str, Any]]:
    if not re.fullmatch(r"[A-Za-z0-9._-]+\.md", report_name):
        raise ImportError("report name must be a plain Markdown filename")
    manifest = load_object(raw_dir / "manifest.json")
    result = load_object(raw_dir / "tool-eval-standard.json")
    profile = manifest.get("tool_eval_profile")
    if not isinstance(profile, dict):
        raise ImportError("run manifest has no tool-eval profile")
    published_profile = load_object(PUBLISHED_PROFILE)
    identity_keys = ("protocol_id", "commit", "standard_scenarios", "trials")
    if any(profile.get(key) != published_profile.get(key) for key in identity_keys):
        raise ImportError("run profile does not match the versioned publication profile")
    profile = {
        **profile,
        "scenario_categories": published_profile.get("scenario_categories"),
    }
    if manifest.get("baseline_id") != baseline_id:
        raise ImportError("run manifest baseline does not match --baseline-id")

    catalog_text = CATALOG.read_text(encoding="utf-8")
    catalog = load_object(CATALOG)
    if catalog.get("schema_version") != 6:
        raise ImportError("results/catalog.json must use schema_version 6")
    baseline = next(
        (item for item in catalog.get("baselines", []) if item.get("id") == baseline_id),
        None,
    )
    if baseline is None:
        raise ImportError(f"unknown baseline id: {baseline_id}")
    model = next(
        (item for item in catalog.get("models", []) if item.get("id") == baseline.get("model_id")),
        None,
    )
    if model is None:
        raise ImportError("baseline references an unknown model")

    summary, non_pass = sanitize_tool_result(result, profile)
    report_path = RESULTS / report_name
    summary["report"] = report_name
    report_path.write_text(
        render_report(baseline, model, summary, non_pass), encoding="utf-8"
    )
    baseline["tool_eval"] = summary
    CATALOG.write_text(
        update_catalog_text(catalog_text, baseline_id, summary), encoding="utf-8"
    )
    return report_path, summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--baseline-id", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args(argv)
    try:
        path, _summary = import_result(args.raw_dir, args.baseline_id, args.report)
    except ImportError as exc:
        print(f"tool-eval import failed: {exc}", file=sys.stderr)
        return 1
    print(f"CURATED_REPORT {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
