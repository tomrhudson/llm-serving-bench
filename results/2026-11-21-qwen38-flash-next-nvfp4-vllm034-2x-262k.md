# Qwen3.8-Flash-Next NVIDIA NVFP4 on vLLM 0.34.0, two Sparks

Date: 2026-11-21

Status: **PASS — 468/468 successful requests and 13/13 serving checks.**

The full suite took 36m 16s. The twenty-minute concurrency-8 soak
sustained **140.54 output tok/s** with
**19.13s** TTFT p95 and **0 request errors**.

## Tested configuration

- Hardware: two NVIDIA DGX Sparks (GB10, 128 GB each), one GPU per node over RoCEv2.
- Checkpoint: [nvidia/Qwen3.8-Flash-Next-NVFP4 @ fc694b54](https://huggingface.co/nvidia/Qwen3.8-Flash-Next-NVFP4/tree/fc694b54fb0174e0913e6adf86691ef85a4ead47). Both nodes loaded the eleven original weight shards offline.
- Weight quantization: NVIDIA ModelOpt NVFP4 with mixed precision for the other layers.
- Runtime: stock vLLM 0.34.0, ARM64, CUDA 13.0.2.
- Runtime image: `docker.io/vllm/vllm-openai@sha256:e40eb98263fa13418dda684147d73e8ec4a2b0e056a37e955dc189cd1b11dd16`.
- Serving configuration: multiprocess distributed executor, TP2 plus expert parallelism, three MTP draft tokens, BF16 KV cache, text-only mode, four sequences, 8,192 max batched tokens, chunked prefill, prefix caching, 0.80 GPU memory utilization, and full decode-only CUDA graphs. Tool and reasoning parsers were `qwen3_coder` and `qwen3`, with auto tool choice enabled.
- Configured context: 262,144 tokens.
- Recipe reference: [MiaAI-Lab two-Spark vLLM topology](https://github.com/MiaAI-Lab/Qwen3.8-Flash-Next-Dual-DGX-Sparks/tree/cd839d0b62f6c737178a0c2037733420e0524ebf). The test used stock vLLM with the settings above.
- Benchmark harness: `562b9ec31c030267c97baa127ecfde70138a8954` and the unmodified `qwen-native-standard-v1` suite, matching the published TensorFold run.
- Load generator: off-cluster macOS client over an SSH forward to the direct OpenAI-compatible endpoint.

## Decode concurrency

Approximately 256 prompt tokens and a forced 512-token completion per request.
Concurrency is offered load. vLLM admitted up to four sequences at a time.

| Concurrency | Output tok/s | Speedup vs c1 | Efficiency | TTFT p95 | E2E p95 |
|:---|---:|---:|---:|---:|---:|
| 1 | 44.35 | 1.00× | 100% | 0.36s | 13.17s |
| 2 | 67.31 | 1.52× | 76% | 0.65s | 16.99s |
| 4 | 103.83 | 2.34× | 59% | 0.81s | 21.69s |
| 8 | 102.92 | 2.32× | 29% | 23.26s | 42.17s |
| 12 | 98.53 | 2.22× | 19% | 43.55s | 64.21s |
| 16 | 101.89 | 2.30× | 14% | 63.01s | 82.51s |

## Prefill, context, and prefix reuse

| Workload | Input tok/s | TTFT p95 | E2E p95 |
|:---|---:|---:|---:|
| Prefill 4K | 1,084.29 | 2.06s | 4.24s |
| Prefill 32K | 2,311.42 | 15.28s | 17.21s |
| Prefill 128K | 2,071.36 | 73.17s | 75.14s |
| 240K passkey | 2,439.80 | 99.43s | 100.75s |
| Unique 32K prefixes, c4 | 1,843.03 | 62.24s | 71.13s |
| Cold shared 32K prefix, c4 | 6,768.00 | 15.17s | 19.37s |
| Warm shared 32K prefix, c4 | 23,079.24 | 1.28s | 5.65s |

## Quality and sustained load

- 240K passkey retrieval: 1/1.
- Serial deterministic canaries: 4/4.
- Concurrency-8 deterministic canaries: 8/8.
- Twenty-minute c8 soak: 335 requests, 0 errors, 140.54 output tok/s, 19.13s TTFT p95, and 34.87s E2E p95.
- Per-request soak decode: 38.66 tok/s at p50 and 41.68 tok/s at p95.

## Host telemetry

Samples span the full suite at a ten-second target interval.

| Node | Samples | Min available RAM | Peak swap used | Peak GPU temperature | Mean GPU power |
|:---|---:|---:|---:|---:|---:|
| Rank 0 | 218 | 12.54 GiB | 4.98 GiB | 65 °C | 27.8 W |
| Rank 1 | 218 | 13.27 GiB | 3.00 GiB | 68 °C | 27.4 W |

## Comparison with the dual-Spark TensorFold baseline

Both runs used the same checkpoint revision, two DGX Sparks, and the same
serving workload. vLLM used native 262K context, BF16 KV, MTP3, and a limit
of four running sequences. The [TensorFold baseline](2026-10-08-qwen38-flash-next-nvfp4-tensorfold-1m.md) used a 1M YaRN
configuration, FP8 KV, MTP and copy drafts, and a limit of sixteen running
sequences.
Its load generator ran on a separate Linux host. The table compares the
two deployed stacks.

| Metric | vLLM 0.34.0 | TensorFold | vLLM change |
|:---|---:|---:|---:|
| Decode c1 (output tok/s) | 44.35 | 83.45 | -46.9% |
| Decode c4 (output tok/s) | 103.83 | 195.56 | -46.9% |
| Decode c8 (output tok/s) | 102.92 | 282.69 | -63.6% |
| Decode c16 (output tok/s) | 101.89 | 417.63 | -75.6% |
| 20-minute c8 soak (output tok/s) | 140.54 | 432.90 | -67.5% |
| c8 soak TTFT p95 (s) | 19.13 | 1.00 | +1812.7% |
| 128K prefill (input tok/s) | 2,071.36 | 2,614.74 | -20.8% |
| 240K passkey TTFT p95 (s) | 99.43 | 98.98 | +0.5% |
| Warm 32K prefix TTFT p95 (s) | 1.28 | 0.33 | +289.1% |

TensorFold sustained **3.08×** as much output in the c8 soak. vLLM reached its
best short-decode throughput at c4. At offered c16 it still processed about
102 output tok/s, while TTFT p95 rose from 0.81s at c4 to 63.01s.

Both configurations retrieved the 240K passkey in about 99s to first token.
The vLLM endpoint counted 245,817 prompt tokens including its chat template.
For the first batch of four requests sharing a 32K prefix, vLLM's TTFT p95
was 15.17s versus TensorFold's 43.64s. TensorFold had lower TTFT p95 on the
warm repeat, 0.33s versus 1.28s.

## Tool-use evaluation

The [three-trial tool evaluation](2026-11-21-qwen38-flash-next-nvfp4-vllm034-2x-262k-tool-eval.md) used the same
vLLM configuration. It graded all 207 attempts, scored 92.0 mean, and failed
the safety gate on TC-51 and TC-58.

## Measurement limits

- The suite's cache-flush endpoint was unavailable. Cold workloads use fresh prompt content, and the shared-prefix pair reuses the same prefix. Cache reset was unverified.
- Both serving suites used the recipe's default thinking behavior. TTFT starts at the first streamed content or reasoning token.
- The 262,144-token window is a configured limit. The longest benchmark workload targeted 245,760 prompt tokens.
- The soak schedules requests for 20 minutes and includes the final drain in throughput. vLLM finished draining at 20m 20s.
- The workload exercised text. Raw results and operational evidence are private.
