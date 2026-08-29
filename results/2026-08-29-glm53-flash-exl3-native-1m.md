# GLM-5.3-Flash-EXL3 two-Spark serving baseline

Date: 2026-08-29

Status: **PASS; use concurrency 1 for interactive latency and up to 4 for batch throughput**

> Serving recipe credit: This deployment uses [MiaAI-Lab's original GLM-5.3-Flash-EXL3 two-DGX-Spark recipe](https://github.com/MiaAI-Lab/GLM-5.3-Flash-EXL3-2x-DGX-Sparks/tree/79f10b91f84779b2b1ff2c9327b1a5847cd97f70). The serving launcher and GB10 overlay originate from MiaAI-Lab; this document reports independent measurements of that recipe.

## Configuration

- Model: `GLM-5.3-Flash-EXL3`
- Weights: EXL3/TR3 uniform-K4, 4 bpw, 120 shards
- Serving topology: two DGX Sparks, tensor parallelism 2
- Runtime recipe commit: `79f10b91f84779b2b1ff2c9327b1a5847cd97f70`
- Runtime image digest: `sha256:9bb1557a4234fce63d59599e44d10747eabd742beb337eebf9e7070be8a0fd58`
- Context length: `1000000`
- Maximum running sequences: `4`
- Chunked prefill size: `2048`
- GPU memory utilization: `0.87`
- Target KV: fp8 sparse MLA (`fp8_ds_mla`)
- Speculative decoding: DFlash2 k=7, draft TP1
- Prefix caching, tools, reasoning, and vision: enabled
- Load generator: separate host, direct OpenAI-compatible endpoint
- Benchmark harness commit: `6dfddf22382418e503d488bd49a2388348548330`, plus the GLM reasoning-stream compatibility change described below

The standard suite ran for 50 minutes and 54 seconds. It issued 231 measured
requests, 1,141,850 prompt tokens, and 103,295 completion tokens with zero
request errors. The 240K retrieval and deterministic canaries passed 13/13.

## Decode concurrency

Each request used approximately 256 input tokens and a forced 512-token
completion. Throughput is aggregate output tokens per second.

| Concurrency | Output tok/s | Speedup vs c1 | Parallel efficiency | TTFT p95 | E2E p95 |
|---:|---:|---:|---:|---:|---:|
| 1 | 35.13 | 1.00x | 100% | **0.95s** | 15.65s |
| 2 | 40.52 | 1.15x | 58% | 15.78s | 28.07s |
| 4 | 62.52 | 1.78x | 44% | 23.65s | 36.14s |
| 8 | 70.02 | 1.99x | 25% | 50.09s | 61.89s |
| 12 | 76.97 | 2.19x | 18% | 65.28s | 89.87s |
| 16 | **79.51** | **2.26x** | 14% | 91.26s | 110.07s |

Concurrency 16 maximized aggregate throughput, but concurrency 1 was the only
interactive-latency result. The server is configured for four active sequences;
higher offered concurrency measures queued batch throughput, not additional
simultaneous execution.

## Prefill and context

| Workload | Input tok/s | TTFT p95 | E2E p95 | Result |
|---|---:|---:|---:|---|
| 4K unique, c1 | 566.73 | 5.00s | 7.43s | Pass |
| 32K unique, c1 | 833.16 | 36.85s | 39.60s | Pass |
| 128K unique, c1 | 882.52 | 147.00s | 149.53s | Pass |
| 240K passkey, c1 | **876.11** | **279.80s** | 280.53s | **1/1 correct** |

The long-context result is a practical strength of this recipe. Under the same
suite, the prior Qwen baseline needed 598.56 seconds to first token for the 240K
passkey request; this GLM run needed 279.80 seconds and remained correct.

## Prefix-cache effectiveness

Four concurrent requests used approximately 32K input tokens and 128 output
tokens each.

| Prefix mode | Input tok/s | Output tok/s | TTFT p95 | E2E p95 |
|---|---:|---:|---:|---:|
| Unique | 794.97 | 3.11 | 153.63s | 159.10s |
| Shared, cold | 2,556.54 | 9.95 | 43.46s | 51.41s |
| Shared, warm | **6,089.78** | **23.71** | **13.91s** | **21.59s** |

The warm shared prefix reduced TTFT p95 by about 11 times versus unique cold
prompts. This vLLM build exposes no cache-reset endpoint, so the harness recorded
cache-flush-unavailable notes. Scenario-specific prompts kept unrelated cases
unique, and the shared cold/warm pair intentionally reused the same prefix.

## Quality validation

- 240K passkey retrieval: 1/1 correct.
- Serial deterministic canaries: 4/4 correct.
- Concurrency-8 deterministic canaries: 8/8 correct.
- Separate preflight canary gate: 12/12 correct.

## Sustained load

The 20-minute concurrency-8 soak completed 98 requests with zero failures.

| Metric | Result |
|---|---:|
| Aggregate output throughput | 38.53 tok/s |
| TTFT p95 | 98.77s |
| E2E p95 | 118.25s |
| Requests completed | 98 |

Live midpoint state showed four running and four queued requests, with zero
abort/error counters. Both rank containers remained running with zero restarts
and no OOM flag. No kernel OOM or GPU Xid event was found in postflight.

## Operational recommendation

Use concurrency 1 when interactive response time matters. Use concurrency 4 as
the practical batch/burst target: it delivered 79% of the c16 peak throughput
without offering twelve extra queued clients. Concurrency 8-16 is stable, but
the measured TTFT tails make it a throughput-only posture.

Compared with the prior Qwen baseline on the same two-Spark hardware and suite,
this GLM recipe is much faster at 240K prefill but materially slower at concurrent
decode and mixed 1K-prefill soak traffic. Treat that as a workload-routing
tradeoff, not a general quality ranking.

## Harness and method notes

- GLM streams reasoning in `delta.reasoning`; the pinned harness originally
  recognized only `reasoning_content` variants, producing `TTFT=None`.
- The first full pass was stopped after decode c1. A narrow compatibility change
  now accepts `reasoning`, `reasoning_content`, and both provider-specific forms.
- A regression test was added; all nine harness tests pass. The completed suite
  was restarted from the beginning after the server drained to zero running and
  zero waiting requests.
- Optional SSH telemetry was omitted because the load generator's persistent
  host-key records did not validate. This matches the earlier Qwen raw baseline,
  which also has no persisted host samples. Container, GPU, memory, and kernel
  postflight checks were run separately.
- Raw output remains local because it can contain generated reasoning text. The
  endpoint URL and SSH targets are omitted from persisted benchmark output.
