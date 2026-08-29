from __future__ import annotations

import re


SELECTED = {
    "sglang:max_total_num_tokens", "sglang:kv_cache_memory_usage_gb",
    "sglang:num_running_reqs", "sglang:num_queue_reqs", "sglang:token_usage",
    "sglang:full_token_usage", "sglang:mamba_usage",
    "sglang:kv_available_tokens", "sglang:kv_evictable_tokens",
    "sglang:kv_used_tokens", "sglang:mamba_available_tokens",
    "sglang:mamba_evictable_tokens", "sglang:mamba_used_tokens",
    "sglang:spec_accept_length", "sglang:spec_accept_rate",
    "sglang:gen_throughput", "sglang:cache_hit_rate",
    "sglang:prompt_tokens_total", "sglang:generation_tokens_total",
    "sglang:num_requests_total", "sglang:num_retracted_reqs",
}

SAMPLE = re.compile(
    r"^(?P<name>[^\s{]+)(?:\{(?P<labels>[^}]*)\})?\s+(?P<value>[-+0-9.eE]+)$"
)


def parse_selected_metrics(text: str | None) -> dict[str, float]:
    if not text:
        return {}
    totals: dict[str, float] = {}
    for line in text.splitlines():
        match = SAMPLE.match(line)
        if not match or match.group("name") not in SELECTED:
            continue
        name = match.group("name")
        value = float(match.group("value"))
        if name.endswith("_total"):
            totals[name] = totals.get(name, 0.0) + value
        else:
            totals[name] = value
    return totals


def metric_delta(before: dict[str, float], after: dict[str, float]) -> dict[str, float]:
    return {
        key: round(after[key] - before[key], 6)
        for key in sorted(before.keys() & after.keys())
        if key.endswith("_total")
    }
