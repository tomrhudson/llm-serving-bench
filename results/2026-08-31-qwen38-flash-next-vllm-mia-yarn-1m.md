# Qwen3.8-Flash-Next-NVFP4 MiaAI vLLM two-Spark baseline

Date: 2026-08-31

Status: **PASS; use concurrency 8 for short-context interactive and agentic workloads**

> Serving recipe: [MiaAI-Lab Qwen3.8 Flash Next Dual DGX Sparks](https://github.com/MiaAI-Lab/Qwen3.8-Flash-Next-Dual-DGX-Sparks/tree/169fbad266f2791335a3102f0d3d625e7c295563), tested at commit `169fbad266f2791335a3102f0d3d625e7c295563`.

## Configuration

- Model: `RadixArk/Qwen3.8-Flash-Next-NVFP4`, served as `qwen3.8-flash-next`
- Serving topology: two DGX Sparks, tensor parallelism 2 and expert parallelism enabled
- Runtime: vLLM `0.1.dev20073+g8e685d198`, MTP speculative decoding with 3 draft tokens
- Runtime image: `vllm/vllm-openai:qwen38-flash-next`
- Image digest: `sha256:fc120ece0a388cc0aa1caad4a9f1cd92113484ab7ec2fd0efadd62585be05bf8`
- Configured context: `1000000` tokens using YaRN factor `4.0` over the native 262,144-token window
- GPU memory utilization: `0.835`; bf16 KV cache (`auto`)
- Maximum sequences: `8`; maximum batched tokens: `8192`
- Measured KV pool: `33.77 GiB`, `2,427,244` tokens, or 2.43 resident requests at the full configured context
- NVFP4 expert weights with the recipe's runtime FP8 PLE resolver patch; PLE CPU offload disabled
- Load generator: separate host, direct OpenAI-compatible endpoint
- Benchmark harness commit: `c7acb983bd4e519de929db3fcf26b764759f402d`

The standard suite ran for 32 minutes and 18 seconds. It issued 602 measured
requests, 1,550,504 prompt tokens, and 293,344 completion tokens with zero
request failures. The 240K retrieval and deterministic canaries passed 13/13.

## Decode concurrency

Each request used approximately 256 input tokens and a forced 512-token
completion. Throughput is aggregate output tokens per second.

| Concurrency | Output tok/s | Speedup vs c1 | Parallel efficiency | TTFT p95 | E2E p95 |
|---:|---:|---:|---:|---:|---:|
| 1 | 48.93 | 1.00x | 100% | **0.43s** | 11.26s |
| 2 | 83.20 | 1.70x | 85% | 0.87s | 12.71s |
| 4 | 134.62 | 2.75x | 69% | 1.22s | 15.35s |
| 8 | 206.78 | 4.23x | 53% | 1.18s | 21.23s |
| 12 | **209.12** | **4.27x** | 36% | 19.13s | 38.66s |
| 16 | 208.17 | 4.25x | 27% | 20.96s | 40.53s |

Concurrency 12 produced the numerical throughput peak, but it added roughly
18 seconds of queueing while improving throughput by only 1.1% over concurrency
8. Concurrency 8 is therefore the practical limit for this short-prompt workload.

## Prefill and context

| Workload | Input tok/s | TTFT p95 | E2E p95 | Result |
|---|---:|---:|---:|---|
| 4K unique, c1 | 1,312.80 | 1.88s | 3.20s | Pass |
| 32K unique, c1 | 2,399.48 | 12.50s | 14.11s | Pass |
| 128K unique, c1 | 2,380.23 | 53.85s | 55.47s | Pass |
| 240K passkey, c1 | 2,069.12 | 117.30s | 118.80s | **1/1 correct** |

The 240K retrieval was correct and reached its first token in under two minutes.
The configured 1M window uses YaRN beyond the checkpoint's native 262K range;
this suite validates workloads only through 240K and is not evidence of quality
or stability at one million tokens.

## Prefix-cache effectiveness

Four concurrent requests used approximately 32K input tokens and 128 output
tokens each.

| Prefix mode | Input tok/s | Output tok/s | TTFT p95 | E2E p95 |
|---|---:|---:|---:|---:|
| Unique | 2,250.50 | 8.78 | 53.14s | 58.26s |
| Shared, cold | 5,500.37 | 21.39 | 19.48s | 23.93s |
| Shared, warm | **16,808.17** | **65.37** | **4.04s** | **7.82s** |

Warm prefix reuse reduced TTFT p95 by about 13 times versus unique prompts and
about 4.8 times versus the first shared-prefix pass.

## Quality validation

- Preflight canary gate: 12/12 correct.
- 240K passkey retrieval in the standard suite: 1/1 correct.
- Standard-suite serial deterministic canaries: 4/4 correct.
- Standard-suite concurrency-8 deterministic canaries: 8/8 correct.

The preflight gate and the full run both completed without transport or serving
errors. The catalog reports the standard suite's independent 13/13 result.

## Sustained load

The 20-minute concurrency-8 soak completed 469 requests and 240,128 output
tokens with zero failures.

| Metric | Result |
|---|---:|
| Aggregate output throughput | 197.71 tok/s |
| TTFT p50 / p95 | 0.78s / 1.19s |
| E2E p50 / p95 | 19.52s / 27.73s |
| Per-request decode p50 | 27.42 tok/s |
| Request throughput | 0.386 req/s |

Live midpoint telemetry showed eight running requests, zero waiting requests,
about 9.2% KV occupancy, and zero abort/error completions. Both rank containers
remained running with zero restarts and no OOM flag.

## Operational recommendation

Use **concurrency 8** for short-context interactive, coding, and agentic traffic.
Concurrency 12-16 is stable but adds severe TTFT queueing for negligible aggregate
throughput. For very long requests, size concurrency against the measured 2.43M
token KV pool: only about two full 1M-context requests can remain resident even
though the admission limit is eight.

Postflight was healthy on both ranks: zero running or waiting requests, zero
abort/error completions, zero container restarts, no OOM state, and no fatal,
NCCL, traceback, segmentation-fault, or CUDA-OOM matches in either container log.
The protected production route returned the expected model marker from the
direct serving backend with zero retries and zero fallbacks.

## Method notes

- Streaming TTFT is measured at the first content or reasoning token.
- The current vLLM build exposes no cache-reset endpoint recognized by the
  harness. Scenario-specific prompts remain unique, and the shared cold/warm
  pair intentionally reuses the same prefix; cache-flush-unavailable notes are
  preserved in the private raw artifact.
- The model's generation configuration supplied temperature 1.0, top-p 0.95,
  and top-k 20 unless a scenario explicitly overrode sampling.
- Raw JSON remains private because it contains generated reasoning. The public
  report contains no endpoint URL, SSH target, username, credential, or internal
  address.
