#!/usr/bin/env python3
"""Generate the published-results comparison page and dependency-free SVG charts."""

from __future__ import annotations

import argparse
import html
import json
import math
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
CATALOG = RESULTS / "catalog.json"
SUMMARY = RESULTS / "README.md"
MODEL_GUIDE = RESULTS / "MODEL-GUIDE.md"
ASSETS = RESULTS / "assets"
COLORS = ["#2563eb", "#dc2626", "#059669", "#9333ea", "#ea580c", "#0891b2", "#4f46e5", "#be123c"]
DASHES = ["", "8 5", "3 4", "12 4 3 4"]


def _load_catalog() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    data = json.loads(CATALOG.read_text())
    if data.get("schema_version") != 3:
        raise ValueError("unsupported results/catalog.json schema_version")
    models = data.get("models")
    if not isinstance(models, list) or not models:
        raise ValueError("results/catalog.json must contain at least one model")
    required_model = {
        "id", "name", "tagline", "official_source", "dgx_spark_count",
        "dgx_spark_memory_gb_each", "tested_choice", "best_for", "not_for",
        "selection_note", "evidence_note",
    }
    model_ids: set[str] = set()
    for model in models:
        missing = required_model - model.keys()
        if missing:
            raise ValueError(f"{model.get('id', '<unknown>')} missing: {sorted(missing)}")
        if model["id"] in model_ids:
            raise ValueError(f"duplicate model id: {model['id']}")
        model_ids.add(model["id"])
        for field in ("dgx_spark_count", "dgx_spark_memory_gb_each"):
            if not isinstance(model[field], int) or model[field] <= 0:
                raise ValueError(f"{model['id']} {field} must be a positive integer")
        for field in ("best_for", "not_for"):
            if not isinstance(model[field], list) or not model[field]:
                raise ValueError(f"{model['id']} {field} must be a non-empty list")

    baselines = data.get("baselines")
    if not isinstance(baselines, list) or not baselines:
        raise ValueError("results/catalog.json must contain at least one baseline")
    required = {
        "id", "model_id", "label", "chart_label", "date", "report", "hardware", "runtime",
        "context_tokens", "recipe_credit", "recommendation", "decode", "prefill",
        "prefix", "soak", "quality",
    }
    seen: set[str] = set()
    for baseline in baselines:
        missing = required - baseline.keys()
        if missing:
            raise ValueError(f"{baseline.get('id', '<unknown>')} missing: {sorted(missing)}")
        if baseline["id"] in seen:
            raise ValueError(f"duplicate baseline id: {baseline['id']}")
        seen.add(baseline["id"])
        if baseline["model_id"] not in model_ids:
            raise ValueError(
                f"{baseline['id']} references unknown model id: {baseline['model_id']}"
            )
        if not (RESULTS / baseline["report"]).is_file():
            raise ValueError(f"missing report: {baseline['report']}")
    for model in models:
        if model["tested_choice"] not in seen:
            raise ValueError(
                f"{model['id']} references unknown tested choice: {model['tested_choice']}"
            )
        selected = next(item for item in baselines if item["id"] == model["tested_choice"])
        if selected["model_id"] != model["id"]:
            raise ValueError(
                f"{model['id']} tested choice belongs to {selected['model_id']}"
            )
        if not any(item["model_id"] == model["id"] for item in baselines):
            raise ValueError(f"{model['id']} has no published baselines")
    return models, baselines


def _fmt_context(tokens: int) -> str:
    if tokens >= 1_000_000:
        if tokens == 1024 * 1024:
            return "1M"
        return f"{tokens / 1_000_000:g}M"
    if tokens % 1000 == 0:
        return f"{tokens / 1000:g}K"
    return f"{round(tokens / 1024):g}K"


