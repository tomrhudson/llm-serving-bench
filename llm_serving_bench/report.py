from __future__ import annotations

from pathlib import Path
from typing import Any


def markdown_report(run: dict[str, Any]) -> str:
    lines = [
        f"# LLM serving benchmark: {run['label']}", "",
        f"- Model: `{run['model']}`",
        f"- Started: `{run['started_at']}`",
        f"- Endpoint: `{run['server_label']}`",
        f"- Suite: `{run['suite_name']}`", "",
        "| Scenario | C | Requests | Output tok/s | TTFT p95 ms | E2E p95 s | Speedup | Efficiency | Errors | Checks |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for scenario in run["scenarios"]:
        summary = scenario["summary"]
        checks = f"{summary['quality_passed']}/{summary['quality_checks']}"
        lines.append(
            "| {name} | {concurrency} | {requests} | {output} | {ttft} | "
            "{e2e} | {speedup} | {efficiency} | {errors} | {checks} |".format(
                name=scenario["config"]["name"],
                concurrency=summary["concurrency"],
                requests=summary["requests"],
                output=_fmt(summary.get("output_throughput_tps")),
                ttft=_fmt(summary.get("ttft_p95_ms")),
                e2e=_fmt(summary.get("e2e_p95_seconds")),
                speedup=_fmt(summary.get("throughput_speedup_vs_c1")),
                efficiency=_fmt(summary.get("parallel_efficiency")),
                errors=summary["failed_requests"], checks=checks,
            )
        )
    lines.extend(["", "## Capacity snapshot", ""])
    for key, value in sorted(run.get("server_metrics_after", {}).items()):
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Notes", ""])
    lines.extend(f"- {note}" for note in run.get("notes", []))
    return "\n".join(lines) + "\n"


def write_report(path: str | Path, text: str) -> None:
    Path(path).write_text(text, encoding="utf-8")


def _fmt(value: object) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)
