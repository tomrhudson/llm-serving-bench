# Qwen3.8 27B Uncensored FP8 single-Spark serving baseline

Date: 2026-10-02

Status: **PASS with an operational concurrency recommendation of 4**

> Serving recipe: [MiaAI-Lab Qwen3.8 27B SGLang recipe](https://github.com/MiaAI-Lab/Qwen3.8-27B-SGLang-DGX-Spark/tree/5d2df792a2ca7e076cb80b8302f5349d492d6f54), adapted to the derivative checkpoint.

## Configuration

- Model: `orcarouter/Qwen3.8-27B-Uncensored-FP8`, revision
  `830602f9b81d083db78f60e889bca37b73b74469`
- Hardware: one NVIDIA DGX Spark with 128GB unified memory
- Runtime: SGLang container
  `lmsysorg/sglang@sha256:febfb971c7352570fc445c466ebd6ffc9d896024958e544a60f2137fd85856b1`
- Load generator: separate host, direct OpenAI-compatible endpoint
- Context length: `262144`
- Static memory fraction: `0.82`
- Maximum running requests: `4`
- Maximum Mamba cache size: `32`
- Chunked prefill size: `8192`
- KV cache: FP8 E4M3
- Speculative decoding: EAGLE, three steps, top-k 1, four draft tokens
- Benchmark mode: thinking disabled per request

The 17-scenario standard suite ran for 60 minutes and 6 seconds. It issued
290 measured requests with zero transport or serving errors.

## Decode concurrency

Each request used approximately 256 input tokens and a forced 512-token
completion. Throughput is aggregate output tokens per second.

| Concurrency | Output tok/s | Speedup vs c1 | Parallel efficiency | TTFT p95 | E2E p95 |
|---:|---:|---:|---:|---:|---:|
| 1 | 18.60 | 1.00x | 100% | 0.28s | 30.04s |
| 2 | 36.82 | 1.98x | 99% | 0.47s | 29.74s |
| 4 | **72.86** | **3.92x** | **98%** | **0.84s** | **30.93s** |
| 8 | 69.59 | 3.74x | 47% | 31.51s | 60.44s |
| 12 | 68.50 | 3.68x | 31% | 67.37s | 92.77s |
| 16 | 70.81 | 3.81x | 24% | 88.06s | 117.35s |

Concurrency 4 was both the throughput peak and the clear latency knee.
Higher offered concurrency queued behind the four-request admission limit
without increasing aggregate throughput.

## Prefill and context

| Workload | Input tok/s | TTFT p95 | E2E p95 | Result |
|---|---:|---:|---:|---|
| 4K unique, c1 | 547.32 | 3.44s | 7.71s | Pass |
| 32K unique, c1 | 710.55 | 41.82s | 46.54s | Pass |
| 128K unique, c1 | 563.45 | 228.68s | 232.99s | Pass |
| 240K passkey, c1 | 439.89 | 557.96s | 558.73s | **1/1 correct** |

The native 262K window was functional through the suite's 240K retrieval
check. Near-window prefill took more than nine minutes, so it is a batch
document workload rather than an interactive request shape.

## Prefix-cache effectiveness

Four concurrent requests used approximately 32K input tokens and 128 output
tokens each.

| Prefix mode | Output tok/s | TTFT p95 | E2E p95 |
|---|---:|---:|---:|
| Unique | 2.77 | 168.87s | 183.55s |
| Shared, cold | 10.07 | 41.57s | 50.85s |
| Shared, warm | **47.25** | **1.00s** | **10.73s** |

Warm shared-prefix reuse reduced TTFT p95 by about 168 times versus unique
prefixes in this four-request workload.

## Quality validation

- 240K passkey retrieval: 1/1 correct.
- Serial deterministic canaries: 4/4 correct.
- Concurrency-8 deterministic canaries: 8/8 correct.

These checks detect obvious serving regressions; they are not a broad model
quality or safety evaluation. This derivative checkpoint is not the upstream
Qwen release.

## Sustained load

The 20-minute concurrency-8 soak completed 157 requests and 80,384 output
tokens with zero failures.

| Metric | Result |
|---|---:|
| Aggregate output throughput | 63.89 tok/s |
| TTFT p95 | 36.05s |
| E2E p95 | 68.50s |
| Per-request decode p50 | 16.46 tok/s |
| Request throughput | 0.125 req/s |

## Operational recommendation

Use **concurrency 4** for interactive or agent traffic. Concurrency 8 is a
valid sustained-load setting only when roughly 30-36 seconds of queueing is
acceptable; offering more load did not improve throughput.

Treat this as a dedicated one-Spark lane. Docker reported no OOM and zero
restarts during the measured run. The endpoint continued returning 200
responses after the soak and was then stopped intentionally.

## Method notes

- The suite used `chat_template_kwargs.enable_thinking=false` for comparable
  throughput and deterministic checks.
- Streaming TTFT is measured at the first content or reasoning token.
- Chunk intervals approximate inter-token latency because a streaming chunk
  can contain more than one token.
- Raw JSON was retained privately but was not published because it contains
  generated model output and operational telemetry. This report contains no
  endpoint URL, SSH target, username, credential, or internal address.
