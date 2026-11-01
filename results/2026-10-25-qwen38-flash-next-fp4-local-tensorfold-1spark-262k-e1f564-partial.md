# Qwen3.8-Flash-Next FP4-Local on TensorFold, one Spark, recipe e1f564 (partial rerun), thinking off

Date: 2026-10-25

Status: **PARTIAL. The serving suite ran through the canaries: 132/132 requests before the soak and 12/12 canaries. The 20-minute soak is invalid, and tool-eval and the long-context suite were not measured.** About two minutes into the soak, the load generator's SSH port forward dropped. Every later soak request failed locally with "connection refused" before reaching the server. The server stayed healthy throughout: its own `/health` returned 200, as checked from the serving side every 15 seconds. The runner then stopped before tool-eval, as designed. These numbers are not a new baseline and are not added to the catalog. The published single-Spark baseline is still [the 2026-10-18 run](2026-10-18-qwen38-flash-next-fp4-local-tensorfold-1spark-262k.md).

Serving recipe: [MiaAI-Lab Qwen3.8 Flash Next Single-DGX-Spark TensorFold](https://github.com/MiaAI-Lab/Qwen3.8-Flash-Next-Single-DGX-Spark-TensorFold/tree/e1f564eb915bb5272474b6c1c527aec3b9ed3de6), commit `e1f564eb915bb5272474b6c1c527aec3b9ed3de6`. The 2026-10-18 baseline used `656879fd7527`.

## What changed in the recipe

Recipe `e1f564` turns three new TensorFold scheduler defaults on: `TF_FLASHNEXT_ADMIT_RECLAIM=1`, `TF_FLASHNEXT_SUPERSEDE=1`, and `TF_FLASHNEXT_MEDIA_REUSE=1`. The other settings are unchanged from the baseline: TensorFold `db281878ddb8`, 5 parallel streams, a 262,144-token context, FP8 KV, MTP drafts, and vision on. The local image's patch hash is `3d3319126c39`; the baseline's was `c0a2df4c680d`.

## Configuration

- Hardware: one NVIDIA DGX Spark (GB10, 128GB unified memory), dedicated to this server.
- Checkpoint: `nvidia/Qwen3.8-Flash-Next-FP4-Local`, revision `b9ce18a6887e18c089fdea8509a33e63429a3300`. It was re-verified against the Hub before the run: 33 files, 102,262,310,289 bytes, 0 mismatches.
- Runtime: built locally with the recipe's Dockerfile and `PULL=0`, with the Zig toolchain from ziglang.org. No API key.
- Deviations from the recipe defaults: `PULL=0`, `HOST=127.0.0.1`, and port 8891. The endpoint was reached through an SSH port forward from a separate macOS load generator, as in the baseline.
- Suite: the standard suite without the 240K passkey (`qwen38-fn-1x-suiteA-standard-minus-needle-off`), with thinking disabled per request.
- The host monitor was replaced by a 5-second logger on the serving host (461 samples).

## Decode concurrency (vs the 2026-10-18 baseline)

| Concurrency | Output tok/s | 2026-10-18 | Change | TTFT p95 | E2E p95 |
|---:|---:|---:|---:|---:|---:|
| 1 | 33.93 | 34.29 | -1.0% | 0.39s | 23.87s |
| 2 | 58.17 | 57.62 | +1.0% | 0.66s | 28.47s |
| 4 | 74.80 | 75.71 | -1.2% | 0.46s | 40.50s |
| 8 | 89.44 | 89.30 | +0.2% | 19.39s | 65.21s |
| 12 | 98.25 | 100.43 | -2.2% | 44.07s | 74.33s |
| 16 | 94.76 | 95.69 | -1.0% | 62.56s | 104.10s |

Per-request decode (p50) was 42.11 tok/s at c1, 25.61 at c8, and 25.68 at c16. The baseline's figures were 42.67, 25.97, and 26.27. Every point is within about 2% of the baseline, which is inside normal run-to-run variation. The new scheduler defaults did not change text-only decode throughput.

## Prefill and prefix reuse (vs the 2026-10-18 baseline)

| Workload | Input tok/s | 2026-10-18 | TTFT p95 | 2026-10-18 | Prompt tokens / TTFT (median) |
|---|---:|---:|---:|---:|---:|
| prefill-4k-c1 | 1,202.16 | 1,176.04 | 1.84s | 1.95s | 2,222.8 |
| prefill-32k-c1 | 1,993.09 | 1,962.37 | 14.69s | 15.03s | 2,230.0 |
| prefill-128k-c1 | 1,966.23 | 1,956.29 | 64.69s | 65.10s | 2,027.9 |
| prefix-unique-32k-c4 | 2,047.75 | 2,028.42 | 56.60s | 57.12s | — |
| prefix-cold-32k-c4 | 2,022.21 | 2,036.38 | 56.96s | 57.13s | — |
| prefix-warm-32k-c4 | 22,291.89 | 20,929.53 | 0.87s | 1.27s | — |

Prefill was 1-3% faster, and warm-prefix TTFT p95 improved from 1.27s to 0.87s.

## Quality, soak, and tool use

- Serial deterministic canaries: 4/4. Concurrency-8 deterministic canaries: 8/8.
- 240K passkey and 4x60K long context: not measured.
- Twenty-minute c8 soak: **invalid, not measured.** 36 requests completed before the port forward dropped, and the 15,811,126 failures after that never reached the server.
- Tool-eval (three trials) and the safety gate: not measured.

## Memory

- Server GPU memory peaked at 85,905 MiB (about 83.9 GiB). The baseline peaked at about 82.7 GiB.
- The lowest `MemAvailable` was 27.8 GiB. Swap use stayed flat at 1,780 MiB, the level it was at before the server started.

## Next step

To complete this rerun, the soak, the three-trial tool-eval, and the long-context suite need another window of about 1h40m. The port forward should restart itself, and the runner should stop as soon as the load generator can no longer reach the endpoint.