def _fmt_dgx_spark(model: dict[str, Any]) -> str:
    count = model["dgx_spark_count"]
    memory_each = model["dgx_spark_memory_gb_each"]
    total_memory = count * memory_each
    systems = "system" if count == 1 else "systems"
    gpus = "GPU" if count == 1 else "GPUs"
    footprint = (
        f"{count} {systems} / {count} {gpus} · {memory_each}GB each · "
        f"{total_memory}GB aggregate"
    )
    if count > 1:
        footprint += " across nodes"
    return footprint


def _hardware_footprint_markdown(models: list[dict[str, Any]]) -> str:
    counts = sorted({model["dgx_spark_count"] for model in models})
    memory_sizes = sorted({model["dgx_spark_memory_gb_each"] for model in models})
    footprints = ", ".join(
        f"{count}× DGX Spark" for count in counts
    )
    memory = ", ".join(f"{size}GB" for size in memory_sizes)
    return (
        f"Published recipes use {footprints} configurations with {memory} of "
        "unified memory per system. Multi-node capacity is aggregate capacity "
        "across separate systems, not one pooled memory space. Each footprint "
        "describes the exact tested serving recipe rather than a universal model "
        "requirement."
    )


def _nice_ceiling(value: float, steps: int = 5) -> float:
    rough = value / steps
    magnitude = 10 ** math.floor(math.log10(rough)) if rough else 1
    normalized = rough / magnitude
    unit = next(candidate for candidate in (1, 2, 5, 10) if normalized <= candidate)
    return unit * magnitude * steps


