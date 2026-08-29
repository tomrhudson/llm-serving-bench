# Qwen3.8-Flash-Next-NVFP4 serving baseline

Date: 2026-08-29

Status: **PASS with an operational concurrency recommendation of 8**

> Serving recipe: [Qwen3.8 Flash Next DGX Spark recipe](https://github.com/tomrhudson/qwen38-flash-next-dgx-spark-recipe/tree/main).

## Configuration

- Model: `Qwen3.8-Flash-Next-NVFP4`
- Serving topology: two DGX Sparks, tensor parallelism 2
- Load generator: separate host, direct OpenAI-compatible endpoint
- Context length: `262144`
- Static memory fraction: `0.78`
- Maximum Mamba cache size: `40`
- Chunked prefill size: `2048`
- Configured maximum running requests: `16`
- Allocated KV capacity: `831552` tokens and `10.112` GB per rank

The standard suite ran for 43 minutes and 23 seconds. Including the corrected
canary-only validation, it issued 519 measured requests with zero transport or
serving errors.

## Decode concurrency

Each request used approximately 256 input tokens and a forced 512-token
completion. Throughput is aggregate output tokens per second.

| Concurrency | Output tok/s | Speedup vs c1 | Parallel efficiency | TTFT p95 | E2E p95 |
|---:|---:|---:|---:|---:|---:|
| 1 | 38.43 | 1.00x | 100% | 0.41s | 14.81s |
| 2 | 68.64 | 1.79x | 89% | 0.82s | 15.74s |
| 4 | 151.70 | 3.95x | 99% | 1.28s | 15.68s |
| 8 | **215.06** | **5.60x** | 70% | 1.58s | 20.02s |
| 12 | 153.55 | 4.00x | 33% | 29.90s | 58.02s |
| 16 | 184.47 | 4.80x | 30% | 30.48s | 49.99s |

Concurrency 8 was the throughput optimum. Live SGLang metrics at concurrency
12 showed 8 running requests and 4 queued. Higher offered concurrency therefore
measured admission queueing rather than additional parallel model execution.

## Prefill and context

| Workload | Input tok/s | TTFT p95 | E2E p95 | Result |
|---|---:|---:|---:|---|
| 4K unique, c1 | 1,015.76 | 2.55s | 4.55s | Pass |
| 32K unique, c1 | 1,551.13 | 19.36s | 21.24s | Pass |
| 128K unique, c1 | 1,808.72 | 83.49s | 85.58s | Pass |
| 240K passkey, c1 | 409.67 | 598.56s | 600.04s | **1/1 correct** |

The 262K allocation is functional, but near-window prefill is a batch workload,
not an interactive one: the 240K request needed almost ten minutes to emit its
first token.

## Prefix-cache effectiveness

Four concurrent requests used approximately 32K input tokens and 128 output
tokens each.

| Prefix mode | Output tok/s | TTFT p95 | E2E p95 |
|---|---:|---:|---:|
| Unique | 8.15 | 56.03s | 62.80s |
| Shared, cold | 21.44 | 18.99s | 23.87s |
| Shared, warm | **77.12** | **0.78s** | **6.56s** |

Repeated long prefixes are the largest practical latency opportunity in this
configuration. The warm shared prefix reduced TTFT p95 by about 72 times versus
the unique-prefix case.

## Quality validation

- 240K passkey retrieval: 1/1 correct.
- Corrected serial deterministic canaries: 4/4 correct.
- Corrected concurrency-8 deterministic canaries: 8/8 correct.

The first standard run allotted only 32 completion tokens to each canary. This
reasoning model consumed that budget before emitting final content, producing an
invalid 0/12 harness result. The canary budget was corrected to 128 tokens and
the 12 checks were rerun; all passed. This was a benchmark defect, not evidence
of a model-quality change.

## Sustained load

The 20-minute concurrency-8 soak completed 374 requests and 191,488 output
tokens with zero failures or retractions.

| Metric | Result |
|---|---:|
| Aggregate output throughput | 157.61 tok/s |
| TTFT p50 / p95 | 0.93s / 1.64s |
| E2E p50 / p95 | 26.00s / 37.76s |
| Per-request decode p50 | 20.51 tok/s |
| Request throughput | 0.308 req/s |

## Operational recommendation

Use **8 as the normal client concurrency target**. Keep the server admission
limit at 16 only if accepting queued bursts is desirable; it does not create 16
simultaneously executing requests with the current Mamba-state allocation.

The postflight was healthy on both ranks: both containers remained running with
zero restarts, the endpoint reported the exact model, SGLang showed zero running
or queued requests and zero retractions, and host memory available was 20-21 GiB.

The harness is reusable for other models. Preserve the same hardware, prompts,
token lengths, sampling settings, endpoint path, and concurrency sweep for fair
A/B comparisons; reduce the 128K and 240K scenarios for models with smaller
native context windows.

## Method notes

- Streaming TTFT is measured at the first content or reasoning token.
- Chunk intervals approximate inter-token latency because a streaming chunk can
  contain more than one token.
- The server cache-flush endpoint returned a successful non-JSON response. The
  original runner incorrectly labeled that as unavailable after the POST; the
  client now treats any successful HTTP response as a successful flush.
- Raw JSON was retained privately but was not published because it
  contains generated reasoning traces. This report contains no endpoint URL,
  SSH target, username, credential, or internal address.
