# Candidate comparison against Qwen3.8-Flash-Next

Date: 2026-11-01

Status: **IN PROGRESS — Nanbeige serving matrix finished with one timeout; production restored and direct/Hermes route verified. Qwen A/B and DeepSeek preflight complete; fresh outage approvals pending.**

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
| Qwen3.8-Flash-Next production reference | NVIDIA NVFP4 | 2x DGX Spark, TP=2 | 91.82 s on restoration | Observed host peaks 87.94 / 85.51 GiB (partial telemetry) | 70.25 | 2,801.80 at 128K | 13/13 regression checks; tool mean 87.7 (98.6% complete) | 575/575 requests; c8 soak 185.82 tok/s; cache-reset endpoint unavailable |
| Nanbeige4.3-33B | FP8 | 1x DGX Spark | 357.90 s first startup | 110.67 GiB observed host peak | 6.58 | 334.88 at 128K | 9/12 canaries vs reference 12/12; 240K timed out vs reference pass; tools not run | 244/245 requests; c8 soak 46.82 tok/s; no OOM/restarts/guard trips |
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

The pinned tool profile finished all three trials but graded 204/207 scenario
trials (98.6%). TC-64 (JSON schema compliance) was excluded by the evaluator,
matching the runtime's known structured-output limitation. Mean score was 87.7
(stddev 0.6; 95% interval 87.0–88.0), Pass@3 79.4%, and Pass^3 77.9%.
The protocol safety gate passed. This remains incomplete evidence and must not
be treated as a complete comparative quality score. Serving requests disabled
thinking; tool evaluation retained the server's thinking-on default, as in the
existing combined workflow.

Both production processes kept their original pre-run PIDs and start times;
neither OOMed. Direct health/model identity and an exact routed postflight
canary passed, with the router attributing the request to the existing SSH
backend tunnel. These checks preceded the first authorized production stop for Nanbeige. Both production containers are preserved, with restoration required after the experiment.

## Nanbeige completed measurements

The full serving run took 5,167.25 seconds. Its only request error was the
240K retrieval: `TimeoutError` after 900.60 seconds, without an answer. The
12 remaining accuracy probes were graded, and nine passed. All three failures
were the same string reversal (`SPARK38` → `83SKRAPS`, expected `83KRAPS`);
production Qwen passed all 12 matching canaries and its retrieval probe.
The existing combined runner rejects serving results with request errors, so
its pinned tool evaluation was not started. No substitute quality score was
created.

The c8 soak completed 112/112 requests in 1,224.78 seconds at 46.82 output tok/s.
All 1,033 memory samples were valid: peak host use 110.67 GiB, minimum available
11.02 GiB. No OOM, restart, or memory-guard stop occurred. At 128K, p95 TTFT was
374.93 seconds. Cold/warm 32K prefix p95 TTFT was 54.94 / 0.97 seconds.

After the experiment, the preserved production worker and head were started
in that order. Container IDs and `unless-stopped` policies matched, direct
model/canary checks passed, and an exact Hermes → router → production-backend
canary passed. Restoration timing above is container start to the API listen
log; first healthy observation was 106.11 seconds after recovery began with
15-second polling. These retained-container recovery timings are not a
controlled cold-start comparison with Nanbeige’s first compilation.

Production is configured for a 1,048,576-token window. The current campaign’s
workloads reach 240K; Nanbeige and the new single-Spark Qwen recipe use 262,144.
The single-Spark recipe’s smaller maximum is a deployment tradeoff even if its
benchmark results are favorable. Longer production contexts were not validated
by this campaign.

## Verified artifacts and boundaries