def _svg_document(title: str, description: str, width: int, height: int, body: str) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
  <title id="title">{html.escape(title)}</title>
  <desc id="desc">{html.escape(description)}</desc>
  <style>
    :root {{ color-scheme: light dark; }}
    text {{ font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; fill: #24292f; font-size: 12px; }}
    .title {{ font-size: 18px; font-weight: 600; }}
    .subtitle, .tick {{ fill: #57606a; }}
    .grid {{ stroke: #d0d7de; stroke-width: 1; }}
    .axis {{ stroke: #8c959f; stroke-width: 1; }}
    .series {{ fill: none; stroke-width: 3; stroke-linejoin: round; stroke-linecap: round; }}
    .marker {{ stroke: #ffffff; stroke-width: 2; }}
    @media (prefers-color-scheme: dark) {{
      text {{ fill: #f0f6fc; }}
      .subtitle, .tick {{ fill: #8c959f; }}
      .grid {{ stroke: #30363d; }}
      .axis {{ stroke: #6e7681; }}
      .marker {{ stroke: #0d1117; }}
    }}
  </style>
{body}
</svg>
'''


def _legend_layout(
    baselines: list[dict[str, Any]], left: int, right_edge: int
) -> tuple[list[tuple[int, int]], int]:
    positions: list[tuple[int, int]] = []
    x, row = left, 0
    for baseline in baselines:
        entry_width = 64 + len(baseline["chart_label"]) * 8
        if positions and x + entry_width > right_edge:
            x, row = left, row + 1
        positions.append((x, row))
        x += entry_width
    return positions, row + 1


def _line_chart(
    baselines: list[dict[str, Any]],
    *,
    title: str,
    subtitle: str,
    field: str,
    x_key: str,
    y_key: str,
    x_title: str,
    y_title: str,
    x_format: Callable[[float], str],
    log_x: bool = False,
) -> str:
    width = 920
    left, right, bottom = 78, 28, 66
    legend_positions, legend_rows = _legend_layout(baselines, left, width - right)
    top = 96 + (legend_rows - 1) * 24
    height = 470 + (legend_rows - 1) * 24
    plot_w, plot_h = width - left - right, height - top - bottom
    all_points = [point for baseline in baselines for point in baseline[field]]
    xs = sorted({float(point[x_key]) for point in all_points})
    y_max = _nice_ceiling(max(float(point[y_key]) for point in all_points))

    x_min, x_max = min(xs), max(xs)
    tx = math.log10 if log_x else lambda value: value
    tx_min, tx_max = tx(x_min), tx(x_max)

    def sx(value: float) -> float:
        return left + (tx(value) - tx_min) / (tx_max - tx_min) * plot_w

    def sy(value: float) -> float:
        return top + plot_h - value / y_max * plot_h

    parts = [
        f'  <text class="title" x="{left}" y="28">{html.escape(title)}</text>',
        f'  <text class="subtitle" x="{left}" y="50">{html.escape(subtitle)}</text>',
    ]
    for index, (baseline, (legend_x, legend_row)) in enumerate(
        zip(baselines, legend_positions)
    ):
        color = COLORS[index % len(COLORS)]
        dash = DASHES[(index // len(COLORS)) % len(DASHES)]
        legend_y = 72 + legend_row * 24
        parts.append(f'  <line x1="{legend_x}" y1="{legend_y}" x2="{legend_x + 24}" y2="{legend_y}" stroke="{color}" stroke-width="3" stroke-dasharray="{dash}"/>')
        parts.append(f'  <circle cx="{legend_x + 12}" cy="{legend_y}" r="4" fill="{color}"/>')
        parts.append(f'  <text x="{legend_x + 31}" y="{legend_y + 4}">{html.escape(baseline["chart_label"])}</text>')

    for step in range(6):
        value = y_max * step / 5
        y = sy(value)
        parts.append(f'  <line class="grid" x1="{left}" y1="{y:.1f}" x2="{width - right}" y2="{y:.1f}"/>')
        parts.append(f'  <text class="tick" x="{left - 10}" y="{y + 4:.1f}" text-anchor="end">{value:g}</text>')
    for value in xs:
        x = sx(value)
        parts.append(f'  <line class="grid" x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{top + plot_h}"/>')
        parts.append(f'  <text class="tick" x="{x:.1f}" y="{top + plot_h + 24}" text-anchor="middle">{html.escape(x_format(value))}</text>')

    parts.extend([
        f'  <line class="axis" x1="{left}" y1="{top + plot_h}" x2="{width - right}" y2="{top + plot_h}"/>',
        f'  <line class="axis" x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}"/>',
        f'  <text x="{left + plot_w / 2:.1f}" y="{height - 16}" text-anchor="middle">{html.escape(x_title)}</text>',
        f'  <text transform="translate(20 {top + plot_h / 2:.1f}) rotate(-90)" text-anchor="middle">{html.escape(y_title)}</text>',
    ])

    for index, baseline in enumerate(baselines):
        color = COLORS[index % len(COLORS)]
        dash = DASHES[(index // len(COLORS)) % len(DASHES)]
        points = sorted(baseline[field], key=lambda point: point[x_key])
        coordinates = [(sx(float(point[x_key])), sy(float(point[y_key]))) for point in points]
        path = " ".join(("M" if position == 0 else "L") + f" {x:.1f} {y:.1f}" for position, (x, y) in enumerate(coordinates))
        parts.append(f'  <path class="series" d="{path}" stroke="{color}" stroke-dasharray="{dash}"/>')
        for (x, y), point in zip(coordinates, points):
            value = float(point[y_key])
            parts.append(f'  <circle class="marker" cx="{x:.1f}" cy="{y:.1f}" r="5" fill="{color}"><title>{html.escape(baseline["chart_label"])}: {value:g}</title></circle>')

    return _svg_document(title, subtitle, width, height, "\n".join(parts))


def _bar_chart(baselines: list[dict[str, Any]]) -> str:
    width = 920
    left, right, top, bottom = 220, 36, 86, 56
    row_height = 62
    height = top + bottom + row_height * len(baselines)
    plot_w = width - left - right
    maximum = _nice_ceiling(max(float(item["soak"]["output_tps"]) for item in baselines))
    parts = [
        f'  <text class="title" x="{left}" y="28">20-minute concurrency-8 soak throughput</text>',
        f'  <text class="subtitle" x="{left}" y="50">Aggregate output tokens per second; all published runs completed with zero errors</text>',
    ]
    for step in range(6):
        value = maximum * step / 5
        x = left + value / maximum * plot_w
        parts.append(f'  <line class="grid" x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{height - bottom}"/>')
        parts.append(f'  <text class="tick" x="{x:.1f}" y="{height - bottom + 24}" text-anchor="middle">{value:g}</text>')
    for index, baseline in enumerate(baselines):
        value = float(baseline["soak"]["output_tps"])
        y = top + index * row_height + 12
        bar_width = value / maximum * plot_w
        color = COLORS[index % len(COLORS)]
        parts.append(f'  <text x="{left - 12}" y="{y + 20}" text-anchor="end">{html.escape(baseline["chart_label"])}</text>')
        parts.append(f'  <rect x="{left}" y="{y}" width="{bar_width:.1f}" height="28" rx="3" fill="{color}"><title>{value:.2f} output tok/s</title></rect>')
        label_x = min(left + bar_width + 10, width - right - 45)
        parts.append(f'  <text x="{label_x:.1f}" y="{y + 20}">{value:.2f}</text>')
    parts.append(f'  <text x="{left + plot_w / 2:.1f}" y="{height - 12}" text-anchor="middle">Aggregate output throughput (tokens/s)</text>')
    return _svg_document("20-minute concurrency-8 soak throughput", "Aggregate output throughput for every published baseline.", width, height, "\n".join(parts))


def _model_guide_markdown(
    models: list[dict[str, Any]], baselines: list[dict[str, Any]]
) -> str:
    by_id = {item["id"]: item for item in baselines}
    newest = max(item["date"] for item in baselines)
    overview_rows = []
    sections = []

    for model in models:
        selected = by_id[model["tested_choice"]]
        c1 = next(point for point in selected["decode"] if point["concurrency"] == 1)
        peak = max(selected["decode"], key=lambda point: point["output_tps"])
        long_context = max(selected["prefill"], key=lambda point: point["input_tokens"])
        quality = selected["quality"]
        overview_rows.append(
            f'| [{model["name"]}](#{model["id"]}) | {_fmt_dgx_spark(model)} | '
            f'{model["tagline"]} | '
            f'{model["best_for"][0]} | {model["not_for"][0]} |'
        )

        best_for = "\n".join(f'- {item}' for item in model["best_for"])
        not_for = "\n".join(f'- {item}' for item in model["not_for"])
        variants = []
        for item in (entry for entry in baselines if entry["model_id"] == model["id"]):
            variant_c1 = next(
                point for point in item["decode"] if point["concurrency"] == 1
            )
            variant_quality = item["quality"]
            marker = " **(pick)**" if item["id"] == model["tested_choice"] else ""
            variants.append(
                f'| [{item["label"]}]({item["report"]}){marker} | {item["runtime"]} | '
                f'{_fmt_context(item["context_tokens"])} | '
                f'{variant_c1["ttft_p95_seconds"]:.2f}s | '
                f'{item["soak"]["output_tps"]:.2f} | '
                f'{variant_quality["passed"]}/{variant_quality["total"]} | '
                f'{item["recommendation"]} |'
            )

        sections.append(
            f'''<a id="{model["id"]}"></a>
## {model["name"]}

> {model["tagline"]}

**Recommended tested configuration:** [{selected["label"]}]({selected["report"]})

**Upstream:** {model["official_source"]}

| Signal from the selected local baseline | Result |
|---|---:|
| DGX Spark footprint | {_fmt_dgx_spark(model)} |
| Interactive c1 | {c1["output_tps"]:.2f} output tok/s · {c1["ttft_p95_seconds"]:.2f}s TTFT p95 |
| Peak short-prompt decode | {peak["output_tps"]:.2f} output tok/s @ c{peak["concurrency"]} |
| 20-minute c8 soak | {selected["soak"]["output_tps"]:.2f} output tok/s · {selected["soak"]["errors"]} errors |
| Longest tested prompt | {_fmt_context(long_context["input_tokens"])} · {long_context["ttft_p95_seconds"]:.2f}s TTFT p95 |
| Regression canaries | {quality["passed"]}/{quality["total"]} |

### Good fit

{best_for}

### Do not choose it when

{not_for}

### Configuration call

{model["selection_note"]}

{model["evidence_note"]}

### Published variants

| Configuration | Runtime | Configured context | c1 TTFT p95 | Soak tok/s | Canaries | Operating posture |
|---|---|---:|---:|---:|---:|---|
{chr(10).join(variants)}
'''
        )

    return f'''# Model selection dashboard

Use this page to choose among the model families with published DGX Spark
baselines in this repository. For the full cross-configuration numbers and charts,
open the [benchmark summary](README.md).

Last updated: {newest} · Model families: {len(models)} · Published configurations: {len(baselines)}

## Hardware footprint

{_hardware_footprint_markdown(models)}

## Fast decision

| Model | DGX Spark requirement | Position | Good default for | Choose something else when |
|---|---|---|---|---|
{chr(10).join(overview_rows)}

Practical default: start with **Qwen3.8-Flash-Next** for mixed interactive,
coding, RAG, and agent traffic. When only one Spark is available, use
**Qwen3.8 27B NVFP4** for concurrent serving; reserve **DeepSeek V4 Flash** for
one-request-at-a-time long-input work after repairing its documented launch
dependency. Move to **GLM-5.3 Flash** when its long-context coding/agent profile
is the better fit and choose deliberately between the fast TensorFold lane and
the vLLM baselines with their documented quality boundaries. Use **DeepSeek
V4.1 Flash** for input-heavy, low-concurrency work where its clean local
canaries matter more than aggregate serving throughput.

## Evidence boundary

“Good fit” combines upstream model-card positioning with the local serving evidence.
This repository directly measures latency, throughput, stability, a 240K retrieval
check, and small deterministic canaries. It does **not** compare broad intelligence,
safety, production vision quality, tool correctness, or quality at the configured
850K/1M request limits. Validate those against the actual application before routing
production work.

{chr(10).join(sections)}
## Reading the dashboard

- “Configured context” is an accepted request limit, not proof of useful quality at
  that entire length.
- Soak throughput is a serving-capacity signal, not a model-quality score.
- The canaries detect obvious serving regressions; they are intentionally small.
- Quantization, runtime, cache behavior, and transport can change the result even
  when the upstream model family is unchanged.
'''


def _summary_markdown(baselines: list[dict[str, Any]]) -> str:
    rows = []
    for item in baselines:
        peak = max(item["decode"], key=lambda point: point["output_tps"])
        c1 = next(point for point in item["decode"] if point["concurrency"] == 1)
        long_context = max(item["prefill"], key=lambda point: point["input_tokens"])
        quality = item["quality"]
        rows.append(
            f'| [{item["label"]}]({item["report"]}) | {item["hardware"]} / {item["runtime"]} | '
            f'{_fmt_context(item["context_tokens"])} | {peak["output_tps"]:.2f} @ c{peak["concurrency"]} | '
            f'{c1["ttft_p95_seconds"]:.2f}s | {long_context["ttft_p95_seconds"]:.2f}s | '
            f'{item["soak"]["output_tps"]:.2f} | {quality["passed"]}/{quality["total"]} | '
            f'{item["recommendation"]} | {item["recipe_credit"]} |'
        )

    newest = max(item["date"] for item in baselines)
    return f'''# Published benchmark results

This page compares the curated, sanitized baselines in this repository. It is
generated from [`catalog.json`](catalog.json) so new results can extend the
same tables and charts without hand-editing this page.

Choosing a model for a workload? Open the [model selection dashboard](MODEL-GUIDE.md).

Last updated: {newest} · Published baselines: {len(baselines)}

## At a glance

| Model | Hardware / runtime | Configured context | Peak decode tok/s | c1 TTFT p95 | Longest-context TTFT p95 | Soak tok/s | Quality | Recommended concurrency | Recipe credit |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
{chr(10).join(rows)}

Peak decode throughput is useful for batch capacity; c1 TTFT is the better
interactive-latency signal. The longest-context column uses the largest shared
prefill scenario available in the standard suite (currently 240K tokens).

## Decode scaling

![Aggregate decode throughput by offered concurrency](assets/decode-throughput.svg)

Each point uses approximately 256 input tokens and a forced 512-token completion.
Concurrency above the server's active-sequence limit includes queueing.

## Long-context prefill

![Time to first token by prompt length](assets/prefill-ttft.svg)

The prompt-length axis is logarithmic. Lower TTFT is better; every plotted
long-context passkey result was correct.

## Sustained load

![Twenty-minute concurrency-eight soak throughput](assets/soak-throughput.svg)

The soak comparison uses the standard 20-minute concurrency-8 workload. Consult
the linked baseline report for TTFT tails, request counts, and model-specific
operational interpretation.

## Adding another baseline

1. Run the standard suite under comparable hardware, prompt, sampling, and
   token-budget conditions.
2. Review and sanitize the generated output into a curated Markdown report;
   keep raw JSON and generated reasoning private.
3. Add one structured entry to `results/catalog.json`, including any recipe
   credit and the metrics used here.
4. Run `python3 scripts/generate_results_summary.py`, then
   `python3 -m unittest discover -s tests -v`.

The generator validates report links and catalog IDs, then rewrites this page
and the SVG assets deterministically. `--check` verifies that committed output
is current without changing files.

## Comparison limits

- These are serving-system results, not general model-quality rankings.
- Hardware, runtime, quantization, cache state, and active-sequence limits can
  materially change throughput and latency.
- Quality canaries catch obvious serving regressions; they are not a broad
  capability evaluation.
- Read the individual report before drawing conclusions from a single chart.
'''


def _outputs(
    models: list[dict[str, Any]], baselines: list[dict[str, Any]]
) -> dict[Path, str]:
    return {
        SUMMARY: _summary_markdown(baselines),
        MODEL_GUIDE: _model_guide_markdown(models, baselines),
        ASSETS / "decode-throughput.svg": _line_chart(
            baselines,
            title="Decode throughput by offered concurrency",
            subtitle="Higher is better; approximately 256 input and 512 output tokens per request",
            field="decode",
            x_key="concurrency",
            y_key="output_tps",
            x_title="Offered concurrency (requests)",
            y_title="Aggregate output throughput (tokens/s)",
            x_format=lambda value: str(int(value)),
        ),
        ASSETS / "prefill-ttft.svg": _line_chart(
            baselines,
            title="Long-context prefill latency",
            subtitle="Lower is better; c1 unique prompts and a 240K passkey check",
            field="prefill",
            x_key="input_tokens",
            y_key="ttft_p95_seconds",
            x_title="Prompt length (tokens, logarithmic scale)",
            y_title="TTFT p95 (seconds)",
            x_format=lambda value: _fmt_context(int(value)),
            log_x=True,
        ),
        ASSETS / "soak-throughput.svg": _bar_chart(baselines),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail if generated files are stale")
    args = parser.parse_args()
    models, baselines = _load_catalog()
    outputs = _outputs(models, baselines)
    stale = [path for path, content in outputs.items() if not path.exists() or path.read_text() != content]
    if args.check:
        if stale:
            print("stale generated result files:")
            for path in stale:
                print(f"- {path.relative_to(ROOT)}")
            return 1
        print("results summary is current")
        return 0
    ASSETS.mkdir(parents=True, exist_ok=True)
    for path, content in outputs.items():
        path.write_text(content)
        print(f"wrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
