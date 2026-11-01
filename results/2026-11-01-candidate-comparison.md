# Candidate comparison against Qwen3.8-Flash-Next

Date: 2026-11-01

Status: **IN PROGRESS — fresh production serving reference complete; pinned tool evaluation running. No candidate measurements yet.**

This campaign uses the existing `llm-serving-bench` serving matrix and the pinned
`tool-eval-standard-v1-b60e2f0` profile. The serving suite is the previously used
thinking-off variant of `qwen-native-standard-v1`: seed 20260829, decode at
concurrency 1/2/4/8/12/16, 4K/32K/128K prefill, prefix reuse, 240K retrieval,
serial/concurrent canaries, and a 20-minute c8 soak. Tool evaluation retains the
existing 15-scenario smoke followed by 69 scenarios across three trials, seed 42,
temperature 0, parallelism 1, eight turns, and 900-second timeout.

The fresh reference uses the same serving request settings as the candidates.
The older published production result used default thinking and is historical
context rather than a controlled comparison to this thinking-off cohort.

| Model | Quant | Spark(s) | Load time | Memory used | Single-stream tok/s | Prefill tok/s | Benchmark scores vs reference | Notes or problems |
|---|---|---|---|---|---|---|---|---|
| Qwen3.8-Flash-Next production reference | NVIDIA NVFP4 | 2x DGX Spark, TP=2 | Not measured yet | Observed host peaks 87.94 / 85.51 GiB (partial telemetry) | 70.25 | 2,801.80 at 128K | 13/13 regression checks; tool profile running | 575/575 requests; c8 soak 185.82 tok/s; cache-reset endpoint unavailable |
| Nanbeige4.3-33B | FP8 | 1x DGX Spark | Pending | Pending | Pending | Pending | Pending | All 17 staged files size-verified; seven weight shards SHA-256 verified |
| Qwen3.8-Flash-Next, ABLIT=0 | FP4-Local QAD | 1x DGX Spark | Pending | Pending | Pending | Pending | Pending | Stock control for the overlay |
| Qwen3.8-Flash-Next, ABLIT=1 | FP4-Local QAD + Keys overlay | Same single Spark | Pending | Pending | Pending | Pending | Pending | Gated access confirmed; terms accepted by operator |
| DeepSeek-V4.1-Flash-1017 | EXL3 EAQ v1, 2.9 bpw | 2x DGX Spark, TP=2 | Pending | Pending | Pending | Pending | Pending | Separate outage window required |

The reference completed in 1,845.43 seconds. Its 20-minute c8 soak completed
442 requests without errors. Prefill in the table uses the existing harness
definition (prompt tokens divided by request wall time, including the short
completion). At 128K, median prompt tokens / TTFT was 2,895.51 tok/s. The two
per-host memory peaks are partial observations: 168/322 and 169/322 host samples
contained usable memory data. Direct API traffic continued through an established
SSH tunnel during the new-connection failures.

## Verified artifacts and boundaries

- [Nanbeige FP8](https://huggingface.co/primitive-ai/Nanbeige4.3-33B-FP8/tree/0140c157bc44507929a742c220865b0870052552): Apache-2.0; 35,548,055,920 bytes in the pinned repository. Its configuration supports 524,288 positions; the planned test uses 262,144.
- [Qwen FP4-Local](https://huggingface.co/nvidia/Qwen3.8-Flash-Next-FP4-Local/tree/b9ce18a6887e18c089fdea8509a33e63429a3300): NVIDIA Open Model Agreement plus upstream Qwen terms. The existing local snapshot contains all 21 indexed weight shards, totaling 102,192,011,716 bytes; a fresh hash check remains pending.
- [Keys overlay](https://huggingface.co/drowzeys/keys-Qwen3.8-Flash-Next-NVFP4-FP4-QAD-house-qsa-L3-47/tree/c44f5b92ee3d307b82aab1c55f4cc4ae1d440344): pinned sidecar is 194,645,112 bytes. Overlay access returned HTTP 200 without downloading the sidecar.
- [DeepSeek quant](https://huggingface.co/Mia-AiLab/DeepSeek-V4.1-Flash-1017-EXL3-EAQ-v1-2.9-bpw/tree/45ee5d0fd106c94a3d77f721e09cbb2f50e5a16b): MIT; repository payload 210,663,291,755 bytes. Required base-model Engram shards total 203,073,077,576 bytes. Prepared rank files and images require additional disk.
- Both systems already have successful 2200 MHz cap services. This campaign has changed no GPU clocks or host configuration.
- All inference listeners remain loopback or fabric only; image pulls are disabled. Production containers will be preserved and restored by starting the worker before the API head, as explicitly approved by the operator.

A controlled overlay capability delta compares ABLIT=1 with ABLIT=0 on the same
checkpoint, runtime, hardware, and settings. Comparing either single-Spark lane
with the two-Spark production service is an operational comparison. Incomplete
tool-eval results remain qualified evidence and cannot be presented as complete
comparative scores.

Raw staging logs, integrity receipts, and run artifacts remain private under
`.bench-runs/20261101-candidate-comparison/` and are not committed.

## Later candidates: not run

MiniMax-M3.1-Flash needs a validated two-Spark serving path before a test is
scheduled. BLACKFOLD requires its own gated access and recipe review. Mistral
Large 4 Mix-256G is 232,947,436,288 bytes of weights and leaves little room for
host memory, caches, and runtime workspace; two-Spark feasibility is unvalidated.

## Recommendation

Pending completed measurements. Keep the production Qwen service as the
reference and recovery target throughout the campaign.
