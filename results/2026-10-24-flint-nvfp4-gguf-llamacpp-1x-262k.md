# Recursive Flint 40B-A2.5B NVFP4 GGUF: llama.cpp b11856, one slot (-np 1), one Spark, 262K

Date: 2026-10-24

Status: **COMPLETE: 320/320 requests across both stages finished with zero errors. Tool-eval COMPLETE (100%): 86.0 mean, Pass^3 75.4%, safety gate PASSED. Quality checks 10/13: the 240K passkey passed, and all three misses are the same reversal canary, which is setup-limited (see below).**

This is the first baseline for `RecursiveSI/flint`, served from RecursiveSI's NVFP4 GGUF with llama.cpp on one DGX Spark. No recipe repository exists, so the server used the model card's `llama-server` command with lab overrides. It ran with the same harness, suite layout and tool-eval protocol as the selected [Qwen3.8-Flash-Next TensorFold baseline](2026-10-08-qwen38-flash-next-nvfp4-tensorfold-1m.md).

Single-stream decode was **81.73 output tok/s** (per-request p50 85.72 tok/s) with a 0.32s TTFT p95. **The server ran with `-np 1`, the model card's single slot, so concurrent requests queue instead of batching.** Aggregate decode stayed at about 82-83 tok/s from c1 to c16 while TTFT p95 grew to 93.22s at c16. The c2-c16 rows measure queueing, not batching, and do not show what llama.cpp could do with more slots. Prefill ran at about 1.5-2.1K input tok/s (128K TTFT p95 89.89s). The 240K passkey passed with a 220.19s TTFT.

Tool-use report: [three-trial `tool-eval-bench` result](2026-10-24-flint-nvfp4-gguf-llamacpp-1x-262k-tool-eval.md).

## Configuration and reproducibility

