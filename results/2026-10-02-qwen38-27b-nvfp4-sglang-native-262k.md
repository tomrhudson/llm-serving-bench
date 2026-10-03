# Qwen3.8 27B NVFP4 single-Spark serving baseline

Date: 2026-10-02

Status: **PASS with an operational concurrency recommendation of 8**

> Serving recipe: [MiaAI-Lab Qwen3.8 27B SGLang recipe](https://github.com/MiaAI-Lab/Qwen3.8-27B-SGLang-DGX-Spark/tree/5d2df792a2ca7e076cb80b8302f5349d492d6f54).

## Configuration

- Model: `RadixArk/Qwen3.8-27B-NVFP4`, revision
  `319f741cce68d7914884900c138a1fbb70a42f30`
- Hardware: one NVIDIA DGX Spark with 128GB unified memory
- Runtime: SGLang container
  `lmsysorg/sglang@sha256:febfb971c7352570fc445c466ebd6ffc9d896024958e544a60f2137fd85856b1`
- Load generator: separate host, direct OpenAI-compatible endpoint
- Context length: `262144`
- Static memory fraction: `0.95`
- Maximum running requests: `10`
- Maximum Mamba cache size: `80`
- Chunked prefill size: `8192`
- KV cache: FP8 E4M3
- Speculative decoding: EAGLE, three steps, top-k 1, four draft tokens
- Benchmark mode: thinking disabled per request

The 17-scenario standard suite ran for 42 minutes and 47 seconds. It issued
510 measured requests with zero transport or serving errors.

## Decode concurrency

Each request used approximately 256 input tokens and a forced 512-token
completion. Throughput is aggregate output tokens per second.

| Concurrency | Output tok/s | Speedup vs c1 | Parallel efficiency | TTFT p95 | E2E p95 |
|---:|---:|---:|---:|---:|---:|
| 1 | 31.83 | 1.00x | 100% | 0.18s | 17.25s |
| 2 | 57.03 | 1.79x | 90% | 0.42s | 19.73s |
| 4 | 98.93 | 3.11x | 78% | 0.78s | 23.12s |
| 8 | 167.35 | 5.26x | 66% | 1.63s | 26.16s |
| 12 | 184.12 | 5.79x | 48% | 20.23s | 41.55s |
| 16 | **187.63** | **5.90x** | 37% | 23.50s | 48.34s |

Concurrency 16 produced the highest aggregate decode throughput, but it was
only 12% faster than concurrency 8 while TTFT p95 rose from 1.63 seconds to
23.50 seconds. Use concurrency 8 as the practical operating point and treat
12-16 as queued batch traffic.

## Prefill and context

| Workload | Input tok/s | TTFT p95 | E2E p95 | Result |
|---|---:|---:|---:|---|
| 4K unique, c1 | 968.66 | 1.90s | 4.36s | Pass |
| 32K unique, c1 | 1,402.94 | 21.15s | 23.49s | Pass |
| 128K unique, c1 | 908.73 | 141.58s | 144.33s | Pass |
| 240K passkey, c1 | 621.28 | 395.05s | 395.60s | **1/1 correct** |

The native 262K window was functional through the suite's 240K retrieval
check. Near-window prefill is a deliberate long-document workload, not an
interactive request shape.

## Prefix-cache effectiveness

Four concurrent requests used approximately 32K input tokens and 128 output
tokens each.

| Prefix mode | Output tok/s | TTFT p95 | E2E p95 |
|---|---:|---:|---:|
| Unique | 5.78 | 79.85s | 88.55s |
| Shared, cold | 18.58 | 20.86s | 27.49s |
| Shared, warm | **70.16** | **1.03s** | **7.30s** |

Warm shared-prefix reuse reduced TTFT p95 by about 77 times versus unique
prefixes in this four-request workload.

## Quality validation

- 240K passkey retrieval: 1/1 correct.
- Serial deterministic canaries: 4/4 correct.
- Concurrency-8 deterministic canaries: 8/8 correct.

These checks detect obvious serving regressions; they are not a broad model
quality evaluation.

## Sustained load

The 20-minute concurrency-8 soak completed 377 requests and 193,024 output
tokens with zero failures.

| Metric | Result |
|---|---:|
| Aggregate output throughput | 157.80 tok/s |
| TTFT p95 | 1.01s |
| E2E p95 | 29.17s |
| Per-request decode p50 | 20.38 tok/s |
| Request throughput | 0.308 req/s |

## Operational recommendation

Use **concurrency 8** for mixed interactive or agent traffic. Higher offered
concurrency adds only modest throughput and sharply increases TTFT because the
server admits at most ten running requests.

Treat this as a dedicated one-Spark lane. Postflight showed the exact model,
no container OOM, no logged traceback or serving error, and only a few GiB of
host memory headroom after load.

## Method notes

- The suite used `chat_template_kwargs.enable_thinking=false` for comparable
  throughput and deterministic checks.
- Streaming TTFT is measured at the first content or reasoning token.
- Chunk intervals approximate inter-token latency because a streaming chunk
  can contain more than one token.
- Raw JSON was retained privately but was not published because it contains
  generated model output and operational telemetry. This report contains no
  endpoint URL, SSH target, username, credential, or internal address.
