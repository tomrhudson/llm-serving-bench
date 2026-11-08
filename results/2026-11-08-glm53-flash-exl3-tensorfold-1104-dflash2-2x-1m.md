# GLM-5.3 Flash EXL3 4 bpw: TensorFold 1.1.9 with DFlash2, two Sparks, 1M

Date: 2026-11-08

Status: **COMPLETE.** The standard serving suite completed with zero request errors, all 13 deterministic checks passed, the 240K passkey was correct, and the 20-minute c8 soak completed. The three-trial tool evaluation is complete but its safety gate failed; see the linked tool report.

Tool-use report: [three-trial `tool-eval-bench` result](2026-11-08-glm53-flash-exl3-tensorfold-1104-dflash2-2x-1m-tool-eval.md).

## Configuration and provenance

- Hardware: two NVIDIA DGX Sparks (GB10, 128 GB unified memory each), tensor parallel 2 over the direct RoCE link.
- Checkpoint: [`Mia-AiLab/GLM-5.3-Flash-EXL3-4bpw-TensorFold` @ `76c0b5173166`](https://huggingface.co/Mia-AiLab/GLM-5.3-Flash-EXL3-4bpw-TensorFold/tree/76c0b5173166d2795dd48860f45d8224817f894c), 175.72 GB, Apache-2.0.
- Drafter: [`incoai/GLM-5.3-Flash-DFlash2` @ `bf582e4eacc1`](https://huggingface.co/incoai/GLM-5.3-Flash-DFlash2/tree/bf582e4eacc1810f76656d1811693ff6c6737d2a), CC BY-NC-ND 4.0. It was used only for personal, non-commercial benchmarking; commercial deployment requires removing or separately licensing it.
- Recipe: [`MiaAI-Lab/GLM-5.3-Flash-DGX-Sparks-1104` @ `13f2464ee84a`](https://github.com/MiaAI-Lab/GLM-5.3-Flash-DGX-Sparks-1104/tree/13f2464ee84ab2b5dabf0bb264d1144b02cf5fb7), Apache-2.0.
- Runtime: TensorFold 1.1.9 from `f350cd3e` plus the recipe's 110 patches; image fingerprint `8734689e7a73`.
- Serving: 1,048,576-token context, 16 streams, FP8 KV, q8 dense layers, bf16 head, DFlash2 drafts, 12 GiB memory reserve. Serving tests disabled thinking per request; tool evaluation used the server default with thinking enabled.
- Harness: repository commit `e04b5dcc`; suite `qwen-native-standard-v1`; tool protocol `tool-eval-standard-v1-b60e2f0`.

The Hugging Face snapshots were exposed to Docker through same-filesystem hard-linked physical views because the original snapshot symlinks resolve outside a snapshot-only bind mount. File contents and pinned revisions were unchanged.

## Serving results

| Concurrency | Output tok/s | TTFT p95 |
|---:|---:|---:|
| 1 | 42.67 | 0.37s |
| 2 | 58.01 | 0.72s |
| 4 | 79.04 | 1.19s |
| 8 | 102.96 | 2.75s |
| 12 | 114.57 | 4.06s |
| 16 | 121.04 | 5.23s |

| Workload | Input tok/s | TTFT p95 |
|---|---:|---:|
| 4K prefill | 902.98 | 2.65s |
| 32K prefill | 1,569.79 | 19.09s |
| 128K prefill | 1,665.97 | 77.03s |
| 240K passkey | 622.77 | 391.26s |

- Prefix reuse: no effective reuse was available at this memory setting; unique, cold shared, and warm shared 32K c4 TTFT p95 were 83.66s, 84.47s, and 84.94s.
- Deterministic checks: **13/13** (serial 4/4, concurrent 8/8, 240K passkey 1/1).
- Twenty-minute c8 soak: 149 requests, zero errors, **62.29 output tok/s**, 38.12s TTFT p95.

## Recommendation

Do not replace the selected Qwen3.8 Flash Next lane with this configuration. It is stable and its full 1M window is functional, but decode, sustained-load, and long-context latency are materially worse on the same two-Spark topology. The 240K request took 391 seconds to first token, and the DFlash2 license prevents commercial use without a different drafter arrangement.

The tool result is useful but does not reverse that operational recommendation: the run is complete and deterministic, yet the safety gate failed consistently. This is a serving-stack result, not a general model-quality or safety claim.

## Evidence boundary

- Raw requests, generated text, internal endpoints, host identifiers, and telemetry remain private.
- Cache flush was unavailable; shared-prefix labels do not prove a fully reset server cache.
- The text-only suite did not test vision.
- Comparison with other published runs is operational rather than a controlled model-only A/B because model, runtime, quantization, and recipe differ.
