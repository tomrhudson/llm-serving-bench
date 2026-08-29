from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import json
import os
import platform
import time
from pathlib import Path
from typing import Any

from .client import OpenAIClient, RequestResult
from .metrics import metric_delta, parse_selected_metrics
from .monitor import HostMonitor
from .report import markdown_report, write_report
from .stats import add_concurrency_effectiveness, summarize
from .workloads import PreparedRequest, PromptFactory, prepare_requests


def run_requests(
    client: OpenAIClient,
    prepared: list[PreparedRequest],
    concurrency: int,
) -> tuple[list[RequestResult], float]:
    started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [
            executor.submit(
                client.chat, item.request_id, item.prompt, item.output_tokens,
                temperature=item.temperature, ignore_eos=item.ignore_eos,
                expected=item.expected, extra_body=item.extra_body,
            )
            for item in prepared
        ]
        results = [future.result() for future in futures]
    return results, time.perf_counter() - started


def run_duration_requests(
    client: OpenAIClient,
    prepared: list[PreparedRequest],
    concurrency: int,
    duration_seconds: float,
) -> tuple[list[RequestResult], float]:
    """Hold a fixed concurrency until the duration expires."""
    started = time.perf_counter()
    deadline = started + duration_seconds

    def worker(worker_id: int) -> list[RequestResult]:
        completed: list[RequestResult] = []
        sequence = 0
        while time.perf_counter() < deadline:
            item = prepared[(worker_id + sequence * concurrency) % len(prepared)]
            completed.append(client.chat(
                f"{item.request_id}-w{worker_id}-n{sequence}",
                item.prompt,
                item.output_tokens,
                temperature=item.temperature,
                ignore_eos=item.ignore_eos,
                expected=item.expected,
                extra_body=item.extra_body,
            ))
            sequence += 1
        return completed

    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        batches = list(executor.map(worker, range(concurrency)))
    return [result for batch in batches for result in batch], time.perf_counter() - started


def execute(args: argparse.Namespace) -> dict[str, Any]:
    suite = json.loads(Path(args.suite).read_text(encoding="utf-8"))
    api_key = os.environ.get(args.api_key_env) if args.api_key_env else None
    client = OpenAIClient(args.base_url, args.model, api_key, args.timeout)
    models = client.models()
    served = [item.get("id") for item in models.get("data", [])]
    if args.model not in served:
        raise SystemExit(f"model {args.model!r} not present in /v1/models: {served}")

    hosts = dict(_parse_mapping(item) for item in args.monitor_host)
    monitor = HostMonitor(hosts, interval=args.monitor_interval)
    factory = PromptFactory(client, seed=int(suite.get("seed", 20260829)))
    started = dt.datetime.now(dt.timezone.utc)
    run: dict[str, Any] = {
        "schema_version": 1, "label": args.label, "model": args.model,
        "server_label": args.server_label,
        "suite_name": suite.get("name", Path(args.suite).stem),
        "suite": suite, "started_at": started.isoformat(),
        "runner": {"python": platform.python_version(), "platform": platform.platform()},
        "server_metrics_before": parse_selected_metrics(client.metrics_text()),
        "scenarios": [],
        "notes": [
            "The persisted artifact intentionally omits endpoint URLs and SSH targets.",
            "Streaming chunk intervals approximate ITL; output TPS and TTFT use request usage/timing.",
        ],
    }

    monitor.start()
    try:
        for config in suite["scenarios"]:
            if config.get("flush_cache") and not client.flush_cache():
                run["notes"].append(
                    f"Cache flush was unavailable before {config['name']}."
                )
            print(f"PREP {config['name']}", flush=True)
            prepared = prepare_requests(config, factory)
            before = parse_selected_metrics(client.metrics_text())
            concurrency = int(config.get("concurrency", 1))
            duration = float(config.get("duration_seconds", 0))
            run_detail = (
                f"duration={duration:.0f}s" if duration > 0
                else f"requests={len(prepared)}"
            )
            print(f"RUN  {config['name']} c={concurrency} {run_detail}", flush=True)
            if duration > 0:
                results, wall = run_duration_requests(
                    client, prepared, concurrency, duration
                )
            else:
                results, wall = run_requests(client, prepared, concurrency)
            after = parse_selected_metrics(client.metrics_text())
            summary = summarize(results, wall, concurrency)
            run["scenarios"].append({
                "config": config,
                "prepared_prompt_tokens": [p.prepared_prompt_tokens for p in prepared],
                "summary": summary, "metrics_before": before,
                "metrics_after": after, "metric_deltas": metric_delta(before, after),
                "requests": [
                    result.to_dict(include_text=result.expected is not None)
                    for result in results
                ],
            })
            print(
                "DONE {name} output_tps={tps} ttft_p95_ms={ttft} errors={errors}".format(
                    name=config["name"], tps=summary["output_throughput_tps"],
                    ttft=summary["ttft_p95_ms"], errors=summary["failed_requests"],
                ), flush=True,
            )
    finally:
        monitor.stop()

    add_concurrency_effectiveness(run["scenarios"])
    run["server_metrics_after"] = parse_selected_metrics(client.metrics_text())
    run["host_samples"] = monitor.samples
    finished = dt.datetime.now(dt.timezone.utc)
    run["finished_at"] = finished.isoformat()
    run["duration_seconds"] = round((finished - started).total_seconds(), 3)
    return run


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark an OpenAI-compatible streaming LLM endpoint."
    )
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--suite", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--server-label", default="redacted-direct-endpoint")
    parser.add_argument("--api-key-env")
    parser.add_argument("--timeout", type=float, default=900)
    parser.add_argument(
        "--monitor-host", action="append", default=[], metavar="LABEL=SSH_TARGET"
    )
    parser.add_argument("--monitor-interval", type=float, default=5.0)
    args = parser.parse_args(argv)

    run = execute(args)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")
    report_path = output.with_suffix(".md")
    write_report(report_path, markdown_report(run))
    print(f"RESULT_JSON {output}")
    print(f"RESULT_MD   {report_path}")


def _parse_mapping(value: str) -> tuple[str, str]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("mapping must be LABEL=VALUE")
    label, target = value.split("=", 1)
    if not label or not target:
        raise argparse.ArgumentTypeError("mapping must be LABEL=VALUE")
    return label, target


if __name__ == "__main__":
    main()
