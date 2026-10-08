# Qwen3.8-Flash-Next NVIDIA NVFP4 on TensorFold, two Sparks

Date: 2026-10-08

Status: **PASS — 1,152/1,152 requests; 13/13 standard-suite quality checks.**

Use concurrency 8 for interactive service and up to 16 for throughput-heavy work. The 20-minute c8 soak sustained **432.90 output tok/s** with 1.00s TTFT p95 and zero errors. This is the strongest Qwen3.8-Flash-Next serving baseline published in this repository.

Serving recipe: [MiaAI-Lab Qwen3.8 Flash Dual DGX Sparks TensorFold](https://github.com/MiaAI-Lab/Qwen3.8-Flash-Dual-DGX-Sparks-TensorFold/tree/be3ed857ab1055ca47b36134d22691f00f2bb94a), commit `be3ed857ab1055ca47b36134d22691f00f2bb94a`.

## Configuration and reproducibility

- Hardware: two NVIDIA DGX Sparks (GB10), one GPU per rank, connected over RoCEv2.
- Checkpoint: `nvidia/Qwen3.8-Flash-Next-NVFP4`, revision [`fc694b54fb0174e0913e6adf86691ef85a4ead47`](https://huggingface.co/nvidia/Qwen3.8-Flash-Next-NVFP4/tree/fc694b54fb0174e0913e6adf86691ef85a4ead47); served as `Qwen3.8-Flash-Next`.
- Runtime: TensorFold Zig engine from commit `db281878ddb836fd0df510d8771ecb7e0fe47d26`, built with recipe patch set `f3e1300f4f62` and Zig 0.17.0.
- Runtime image: `ghcr.io/miaai-lab/qwen3.8-flash-dual-dgx-sparks-tensorfold@sha256:e188128ddabdc67ac02c05781f5c0c6b348db5f050cac297861d82b7f086e18c`; identical local image ID `sha256:5eb5d4d384773543109baa26783fc6ea38ad619dff330f01672e05c01721cfb0` on both ranks.
- Tensor parallelism 2; MTP and copy drafts enabled; FP8 KV cache; vision frontend enabled but not exercised by this text-only suite.
- Configured context: 1,048,576 tokens with YaRN factor 4 over the native 262,144-token window; maximum parallel requests 16.
- The engine reported a 32.57 GiB sequence-memory pool per rank while retaining a 10 GiB memory reserve.
- Load generator: a separate Linux host using the direct OpenAI-compatible endpoint.
- Benchmark harness commit: `562b9ec31c030267c97baa127ecfde70138a8954`; suite `qwen-native-standard-v1`.
- Recipe source is Apache-2.0. The model is distributed under NVIDIA's model terms and the upstream Qwen license; users remain responsible for those terms.

The standard suite ran for 29 minutes and 23 seconds. It issued 1,152 requests, 2,142,751 prompt tokens, and 574,952 completion tokens with zero request failures.

## Decode concurrency

Approximately 256 prompt tokens and a forced 512-token completion per request. Output throughput is aggregate across concurrent requests.

| Concurrency | Output tok/s | Speedup vs c1 | Efficiency | TTFT p95 | E2E p95 |
|---:|---:|---:|---:|---:|---:|
| 1 | 83.45 | 1.00x | 100% | 0.23s | 6.43s |
| 2 | 129.24 | 1.55x | 77% | 0.43s | 8.55s |
| 4 | 195.56 | 2.34x | 59% | 0.68s | 11.83s |
| 8 | 282.69 | 3.39x | 42% | 1.02s | 15.86s |
| 12 | 362.59 | 4.35x | 36% | 1.44s | 19.02s |
| 16 | **417.63** | **5.00x** | 31% | 2.11s | 22.64s |

Unlike the prior vLLM baselines, throughput continued to scale materially through concurrency 16 without a large admission queue. Concurrency 8 remains the interactive recommendation because it keeps TTFT p95 near one second; concurrency 16 is appropriate when aggregate throughput matters more than per-request decode rate.

## Prefill, context, and prefix reuse

| Workload | Input tok/s | TTFT p95 | E2E p95 |
|---|---:|---:|---:|
| prefill-4k-c1 | 2,010.45 | 1.51s | 2.19s |
| prefill-32k-c1 | 2,673.36 | 11.24s | 12.48s |
| prefill-128k-c1 | 2,614.74 | 48.97s | 50.68s |
| needle-240k-c1 | 2,436.01 | 98.98s | 100.91s |
| prefix-unique-32k-c4 | 2,667.53 | 43.37s | 49.16s |
| prefix-cold-32k-c4 | 2,686.44 | 43.64s | 48.99s |
| prefix-warm-32k-c4 | **33,074.04** | **0.33s** | **3.97s** |

The 240K passkey was correct. Warm 32K prefix reuse reduced TTFT p95 by about 131 times versus the cold shared-prefix run. The configured window is 1,048,576 tokens, but this suite validates retrieval and serving behavior only through approximately 240K tokens; it is not evidence of quality at one million tokens.

## Quality and sustained load

- 240K passkey retrieval: 1/1.
- Serial deterministic canaries: 4/4.
- Concurrency-8 deterministic canaries: 8/8.
- Twenty-minute c8 soak: 1,019 requests, zero errors, **432.90 output tok/s**, 1.00s TTFT p95, and 20.24s E2E p95.
- The soak generated 521,728 completion tokens; per-request decode was 69.63 tok/s at p50 and 83.60 tok/s at p95.

## Comparison with the NVIDIA/vLLM FP8-KV baseline

The closest published comparison uses the same two-Spark hardware and NVIDIA NVFP4 weights. The earlier checkpoint revision has byte-identical safetensor files, but the runtime, draft engine, configured context, and other serving details differ, so this is a serving-system comparison rather than a pure runtime-only A/B.

| Metric | vLLM native 262K | TensorFold 1M YaRN | Change |
|---|---:|---:|---:|
| c1 output tok/s | 47.34 | 83.45 | +76% |
| c8 output tok/s | 198.09 | 282.69 | +43% |
| c16 output tok/s | 207.77 | 417.63 | +101% |
| c8 soak output tok/s | 197.42 | 432.90 | +119% |
| c8 soak TTFT p95 | 1.11s | 1.00s | -10% |
| 240K TTFT p95 | 99.22s | 98.98s | effectively unchanged |
| warm 32K-prefix TTFT p95 | 5.86s | 0.33s | -94% |

TensorFold is the new throughput choice for this model. Keep the vLLM lane available as a rollback and compatibility fallback until application routing and workload-specific tool, vision, and exact-output behavior have been validated against the new served model identifier.

## Validation and method limits

- Both rank containers remained running after the suite with zero restarts and no OOM flag; queues drained to zero.
- Both ranks used the same image ID and recipe patch label. Fatal, traceback, segmentation-fault, CUDA-OOM, and NCCL-failure log scans were clean.
- The endpoint's cache-reset route was unavailable. Scenario-specific prompts remained unique, and the deliberate shared-prefix pair retained its cold/warm semantics, but the other cold labels do not prove a fully reset cache.
- Host telemetry is omitted because the load generator's existing direct SSH monitor credentials were stale. Server health, benchmark timing, request counts, container state, and postflight log evidence were still verified independently.
- The text-only suite does not validate image/video input, tool-call correctness, safety, or broad model quality.
- Streaming TTFT begins at the first content or reasoning token. Thinking remained at the recipe default; `max_tokens` includes reasoning and answer tokens.
- Raw requests, generated reasoning, internal endpoints, SSH targets, usernames, and host identifiers are excluded. Raw JSON and operational evidence remain private.
