from __future__ import annotations

import math
import statistics
from typing import Iterable

from .client import RequestResult


def percentile(values: Iterable[float], percentile_value: float) -> float | None:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return None
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * percentile_value / 100.0
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _round(value: float | None, digits: int = 4) -> float | None:
    return None if value is None else round(value, digits)


def summarize(
    results: list[RequestResult], wall_seconds: float, concurrency: int
) -> dict[str, object]:
    successful = [result for result in results if result.error is None]
    ttfts = [r.ttft_seconds for r in successful if r.ttft_seconds is not None]
    e2es = [r.e2e_seconds for r in successful]
    chunk_itls = [
        interval for result in successful
        for interval in result.chunk_intervals_seconds
    ]
    decode_rates = []
    for result in successful:
        decode_time = result.e2e_seconds - (result.ttft_seconds or 0.0)
        if result.completion_tokens > 1 and decode_time > 0:
            decode_rates.append(result.completion_tokens / decode_time)
    prompt_tokens = sum(r.prompt_tokens for r in successful)
    completion_tokens = sum(r.completion_tokens for r in successful)
    checks = [r for r in successful if r.expected is not None]
    return {
        "concurrency": concurrency,
        "requests": len(results),
        "successful_requests": len(successful),
        "failed_requests": len(results) - len(successful),
        "quality_checks": len(checks),
        "quality_passed": sum(1 for r in checks if r.passed),
        "wall_seconds": _round(wall_seconds),
        "request_throughput_rps": _round(len(successful) / wall_seconds),
        "input_throughput_tps": _round(prompt_tokens / wall_seconds),
        "output_throughput_tps": _round(completion_tokens / wall_seconds),
        "total_prompt_tokens": prompt_tokens,
        "total_completion_tokens": completion_tokens,
        "ttft_mean_ms": _round(statistics.fmean(ttfts) * 1000 if ttfts else None, 2),
        "ttft_p50_ms": _round(percentile(ttfts, 50) * 1000 if ttfts else None, 2),
        "ttft_p95_ms": _round(percentile(ttfts, 95) * 1000 if ttfts else None, 2),
        "e2e_mean_seconds": _round(statistics.fmean(e2es) if e2es else None),
        "e2e_p50_seconds": _round(percentile(e2es, 50)),
        "e2e_p95_seconds": _round(percentile(e2es, 95)),
        "chunk_itl_p50_ms": _round(
            percentile(chunk_itls, 50) * 1000 if chunk_itls else None, 2
        ),
        "chunk_itl_p95_ms": _round(
            percentile(chunk_itls, 95) * 1000 if chunk_itls else None, 2
        ),
        "per_request_decode_tps_mean": _round(
            statistics.fmean(decode_rates) if decode_rates else None
        ),
        "per_request_decode_tps_p50": _round(percentile(decode_rates, 50)),
        "per_request_decode_tps_p95": _round(percentile(decode_rates, 95)),
    }


def add_concurrency_effectiveness(scenarios: list[dict[str, object]]) -> None:
    baselines: dict[str, float] = {}
    for scenario in scenarios:
        config = scenario["config"]
        summary = scenario["summary"]
        group = config.get("comparison_group")
        if group and int(summary["concurrency"]) == 1:
            throughput = float(summary["output_throughput_tps"] or 0)
            if throughput > 0:
                baselines[str(group)] = throughput
    for scenario in scenarios:
        config = scenario["config"]
        summary = scenario["summary"]
        group = config.get("comparison_group")
        baseline = baselines.get(str(group)) if group else None
        if not baseline:
            continue
        concurrency = int(summary["concurrency"])
        throughput = float(summary["output_throughput_tps"] or 0)
        speedup = throughput / baseline
        summary["throughput_speedup_vs_c1"] = round(speedup, 4)
        summary["parallel_efficiency"] = round(speedup / concurrency, 4)
