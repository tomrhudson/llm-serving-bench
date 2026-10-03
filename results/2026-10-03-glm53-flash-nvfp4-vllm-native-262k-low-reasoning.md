# GLM-5.3 Flash NVFP4 vLLM two-Spark low-reasoning baseline

Date: 2026-10-03

Status: **PERFORMANCE, STABILITY, LONG-CONTEXT, AND 13/13 CANARY PASS; RUNTIME ACCURACY WARNING PRESENT**

> Serving recipe credit: This deployment uses
> [MiaAI-Lab's GLM-5.3 Flash NVFP4 dual-Spark recipe](https://github.com/MiaAI-Lab/GLM-5.3-Flash-NVFP4-Dual-DGX-Spark/tree/aed98a13ca75140d2691cc5c651ea5817d9a3e44).

## Configuration

- Model: `LibertAIDAI/GLM-5.3-Flash-NVFP4`
- Model revision: `aa28e1f54130286c95fee10d0705c74ce8743734`
- Serving topology: two NVIDIA DGX Sparks, tensor parallelism 2 through Ray
- Runtime recipe commit: `aed98a13ca75140d2691cc5c651ea5817d9a3e44`
- Runtime: vLLM in MiaAI-Lab image `mia/glm53-flash-spark:mm-ray-v1`
- Image ID on both nodes:
  `sha256:011a7278cf5662b795962d562d1fa580db5ce4f52f42d2160fb612cea96fd894`
- Published image digest: unavailable; the local image had no repository digest
- Context length: `262144`
- Maximum running sequences: `8`
- Maximum batched tokens: `8192`
- KV cache: FP8, 4 GiB per rank, 615,641 token capacity reported at startup
- Weight path: NVFP4 checkpoint with vLLM's Marlin weight-only fallback on GB10
- Inter-node runtime: NCCL tensor parallelism on the dedicated Spark fabric
- Chat template SHA-256:
  `34d5ee66b12fa6446cdae131c352b8f68cd85369e0e6fda115583805fada3891`
- Load generator: separate host, direct OpenAI-compatible endpoint
- Benchmark mode: `reasoning_effort="low"` on every request
- Benchmark harness commit: `01925a9b24c9592b505ac4a3bad7d48158ab6d55`

The 17-scenario suite ran for 50 minutes and 2 seconds. It issued 275 measured
requests, 1,188,996 prompt tokens, and 126,121 completion tokens with zero
request errors. The 240K passkey retrieval and all 12 deterministic canaries
passed, for a combined result of 13/13.

### Accuracy-warning boundary

Both tensor-parallel ranks emitted the same startup warning:
`w1_weight_scale_2 must match w3_weight_scale_2. Accuracy may be affected.`
The standard canaries passed, but they are small regression checks rather than
a broad model-quality evaluation. This report therefore records the exact
13/13 result without calling the serving combination a clean general-quality
pass. Resolve or explain the scale mismatch before relying on this lane for
quality-sensitive production work.

The fetched chat template did not honor `enable_thinking=false`; it defaults
unspecified requests to maximum reasoning. The benchmark instead used the
template's supported `reasoning_effort="low"` control. Older GLM reports in
this repository used non-thinking requests, so performance comparisons are
not controlled reasoning-mode A/B tests.

## Decode concurrency

Each request used approximately 256 input tokens and a forced 512-token
completion. Throughput is aggregate output tokens per second.

| Concurrency | Output tok/s | Speedup vs c1 | Parallel efficiency | TTFT p95 | E2E p95 |
|---:|---:|---:|---:|---:|---:|
| 1 | 14.20 | 1.00x | 100% | **0.45s** | **36.16s** |
| 2 | 27.40 | 1.93x | 96% | 0.97s | 37.66s |
| 4 | 40.87 | 2.88x | 72% | 6.43s | 52.79s |
| 8 | **65.94** | **4.64x** | 58% | **1.88s** | 63.15s |
| 12 | 63.04 | 4.44x | 37% | 69.96s | 132.23s |
| 16 | 66.18 | 4.66x | 29% | 63.40s | 124.33s |

Concurrency 1 is the interactive posture. Concurrency 8 reached 99.6% of the
sweep's maximum throughput with far better tail latency than the queued c12
and c16 cases. Offering more than eight requests did not materially increase
throughput and raised TTFT p95 above one minute.

## Prefill and context

| Workload | Input tok/s | TTFT p95 | E2E p95 | Result |
|---|---:|---:|---:|---|
| 4K unique, c1 | 560.42 | 2.84s | 7.30s | Pass |
| 32K unique, c1 | 1,096.57 | 28.40s | 32.74s | Pass |
| 128K unique, c1 | 1,252.93 | 100.93s | 105.39s | Pass |
| 240K passkey, c1 | **1,288.72** | **188.82s** | 190.71s | **1/1 correct** |

The passkey result establishes correct retrieval at approximately 240K tokens
inside the configured 262,144-token window. It does not establish quality at
every input length or simultaneous near-window capacity for eight requests.

## Prefix-cache observation

Four concurrent requests used approximately 32K input tokens and up to 128
output tokens each.

| Prefix mode | Input tok/s | Output tok/s | TTFT p95 | E2E p95 |
|---|---:|---:|---:|---:|
| Unique | 1,171.60 | 4.58 | 97.47s | 111.70s |
| Shared, nominally cold | 3,527.22 | 13.73 | 26.40s | 37.27s |
| Shared, warm | **10,198.60** | **39.71** | **2.07s** | **12.89s** |

The endpoint did not expose the harness's cache-flush operation. The shared
first pass is therefore observational rather than a hard-reset cold-cache
measurement. The retained shared prefix reduced TTFT p95 by 92.2% versus that
first pass.

## Quality validation

- 240K passkey retrieval: 1/1 correct.
- Serial deterministic canaries: 4/4 correct.
- Concurrency-8 deterministic canaries: 8/8 correct.
- Combined standard-suite result: 13/13.

These exact checks completed normally with no transport, timeout, or serving
error. They do not negate the runtime weight-scale warning or validate broad
reasoning, coding, tool-use, vision, or safety quality.

## Sustained load

The 20-minute concurrency-8 submission window completed 144 requests and
73,728 output tokens, then drained, with zero failures.

| Metric | Result |
|---|---:|
| Aggregate output throughput | 60.90 tok/s |
| TTFT p95 | 4.22s |
| E2E p95 | 68.35s |
| Requests completed | 144 |

Postflight reported the exact model and revision, zero running and waiting
requests, identical image IDs on both ranks, zero container restarts, and
`OOMKilled=false`. No traceback, fatal, OOM, NCCL, or transport failure was
present. The benchmark lane was then stopped with its retained launcher.

## Operational recommendation

Use concurrency 1 for latency-sensitive interactive work and concurrency 8
for throughput-oriented batches. Do not offer more than eight simultaneous
requests when tail latency matters; c12-c16 added no useful throughput.

The selected TensorFold baseline remains the better default when raw decode
throughput and the 1M request window matter: it measured 51.49 tok/s at c1,
93.53 tok/s at c8, and 84.90 tok/s in soak, versus 14.20, 65.94, and 60.90
tok/s here. This NVFP4 lane produced lower c8 TTFT and passed all 13 standard
checks, but its startup accuracy warning prevents treating those canaries as
broad assurance.

That comparison is not a controlled runtime-only A/B. The model checkpoint,
quantization, runtime, scheduler, reasoning mode, cache design, context limit,
and speculative decoding all differ.

## Harness and method notes

- Model weights were local on both ranks; the run did not depend on NFS.
- Cache flush was unavailable, so cold-prefix claims are intentionally limited.
- Streaming TTFT begins at the first content or reasoning token.
- Raw JSON and generated output remain private because they contain generated
  text and detailed operational timing. Endpoint URLs and SSH targets are not
  published.

```bash
python3 -m unittest discover -s tests -v
python3 scripts/generate_results_summary.py --check
```
