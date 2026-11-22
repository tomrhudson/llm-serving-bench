# Inkling 2 Mini NVFP4 (vLLM, DSpark7, 1 Spark, 262K)

## Configuration

- Checkpoint [thinkingmachines/Inkling-2-Mini @ b85c3cf](https://huggingface.co/thinkingmachines/Inkling-2-Mini/tree/b85c3cfa615fc413cc9af3379f491b963f3b586a). Apache-2.0.
- Runtime vLLM `v0.1.dev25855+g7cb5dae22` in image `vllm/vllm-openai@sha256:c2dc759f5984f69c1e2418c6af7c26eb756f5ed2a8934c768ae1253645d1449e`. [vLLM's day-zero support notes](https://vllm.ai/blog/2026-11-20-inkling2-mini).
- One NVIDIA DGX Spark, ARM64, TP1, 262,144-token limit, BF16 model dtype, auto KV-cache dtype, and default checkpoint reasoning.
- Inkling reasoning and tool parsers enabled. DSpark configured with seven speculative tokens and probabilistic draft sampling. [vLLM's one-Spark Inkling serving recipe](https://recipes.vllm.ai/thinkingmachines/Inkling-2-Mini).
- Benchmark harness `1e35dc1` and suite `qwen-native-standard-v1`, run from an off-host client over SSH.

## Decode concurrency

| Offered concurrency | Throughput (output tok/s) | TTFT p95 (s) | E2E p95 (s) |
| ---: | ---: | ---: | ---: |
| 1 | 41.59 | 0.28 | 13.93 |
| 2 | 67.66 | 0.61 | 16.89 |
| 4 | 89.73 | 6.86 | 30.21 |
| 8 | 146.43 | 3.13 | 29.89 |
| 12 | 199.83 | 3.38 | 33.01 |
| 16 | 229.47 | 2.85 | 39.21 |

## Context and prefix reuse

| Workload | Throughput (input tok/s) | TTFT p95 (s) |
| --- | ---: | ---: |
| 4K cold | 1117.46 | 3.01 |
| 32K cold | 2363.60 | 12.75 |
| 128K cold | 2007.46 | 63.84 |
| 240K passkey | 1548.23 | 155.99 |
| 32K unique prefix, c4 | 2294.73 | 50.83 |
| 32K cold prefix, c4 | 4456.00 | 23.96 |
| 32K warm prefix, c4 | 20145.53 | 0.71 |

## Regression checks and sustained load

- Serving correctness 10/13. The 240K passkey passed.
- The c8 soak sustained 145.04 output tok/s over 347 requests with 0 errors and 1.21s p95 TTFT.
- The serving suite recorded 0 request errors.
- All 3 missed canaries were string-reversal attempts that reached the 128-token output cap.

## Host telemetry

- 92 of 415 telemetry polls returned samples. The remaining SSH polls failed
  after LAN authentication stopped working. Minimum available RAM in the
  observed samples was 4.94 GiB.
- Peak GPU temperature 70°C and average GPU power 27.6 W.

Some cache resets were unavailable. Cold prompts used distinct content and the warm prefix stage reused the paired prefix.

## Capability results

- [Tool-use evaluation](2026-11-21-inkling-2-mini-nvfp4-vllm-1spark-262k-tool-eval.md).
- [RULER, LongBench v2, and local τ²-Bench](2026-11-21-inkling-2-mini-nvfp4-vllm-1spark-262k-capabilities.md).
- [RULER and LongBench v2 output-cap comparison](2026-11-22-inkling-2-mini-nvfp4-vllm-1spark-262k-context-output-cap-2048.md).

The serving workload exercised text and measured prefill through approximately 240K tokens.
