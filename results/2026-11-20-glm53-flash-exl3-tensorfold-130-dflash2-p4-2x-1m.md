# GLM-5.3 Flash EXL3 4 bpw: TensorFold 1.3.0 with DFlash2, P4, two Sparks, 1M

Date: 2026-11-20

Status: **COMPLETE.** The standard serving suite completed with zero request errors, all 13 deterministic checks passed, the 240K passkey was correct, and the 20-minute c8 soak completed. Tool evaluation was not run for this exact runtime stack.

## Configuration and provenance

- Hardware: two NVIDIA DGX Sparks (GB10, 128 GB unified memory each), one rank per Spark, tensor parallel 2 over the direct ConnectX-7 links.
- Checkpoint: [`Mia-AiLab/GLM-5.3-Flash-EXL3-4bpw-TensorFold` @ `76c0b5173166`](https://huggingface.co/Mia-AiLab/GLM-5.3-Flash-EXL3-4bpw-TensorFold/tree/76c0b5173166d2795dd48860f45d8224817f894c), approximately 164 GiB on disk, Apache-2.0.
- Drafter: [`incoai/GLM-5.3-Flash-DFlash2` @ `bf582e4eacc1`](https://huggingface.co/incoai/GLM-5.3-Flash-DFlash2/tree/bf582e4eacc1810f76656d1811693ff6c6737d2a), CC BY-NC-ND 4.0. It was used only for personal, non-commercial benchmarking; commercial deployment requires removing or separately licensing it.
- Recipe: [`MiaAI-Lab/GLM-5.3-Flash-DGX-Sparks-1104` @ `a691916c16b6`](https://github.com/MiaAI-Lab/GLM-5.3-Flash-DGX-Sparks-1104/tree/a691916c16b6287ebb79ef8ee37ea182b5240a29), Apache-2.0.
- Runtime: TensorFold 1.3.0 from `81de26f64967` plus the recipe's 16-patch stack. The locally built image was `sha256:a7e44c42b478e861b4b99438a0493d210adc75449114fe185036d6287656adcb`, with recipe patch fingerprint `748a4e4e3e89`.
- Serving: `PARALLEL=4`, 1,048,576-token request window, FP8 paged KV, q8 dense layers, q8 LM head, DFlash2 4-bit drafts, 5 GiB prompt cache, 6.5 GiB memory reserve, and thinking disabled by default. The engine exposed 5,836 KV pages (2,988,032 shared tokens), enough for two simultaneous 1M-token requests rather than four.
- Fabric: RoCE v2 on both direct-link HCAs with GID index 3. NCCL reported eight `NET/IB` connections; TensorFold's RoCE all-gather path was active.
- Vision: image inputs were advertised, but the optional video library was not built; `video_url` inputs were therefore unavailable and were not tested.
- Load generator: a separate macOS host on the trusted local network. Both Sparks were sampled over passwordless SSH every five seconds.
- Benchmark harness: `llm-serving-bench` commit `bffcecad3a17386440ba45ff9df84243e09ec13e`, suite `qwen-native-standard-v1`, with thinking disabled per request.

The suite ran for 44 minutes and 53 seconds. It issued 291 measured requests, 1,202,343 prompt tokens, and 133,479 completion tokens with zero request failures.

## Decode concurrency

Each request used approximately 256 input tokens and a forced 512-token completion. Throughput is aggregate output tokens per second. With four active streams, c8-c16 primarily measure queue behavior.

| Concurrency | Output tok/s | Speedup vs c1 | Efficiency | TTFT p95 | E2E p95 |
|---:|---:|---:|---:|---:|---:|
| 1 | 41.85 | 1.00x | 100% | **0.51s** | 13.68s |
| 2 | 54.70 | 1.31x | 65% | 0.86s | 19.84s |
| 4 | 71.69 | 1.71x | 43% | 1.63s | 31.69s |
| 8 | **77.02** | 1.84x | 23% | 30.08s | 58.40s |
| 12 | 71.98 | 1.72x | 14% | 60.51s | 90.64s |
| 16 | 73.07 | 1.75x | 11% | 94.00s | 124.07s |

Concurrency 8 produced the highest aggregate decode result, but its 30-second TTFT tail is not interactive. Use c1 for latency-sensitive work and c4 for throughput-oriented batches; offering more than four simultaneous requests adds queueing without a useful throughput gain.

The recipe README cites about 79-81 tok/s at c4 for its lab harness. This run measured 71.69 tok/s, about 9-12% lower. The result is also 9.3% below the November 8 TensorFold 1.1.9 c4 result of 79.04 tok/s. That comparison is not a controlled engine-only A/B: the earlier run used 16 streams, a bf16 head, a 12 GiB reserve, and no effective 5 GiB prompt cache, while this run used P4, a q8 head, and a 6.5 GiB reserve.

## Prefill, long context, and prefix reuse

| Workload | Input tok/s | TTFT p95 | E2E p95 | Result |
|---|---:|---:|---:|---|
| 4K unique, c1 | 772.71 | 3.63s | 5.42s | Pass |
| 32K unique, c1 | 1,170.32 | 26.18s | 28.08s | Pass |
| 128K unique, c1 | 1,226.52 | 105.73s | 107.49s | Pass |
| 240K passkey, c1 | **1,226.54** | **199.29s** | 200.38s | **1/1 correct** |

The 4K-128K prefill results were 14-26% slower than the November 8 TensorFold 1.1.9 run. The 240K request moved in the opposite direction: TTFT fell from 391.26 seconds to 199.29 seconds while remaining correct. Because serving limits, head quantization, memory reserve, cache policy, and runtime all changed, the long-context gain cannot be assigned to one patch or setting.

Four concurrent requests then used approximately 32K input tokens and 128 output tokens each:

| Prefix mode | Input tok/s | Output tok/s | TTFT p95 | E2E p95 |
|---|---:|---:|---:|---:|
| Unique | 1,103.98 | 4.31 | 112.26s | 116.72s |
| Shared, first pass | 3,819.40 | 14.87 | 27.60s | 34.29s |
| Shared, warm | **15,362.78** | **59.83** | **1.84s** | **8.50s** |

The 5 GiB prompt cache was effective for the repeated shared prefix. TensorFold did not expose a cache-flush endpoint, so the labels do not prove a hard-reset cache state; the unique prompts remained scenario-specific and the shared pair intentionally reused the same prefix.

## Quality and sustained load

- 240K passkey retrieval: **1/1 correct**.
- Serial deterministic canaries: **4/4 correct**.
- Concurrency-8 deterministic canaries: **8/8 correct**.
- Total deterministic checks: **13/13**.
- Twenty-minute c8 soak: 158 completed requests, zero errors, **65.01 output tok/s**, 37.75s TTFT p95, and 70.30s E2E p95.

During the soak the health endpoint consistently showed four active and four waiting requests, as expected for P4. Both rank containers completed with zero restarts and no OOM flag. Postflight found no fatal, OOM, Xid, segfault, panic, memory-guard stop, or rank-exit log match.

## Memory and host telemetry

The harness collected 538 five-second samples from each Spark. Both retained the 2,200 MHz GPU clock cap.

| Rank | Lowest MemAvailable | Peak host memory used | Peak swap used | Peak GPU power | Peak temperature | Peak GPU utilization |
|---|---:|---:|---:|---:|---:|---:|
| Rank 0 | 5.79 GiB | 117.40 GiB | 0.001 GiB | 61.52 W | 78°C | 96% |
| Rank 1 | 7.10 GiB | 116.08 GiB | 0.065 GiB | 61.22 W | 78°C | 96% |

The recipe's guard would stop both ranks below 2.5 GiB held for four seconds; neither node approached that floor. After the benchmark drained, the endpoint was healthy and idle, both containers remained running, and temperatures returned to 49-51°C.

## Recommendation

This is a viable long-context P4 lane on two Sparks, but it is not a replacement recommendation for the selected Qwen serving lane. Use GLM at c1 for interactive requests or c4 for bounded batch work. Its strongest results are the correct 240K retrieval and effective warm-prefix cache; its weaker results are modest decode throughput and slower 4K-128K cold prefill than the prior GLM recipe.

Do not route Hermes or other consequential tool automation to this exact stack based on serving checks alone. Tool evaluation was not run here, and the November 8 run of the same checkpoint and drafter on TensorFold 1.1.9 failed the TC-51 safety gate in all three trials. That older result does not prove this runtime fails, but it remains a relevant acceptance gate. DFlash2's non-commercial license is also a deployment constraint.

## Evidence boundary

- This run measures the exact checkpoint, drafter, runtime, recipe, quantization, P4 topology, and cache policy listed above; comparisons to other runs are operational rather than controlled model-only A/Bs.
- No tool-use or vision-quality suite was run. Image inputs were not benchmarked, and video inputs were unavailable.
- Cache reset was unavailable; shared-prefix labels do not prove a fully reset server cache.
- The text-only canaries are narrow serving-regression checks, not broad model-quality or safety certification.
- Raw requests, generated text, endpoint details, SSH targets, usernames, and host identifiers remain private.
