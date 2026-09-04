# Qwen3.8-Flash-Next-NVFP4 MiaAI vLLM two-Spark 2200 MHz baseline

Date: 2026-09-03

Status: **PASS; retain the 2200 MHz GPU clock cap and use concurrency 8 for
short-context interactive and agentic workloads**

> Serving recipe: [MiaAI-Lab Qwen3.8 Flash Next Dual DGX Sparks](https://github.com/MiaAI-Lab/Qwen3.8-Flash-Next-Dual-DGX-Sparks/tree/169fbad266f2791335a3102f0d3d625e7c295563),
> tested at commit `169fbad266f2791335a3102f0d3d625e7c295563` with
> `nvidia-smi -i 0 -lgc 0,2200` applied to both ranks.

## Configuration

- Model: `RadixArk/Qwen3.8-Flash-Next-NVFP4`, served as `qwen3.8-flash-next`
- Serving topology: two DGX Sparks, tensor parallelism 2 and expert parallelism enabled
- Runtime: vLLM `0.1.dev20073+g8e685d198`, MTP speculative decoding with 3 draft tokens
- Runtime image: `vllm/vllm-openai:qwen38-flash-next`
- Image digest: `sha256:fc120ece0a388cc0aa1caad4a9f1cd92113484ab7ec2fd0efadd62585be05bf8`
- Configured context: `1000000` tokens using YaRN factor `4.0` over the native 262,144-token window
- GPU memory utilization: `0.835`; bf16 KV cache (`auto`)
- Maximum sequences: `8`; maximum batched tokens: `8192`
- GPU graphics-clock range: `0,2200` MHz on both ranks; measured maximum 2,184 MHz
- Load generator: separate host, direct OpenAI-compatible endpoint
- Benchmark harness commit: `c7acb983bd4e519de929db3fcf26b764759f402d`

The standard suite ran for 32 minutes and 5 seconds. It completed 610 measured
requests, 1,559,083 prompt tokens, and 297,429 completion tokens with zero
request failures. The 240K retrieval and deterministic canaries passed 13/13.

The comparison below uses the separately measured
[stock-clock baseline](2026-08-31-qwen38-flash-next-vllm-mia-yarn-1m.md).
Recipe, model, image, topology, endpoint path, suite, and benchmark commit were
unchanged. Because the two runs occurred on different days rather than as an
interleaved A/B test, small differences should be treated as run-to-run
variation rather than attributed solely to the clock cap.

## Decode concurrency

Each request used approximately 256 input tokens and a forced 512-token
completion. Throughput is aggregate output tokens per second.

| Concurrency | Stock tok/s | 2200 MHz tok/s | Change | 2200 MHz TTFT p95 |
|---:|---:|---:|---:|---:|
| 1 | 48.93 | 47.51 | -2.91% | 0.36s |
| 2 | 83.20 | 81.83 | -1.64% | 0.83s |
| 4 | 134.62 | 135.45 | +0.62% | 1.25s |
| 8 | 206.78 | **213.72** | **+3.36%** | **1.18s** |
| 12 | 209.12 | 210.19 | +0.51% | 19.07s |
| 16 | 208.17 | 210.03 | +0.89% | 20.76s |

The cap did not reduce practical concurrent decode. Concurrency 8 became the
numerical throughput peak while retaining the same interactive TTFT as stock.
Concurrency 12-16 still adds approximately 18-20 seconds of queueing and remains
unsuitable for latency-sensitive traffic.

## Prefill and context

| Workload | Stock input tok/s | 2200 MHz input tok/s | Change | 2200 MHz TTFT p95 | Result |
|---|---:|---:|---:|---:|---|
| 4K unique, c1 | 1,312.80 | 1,251.71 | -4.65% | 1.96s | Pass |
| 32K unique, c1 | 2,399.48 | 2,361.85 | -1.57% | 12.64s | Pass |
| 128K unique, c1 | 2,380.23 | 2,350.87 | -1.23% | 54.38s | Pass |
| 240K passkey, c1 | 2,069.12 | 2,146.46 | +3.74% | 113.18s | **1/1 correct** |

The 4K probe showed the largest prefill penalty. The 32K and 128K probes were
within 1.6% of stock, while the 240K passkey completed correctly and 3.5%
faster by TTFT. Taken together, this run does not show a material long-context
penalty from the 2200 MHz cap.

## Prefix-cache effectiveness

Four concurrent requests used approximately 32K input tokens and 128 output
tokens each.

| Prefix mode | Input tok/s | Output tok/s | TTFT p95 | E2E p95 |
|---|---:|---:|---:|---:|
| Unique | 2,459.23 | 9.59 | 48.22s | 53.34s |
| Shared, cold | 6,150.01 | 23.92 | 17.20s | 21.38s |
| Shared, warm | **15,822.91** | **61.53** | **4.07s** | **8.31s** |

Warm prefix reuse reduced TTFT p95 by about 12 times versus unique prompts and
4.2 times versus the first shared-prefix pass.

## Sustained load

The 20-minute concurrency-8 soak completed 477 requests and 244,224 output
tokens with zero failures.

| Metric | Stock | 2200 MHz | Change |
|---|---:|---:|---:|
| Aggregate output throughput | 197.71 tok/s | **201.58 tok/s** | **+1.96%** |
| TTFT p95 | 1.19s | 1.31s | +0.13s |
| Per-request decode p50 | 27.42 tok/s | 28.62 tok/s | +4.39% |
| Request throughput | 0.386 req/s | 0.394 req/s | +1.94% |

Live midpoint metrics showed eight running requests, zero waiting requests,
approximately 9.2% KV occupancy, and zero abort/error completions.

## Clock, power, and thermal evidence

Independent five-second sampling across the capped run collected 389 samples
per rank. Power is the GPU rail reported by `nvidia-smi`, not total system or
wall power.

| Rank | Average clock | Maximum clock | Average utilization | Peak GPU temperature | Mean GPU-rail power | Peak GPU-rail power |
|---|---:|---:|---:|---:|---:|---:|
| 0 | 2,183 MHz | 2,184 MHz | 92.3% | **63 C** | 26.57 W | 37.56 W |
| 1 | 2,177 MHz | 2,184 MHz | 92.7% | **66 C** | 26.30 W | 38.73 W |

Both ranks reported zero software and hardware thermal-slowdown time after the
run. The stock-clock benchmark did not preserve comparable thermal telemetry,
so this report does not claim a measured temperature or power delta versus the
stock result.

## Quality and postflight

- Preflight deterministic canaries: 12/12 correct in a separate capped-clock run.
- 240K passkey retrieval in the standard suite: 1/1 correct.
- Standard-suite serial deterministic canaries: 4/4 correct.
- Standard-suite concurrency-8 deterministic canaries: 8/8 correct.
- Both rank containers remained running with zero restarts and no OOM state.
- Final backend metrics showed zero running/waiting requests and zero abort/error completions.

## Operational recommendation

Retain the **2200 MHz cap** for this recipe and continue using **concurrency 8**
for short-context interactive, coding, and agentic traffic. The capped run
provided substantial thermal headroom while preserving practical decode and long-context
performance in this run. The direct `nvidia-smi -lgc` setting does not survive
a reboot or driver reload; reset it immediately with `nvidia-smi -i 0 -rgc`.

## Method notes

- Streaming TTFT is measured at the first content or reasoning token.
- The current vLLM build exposes no cache-reset endpoint recognized by the
  harness. Scenario-specific prompts remain unique, and the shared cold/warm
  pair intentionally reuses the same prefix.
- The model's generation configuration supplied temperature 1.0, top-p 0.95,
  and top-k 20 unless a scenario explicitly overrode sampling.
- Raw JSON and generated reasoning remain private. This report contains no
  endpoint URL, SSH target, username, credential, or internal address.
