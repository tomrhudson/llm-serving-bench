# NousResearch Arete-27B on SGLang, one Spark, FP8 KV, 262K

Date: 2026-11-08

Status: **COMPLETE WITH A STABILITY CAVEAT.** The standard serving suite completed with zero request errors, all 13 deterministic checks passed, the 240K passkey was correct, and the 20-minute c8 soak completed. A clean-restart three-trial tool evaluation scored 95.0 and passed its safety gate. The first post-soak tool attempt ended when the SGLang scheduler received SIGTERM; it was not an OOM or GPU fault, and the unchanged retry completed.

Tool-use report: [three-trial `tool-eval-bench` result](2026-11-08-arete-27b-sglang-fp8kv-1spark-262k-tool-eval.md).

## Configuration and provenance

- Hardware: one NVIDIA DGX Spark (GB10, 128 GB unified memory), dedicated to this server.
- Checkpoint: [`NousResearch/Arete-27B` @ `108f0afbdcfa`](https://huggingface.co/NousResearch/Arete-27B/tree/108f0afbdcfaa1ceeda4a635004304dfff6d4da2), 54.74 GB on disk, Apache-2.0. The model card identifies Qwen3.8-27B as the base model.
- Runtime: SGLang image `lmsysorg/sglang@sha256:febfb971c7352570fc445c466ebd6ffc9d896024958e544a60f2137fd85856b1`.
- Serving configuration: 262,144-token context, FP8 E4M3 KV cache, FlashInfer attention, 8,192-token chunked prefill, maximum 10 running requests, Qwen3 reasoning parser, and Qwen3-Coder tool parser.
- Serving tests disabled thinking per request. Tool evaluation used the model's default thinking behavior.
- Harness: suite `qwen-native-standard-v1`; tool protocol `tool-eval-standard-v1-b60e2f0`.

No upstream DGX Spark serving recipe was supplied. This is a local, pinned SGLang configuration and should not be treated as a NousResearch performance recipe.

## Serving results

| Concurrency | Output tok/s | TTFT p95 |
|---:|---:|---:|
| 1 | 4.29 | 0.61s |
| 2 | 8.63 | 0.88s |
| 4 | 16.95 | 1.14s |
| 8 | 32.42 | 2.34s |
| 12 | 32.61 | 130.35s |
| 16 | 32.65 | 130.41s |

Eight concurrent requests are the practical maximum for this configuration. Higher concurrency does not increase aggregate decode and adds approximately two minutes of queueing before first token.

| Workload | Input tok/s | TTFT p95 |
|---|---:|---:|
| 4K prefill | 225.16 | 3.48s |
| 32K prefill | 719.69 | 30.60s |
| 128K prefill | 683.41 | 175.95s |
| 240K passkey | 539.69 | 452.84s |

- Prefix reuse was effective: unique, cold shared, and warm shared 32K c4 TTFT p95 were 114.02s, 30.29s, and 1.49s.
- Deterministic checks: **13/13** (serial 4/4, concurrent 8/8, 240K passkey 1/1).
- Twenty-minute c8 soak: 80 requests, zero errors, **31.28 output tok/s**, 6.84s TTFT p95.

## Tool use

The clean-restart three-trial run scored **95.0 mean**, with Pass@3 and Pass^3 both **91.3%**. Results were identical across trials and the safety gate passed. The weakest categories were autonomous planning and structured output, both 83%. TC-68 failed all three trials because the answer was not valid JSON. TC-57 and TC-60 earned partial credit: the model rejected the injections but reproduced attacker-controlled content, so side-effecting tool use still needs application-level review.

The first tool run immediately after the serving soak is excluded from the score: the scheduler exited on SIGTERM during the capability probe and did not produce a complete standard result. A fresh server passed the same probe and completed all three unchanged trials. This makes the published score valid for the clean retry while retaining a material stability caveat for long-lived service.

## Recommendation

Do not use this configuration as the default interactive lane. It has the strongest complete tool-eval mean published in this repository and a passing safety gate, but it is far slower than the selected Qwen lanes: 4.29 tok/s at c1, 31.28 tok/s during the c8 soak, 176 seconds to first token at 128K, and 453 seconds at 240K. Tool turns were also slow, with a 36.58-second median and individual complex scenarios taking many minutes.

Retain Arete as a quality-oriented, single-user research option after reproducing the post-soak stability behavior. The comparison with Qwen is operational rather than controlled because model, runtime, quantization, and recipe differ.

## Evidence boundary

- Raw requests, generated text, tool payloads, endpoints, host identifiers, and logs remain private.
- The transient scheduler exit is reported as observed; its root cause was not established.
- The text-only suite did not test the checkpoint's multimodal configuration.
- FP8 KV changes the serving stack relative to the BF16 checkpoint and may affect quality.
- The 13 deterministic checks and tool scenarios do not establish broad model quality or safety.