- [Nanbeige FP8](https://huggingface.co/primitive-ai/Nanbeige4.3-33B-FP8/tree/0140c157bc44507929a742c220865b0870052552): Apache-2.0; 35,548,055,920 bytes in the pinned repository. Its configuration supports 524,288 positions; the planned test uses 262,144.
- [Qwen FP4-Local](https://huggingface.co/nvidia/Qwen3.8-Flash-Next-FP4-Local/tree/b9ce18a6887e18c089fdea8509a33e63429a3300): NVIDIA Open Model Agreement plus upstream Qwen terms. All 33 pinned repository files passed fresh hashes on the test Spark, including 21 indexed weight shards totaling 102,192,011,716 bytes.
- [Keys overlay](https://huggingface.co/drowzeys/keys-Qwen3.8-Flash-Next-NVFP4-FP4-QAD-house-qsa-L3-47/tree/c44f5b92ee3d307b82aab1c55f4cc4ae1d440344): pinned sidecar is 194,645,112 bytes. NVIDIA Open Model License plus the separately accepted access agreement. The sidecar downloaded successfully and its SHA-256 matched the pinned metadata.
- [DeepSeek quant](https://huggingface.co/Mia-AiLab/DeepSeek-V4.1-Flash-1017-EXL3-EAQ-v1-2.9-bpw/tree/45ee5d0fd106c94a3d77f721e09cbb2f50e5a16b): MIT; repository payload 210,663,291,755 bytes. Required base-model Engram shards total 203,073,077,576 bytes. Matching retained artifacts are verified on both nodes: all head-side upstream source files and 256 required/present worker files passed fresh hashes. The retained rank-cache fingerprints match the current planner, the template matches, and the kernel kit passed its documented checks. The current recipe image was built, copied, and its ID matched on both nodes. The documented local-copy worker preflight passed. Quant + Engram shards + one rank-0 file total 519,856,832,154 bytes before metadata, kit, and image—more than the recipe’s approximate 505 GB. Existing files also retain an extra rank-1 copy on the head; nothing is deleted.
- Both systems already have successful 2200 MHz cap services. The recipe also documents NFS configuration and optional conversion to a headless host; local-copy mode and current free memory avoid those changes. This campaign has changed no GPU clocks or host configuration.
- All inference listeners remain loopback or fabric only; image pulls are disabled. Production containers will be preserved and restored by starting the worker before the API head, as explicitly approved by the operator.

Both Qwen A/B launch dry runs passed. The separately built overlay view changes exactly 24 expected tensor mappings; all other stock files resolve unchanged. Production remains healthy while the next explicit outage decisions are pending.

A controlled overlay capability delta compares ABLIT=1 with ABLIT=0 on the same
checkpoint, runtime, hardware, and settings. Comparing either single-Spark lane
with the two-Spark production service is an operational comparison. Incomplete
tool-eval results remain qualified evidence and cannot be presented as complete
comparative scores.

Raw staging logs, integrity receipts, and run artifacts remain private under
`.bench-runs/20261101-candidate-comparison/` and are not committed.

## Nanbeige runtime constraint

The cached vLLM stack initializes PyTorch distributed state even with one GPU.
PyTorch's [TCPStore listener](https://github.com/pytorch/pytorch/blob/v2.11.0/torch/csrc/distributed/c10d/TCPStoreLibUvBackend.cpp)
binds wildcard addresses. A host-network launch would violate the operator's
listener rule, so none was attempted. An isolated `--network none` container
with a private Unix-socket API was explicitly approved and completed the unchanged suite. The container has only a loopback interface and no external route; the socket is owner-only (0600) beneath a private directory (0700). The already-approved
Apache-2.0 [Q8_0 GGUF fallback](https://huggingface.co/bartowski/Nanbeige_Nanbeige4.3-33B-GGUF/tree/9beb68421fdf7be095093a6888325fa2c83ddd38)
(35,195,128,960 bytes) loaded in 32.365 seconds and completed preliminary decode cells without errors: c1 6.15, c2 11.99, c4 22.85, c8 41.73, c12 56.33 output tok/s. Its run was deliberately interrupted when FP8 isolation approval arrived. These are partial observations, without a completed suite or tool score; the preferred FP8 format will receive the full protocol.

## Later candidates: not run

MiniMax-M3.1-Flash needs a validated two-Spark serving path before a test is
scheduled. BLACKFOLD requires its own gated access and recipe review. Mistral
Large 4 Mix-256G is 232,947,436,288 bytes of weights and leaves little room for
host memory, caches, and runtime workspace; two-Spark feasibility is unvalidated.

## Recommendation

Nanbeige FP8 does not earn a replacement recommendation from this run: it was slower, failed one retrieval request, and missed the same string-reversal probe three times. Keep production Qwen while the controlled overlay pair and two-node DeepSeek candidate remain unmeasured.