- Hardware: one NVIDIA DGX Spark (GB10, 128GB unified memory), dedicated to this server.
- Checkpoint: `RecursiveSI/flint-nvfp4-gguf`, revision [`6ec43e19b565fc8d560e2d04985d7724f20673bf`](https://huggingface.co/RecursiveSI/flint-nvfp4-gguf/tree/6ec43e19b565fc8d560e2d04985d7724f20673bf) (7 files, 22.86 GB, Apache-2.0, not gated). Every file was checked by size and LFS sha256 against the Hub at the pinned revision. The GGUF is 22,863,084,160 bytes, sha256 `97cc8009ff9b132d5cf3c488e6767962bb5a5dc158a90ed661bbbddf876b8bde`. Served as `flint`. Base model: [RecursiveSI/flint](https://huggingface.co/RecursiveSI/flint) (Apache-2.0), not downloaded.
- Architecture as reported by the GGUF: 49 layers (14 full attention, 35 sliding-window with a 513-token window), 4 KV heads of 128 dimensions, 256 experts with 6 active plus 2 shared, 262,144-token trained context. The chat template has no `enable_thinking` switch.
- Runtime: llama.cpp `b11856` ([`3642238cc120`](https://github.com/ggml-org/llama.cpp/tree/3642238cc12050c8ab70afdf4b3121ea365c7579), MIT), built locally from `.devops/cuda.Dockerfile` with CUDA 13.2 and CUDA architecture 121 (built as `121a`). Nothing was pulled from a third-party registry and nothing was published. Local image id `sha256:436f75f6eecb…`.
- Serving settings: `-ngl all -c 262144 -np 1 -fa on -ctk f16 -ctv f16 --jinja --reasoning-format deepseek --temp 1 --top-p 0.95 --top-k 20 --min-p 0 --metrics`, offline. These are the model card's settings plus `--reasoning-format deepseek`, `--metrics` and `--offline`. Reasoning-preserve stayed at llama.cpp's default (on), as the model card ships it.
- Benchmark mode: the serving suite sent `reasoning_budget_tokens=0` per request. `chat_template_kwargs.enable_thinking=false` was also sent but is a no-op for this template. **The tool-eval run used the server default** (reasoning on), as the Qwen3.8-Flash-Next TensorFold tool-eval run did.
- Deviations from the model card command: the API was bound to `127.0.0.1` on a non-default port in a lab container. The weights revision was pinned and the server ran offline.
- Load generator: a separate macOS host that reached the localhost-bound endpoint through an SSH port forward. llama.cpp offers no cache-flush route.
- Benchmark harness commit `2e61469`, which adds llama.cpp `/tokenize` response support to the serving client. Serving suite `qwen-native-standard-v1` without its needle scenario, run through the combined runner with tool-eval protocol `tool-eval-standard-v1-b60e2f0`. The 240K passkey and a 4x60K stage ran afterwards as a separate long-context stage (`--timeout 900`).

The standard suite ran for 37 minutes and 10 seconds. It issued 314 requests, 980,293 prompt tokens and 146,096 completion tokens, with zero request failures. The long-context stage issued 6 more requests, also with zero failures.

## Decode concurrency

Each request used about 256 prompt tokens and a forced 512-token completion (`ignore_eos`), with reasoning off. Output throughput is the aggregate across concurrent requests. **With `-np 1`, rows above c1 measure queueing behind one slot, not batching.**

| Concurrency | Output tok/s | Speedup vs c1 | Efficiency | TTFT p95 | E2E p95 | Qwen3.8-Flash-Next TF (2 Sparks) |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | **81.73** | 1.00x | 100% | 0.32s | 6.41s | 83.45 |
| 2 | 83.40 | 1.02x | 51% | 6.46s | 12.48s | 129.24 |
| 4 | 82.85 | 1.01x | 25% | 18.95s | 25.00s | 195.56 |
| 8 | 83.03 | 1.02x | 13% | 43.81s | 49.85s | 282.69 |
| 12 | 81.67 | 1.00x | 8% | 69.43s | 75.49s | 362.59 |
| 16 | 82.95 | 1.01x | 6% | 93.22s | 99.25s | 417.63 |

Per-request decode (p50) was 85.72 tok/s at c1, 85.05 at c4, and 84.94 at c16. Each request decodes at full speed once it reaches the slot; the waiting shows up only in TTFT.

## Prefill, context, and prefix reuse

The harness's input tok/s divides prompt tokens by full request wall time, including the short decode. The last column divides each request's prompt tokens by its TTFT (median shown), which is closer to a published prefill rate.

| Workload | Input tok/s | TTFT p95 | E2E p95 | Prompt tokens / TTFT (median) | Qwen3.8-Flash-Next TF input tok/s |
|---|---:|---:|---:|---:|---:|
| prefill-4k-c1 | 1,485.24 | 2.00s | 2.84s | 2,067.8 | 2,010.45 |
| prefill-32k-c1 | 1,848.59 | 16.74s | 17.74s | 1,958.5 | 2,673.36 |
| prefill-128k-c1 | 1,436.04 | 89.89s | 91.70s | 1,465.0 | 2,614.74 |
| needle-240k-c1 (long-context stage) | 1,090.53 | 220.19s | 225.33s | 1,116.0 | 2,436.01 |
| longctx-unique-60k-c4 (long-context stage) | 1,651.03 | 140.79s | 143.31s | — | not measured |
| prefix-unique-32k-c4 | 1,725.84 | 71.12s | 73.12s | — | — |
| prefix-cold-32k-c4 | 5,230.57 | 22.71s | 24.74s | — | — |
| prefix-warm-32k-c4 | 15,020.72 | 6.38s | 8.41s | — | — |

The c4 rows queue behind one slot, so their TTFT includes waiting for the earlier requests. Shared-prefix reuse worked: warm TTFT p95 (6.38s) was far below unique (71.12s), and the cold run already reused the prefix after its first request (22.71s). The four ~61K prompts of the long-context stage also ran one at a time.

## Quality and sustained load

- 240K passkey retrieval (245,735 prompt tokens): **passed**.
- Serial deterministic canaries: 3/4. Concurrency-8 deterministic canaries: 6/8.
- **All three misses are the same canary and are setup-limited, not model errors.** The canary asks the model to reverse `SPARK38` (expected `83KRAPS`) within a 128-token limit. Flint always reasons, and with `reasoning_budget_tokens=0` it reasons inside the visible reply instead, so each attempt ran out of the 128 tokens mid-reasoning (`finish_reason=length`) before giving an answer. The other three canaries passed in every attempt. This is a limit of an always-reasoning model against 128-token canaries, so these results do not show whether the model can do the reversal.
- Twenty-minute c8 soak: 182 requests, zero errors, **74.62 output tok/s**, 48.81s TTFT p95 and 55.06s E2E p95, with per-request decode of 81.70 tok/s at p50. These numbers are queueing behind one slot.

## Memory and host telemetry

The harness host monitor collected 446 samples on the serving node during the standard suite. It does not record GPU process memory. A separate `nvidia-smi` reading after load showed 29,005 MiB used by the server.

| Node | Host used (peak) | Lowest MemAvailable | Swap (peak) | GPU power / temp max |
|---|---:|---:|---:|---:|
| Serving Spark | 44.6 GiB | **77.04 GiB** | 373 MiB | 74.3 W / 79 °C |

With a 262K f16 KV cache and one slot, the server left about 77 GiB of the Spark's memory free throughout the run.

## Tool use

The pinned `tool-eval-standard-v1-b60e2f0` profile ran: a smoke test (score 97), then 69 scenarios in each of three trials, with reasoning on (the server default). **The result is complete (100%)** and comparable within the protocol cohort.

- Mean score **86.0** (median 86.0, stddev 1.0, 95% interval 85.0-87.0); Pass@3 84.1%; Pass^3 75.4%; reliability gap 8.7.
- **Safety gate passed**, with no safety warnings. TC-43 (safety and boundaries) failed in all three trials, TC-57 was partial and TC-58 was flaky.
- Weakest categories: localization 67.0% (TC-18 failed in all three trials), context and state 68.3% (TC-48 failed in all three, TC-25 and TC-63 flaky, TC-46/50/62 partial), error recovery 72.3% (TC-13 and TC-14 flaky), and structured output 75.0% (TC-68 failed in all three, TC-67 partial).
- No scenario recorded an infrastructure failure. llama.cpp issue #31000 (tool-call XML left inside the reasoning for Flint NVFP4) was a known risk before the run. The harness reported no symptom of it, but the raw conversations were not inspected for it.

## Comparison with the selected Qwen3.8-Flash-Next TensorFold baseline

| | This run (Flint NVFP4 GGUF, llama.cpp -np 1, 1 Spark) | Qwen3.8-Flash-Next NVFP4, TensorFold 2x (Oct 8/10) |
|---|---|---|
| Sparks used | **1** | 2 |
| c1 / c4 / c16 decode | 81.73 / 82.85 / 82.95 (queued) | **83.45 / 195.56 / 417.63** |
| c8 decode TTFT p95 | 43.81s (queued) | **1.02s** |
| c8 soak | 74.62 (TTFT p95 48.81s, queued) | **432.90** (TTFT p95 1.00s) |
| 128K input tok/s / TTFT p95 | 1,436 / 89.89s | **2,615 / 48.97s** |
| 240K passkey | passed, 220.19s TTFT p95 | **passed, 98.98s TTFT p95** |
| Prefix 32K c4 unique / warm TTFT p95 | 71.12s / 6.38s (queued) | **43.37s / 0.33s** |
| Quality checks | 10/13 (3 setup-limited reversal misses) | **13/13** |
| Tool-eval mean / Pass^3 | 86.0 / 75.4% (complete) | **88.0 / 79.4%** (incomplete 98.1%) |
| Safety gate | PASSED | PASSED |
| Context window served | 262,144 | **1,048,576** |
| Lowest MemAvailable | **77.04 GiB** | not captured |

Qwen3.8-Flash-Next TensorFold stays the selected lane. It batches concurrent requests, prefills about 1.8x faster at 128K, serves a 4x larger window, and scored slightly higher on tool use. Flint matches its single-stream decode on one Spark while using about 29 GB of GPU memory, which makes it a light single-user option. Its concurrency was not tested here, because one slot was served.

This is an operational comparison, not a controlled A/B: the model, quantization, runtime, slot count, node count, context window and run dates all differ. The serving suite ran with reasoning off for both runs (here via `reasoning_budget_tokens=0`), and both tool-eval runs used reasoning on.

## Validation and method limits

- `-np 1` serves one request at a time. All concurrency, soak and c4 prefix numbers measure queueing, not batching. Throughput with more slots is **not measured**.
- The reversal canary is setup-limited (see above). The canary result does not show whether the model can do the reversal.
- Server-side cache reset was unavailable. Scenario prompts remained unique, but cold labels do not prove a fully reset cache.
- GPU process memory was captured once after load, not during the run.
- The text-only suite does not validate broad model quality or safety, and vision was not tested.
- Raw requests, generated text, internal endpoints, SSH targets, usernames, and host identifiers are excluded. Raw JSON and operational evidence remain private.
