# DeepSeek V4.1 Flash 1017 EXL3-EAQ 2.9 bpw: TensorFold native, two Sparks (TP=2), 262K, thinking off

Date: 2026-10-19

Status: **PASS: 386/386 requests (380 standard-suite + 6 long-context) and 13/13 quality checks. Tool-eval INCOMPLETE (98.6%; TC-64 not scored): 90.0 mean, Pass^3 83.8%. Safety gate PASSED.**

This is the first baseline for `deepseek-ai/DeepSeek-V4.1-Flash-1017`, served from Mia-AiLab's EXL3-EAQ 2.9 bpw quantization on MiaAI-Lab's two-Spark TensorFold recipe. The engine is a native Zig TensorFold build with tensor parallelism across both Sparks, a shared 262,144-token pool, and **4 concurrent streams**. It was run with the same harness and the same thinking-off serving suite as the selected [Qwen3.8-Flash-Next TensorFold baseline](2026-10-08-qwen38-flash-next-nvfp4-tensorfold-1m.md); the 240K passkey and a new four-way ~61K-token check ran in a separate, final long-context stage.

Single-stream decode was **65.62 output tok/s** and c4 reached **119.53 tok/s**. Above c4, requests queue: aggregate decode stayed at 120-123 tok/s through c16 while TTFT p95 grew to 52.79s, and the 20-minute c8 soak sustained 103.17 tok/s with zero errors. Prefill was about 1.1K-1.7K tok/s at 32K-128K (128K TTFT p95 127.77s). The 240K passkey passed and four concurrent ~61K-token prompts all completed. The tool-eval run scored 90.0 with **its safety gate passed**, but it is incomplete (TC-64 was an infrastructure failure), so it is not a comparative result. Both Sparks must be dedicated: each node held about 104-105 GiB of GPU memory.

Serving recipe: [MiaAI-Lab DeepSeek V4.1 Flash 1017 2x DGX Sparks](https://github.com/MiaAI-Lab/DeepSeek-v4.1-Flash-1017-2x-DGX-Sparks/tree/1afc8910b76574aa6b844a08ec9643d14d57089a), commit `1afc8910b76574aa6b844a08ec9643d14d57089a` (October 19, 2026).

Tool-use report: [three-trial `tool-eval-bench` result](2026-10-19-deepseek-v41-flash-1017-exl3-eaq-tensorfold-2x-262k-tool-eval.md).

## Configuration and reproducibility

- Hardware: two NVIDIA DGX Sparks (GB10, 128GB unified memory each), dedicated to this server and joined by a direct QSFP link. Rank 0 is the head and serves HTTP; rank 1 is a headless worker.
- Checkpoint: `Mia-AiLab/DeepSeek-V4.1-Flash-1017-EXL3-EAQ-v1-2.9-bpw`, revision [`6d54be4fca338d79b17c3b03cc9a423bb3ac6718`](https://huggingface.co/Mia-AiLab/DeepSeek-V4.1-Flash-1017-EXL3-EAQ-v1-2.9-bpw/tree/6d54be4fca338d79b17c3b03cc9a423bb3ac6718) (47 files, 210.7 GB, MIT, not gated). Every file was checked by size and LFS sha256 against the Hub at the pinned revision (47/47). Served as `DeepSeek-V4.1-Flash-1017`.
- Engram: `deepseek-ai/DeepSeek-V4.1-Flash-1017`, revision [`1bae0e1088993b9b82de08f59de5be5a34e42170`](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash-1017/tree/1bae0e1088993b9b82de08f59de5be5a34e42170), shards 47 and 48 plus index and config only (203.1 GB, sha256 verified on both nodes).
- Runtime: TensorFold (native Zig, TP=2) built locally by the recipe's `prepare.sh` with `PULL=0` (no registry image was pulled); image `tensorfold-dsv41:exl3-tp2-1cbf54e3684f`, identical on both nodes. The recipe's kit (`abe07c7d`) matched its manifest.
- Serving settings: `CONTEXT=262144`, one shared 262,144-token pool, `max_batch_size` 4 (4 concurrent streams; further requests wait), draft decoding enabled, thinking on by default in the chat template.
- Benchmark mode: thinking disabled per request (`chat_template_kwargs.enable_thinking=false`) for the serving suite. **The tool-eval run used the server default, thinking on** (max_tokens 16384), as the Qwen3.8-Flash-Next TensorFold tool-eval run did.
- Deviations: the API was bound to `127.0.0.1` on a non-default port with a local container name, and the recipe's documented local-copy mode was used instead of NFS: `prepare.sh` stopped at its NFS step as expected, and the worker's local tree (rank-1 weight file, Engram, small files, and shard 39) was staged over the QSFP link and compared with the head's tree before start.
- Load generator: a separate macOS host that reached the localhost-bound endpoint through an SSH port forward. The runtime serves `/tokenize`; it does not offer a cache-flush route.
- Benchmark harness commit: `7af7cce`; serving suite `qwen-native-standard-v1` without its needle scenario (`qwen-native-standard-v1-minus-needle`, per-request `enable_thinking=false`), followed by a long-context stage (`needle-240k-c1`, `longctx-unique-60k-c4`); combined runner with tool-eval protocol `tool-eval-standard-v1-b60e2f0`.
- The recipe is Apache-2.0. The TensorFold fork and kit are Apache-2.0. The weights are MIT.

The standard suite ran for 36 minutes and 15 seconds. It issued 380 requests, 1,049,097 prompt tokens, and 179,326 completion tokens, with zero request failures. The long-context stage ran for 4 minutes and 14 seconds: 6 requests, 491,577 prompt tokens, 507 completion tokens, zero failures.

## Decode concurrency

Each request used about 256 prompt tokens and a forced 512-token completion (`ignore_eos`), with thinking off. Output throughput is the aggregate across concurrent requests.

| Concurrency | Output tok/s | Speedup vs c1 | Efficiency | TTFT p95 | E2E p95 | Qwen3.8-Flash-Next TF |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | **65.62** | 1.00x | 100% | 0.48s | 8.40s | 83.45 |
| 2 | 90.25 | 1.38x | 69% | 0.86s | 13.29s | 129.24 |
| 4 | **119.53** | 1.82x | 46% | 1.28s | 20.20s | 195.56 |
| 8 | 120.56 | 1.84x | 23% | 19.48s | 36.40s | 282.69 |
| 12 | 123.06 | 1.88x | 16% | 35.61s | 50.88s | 362.59 |
| 16 | 123.18 | 1.88x | 12% | 52.79s | 71.16s | 417.63 |

Per-request decode (p50) was 66.65 tok/s at c1, 33.32 at c4, and 32.35 at c16. Throughput is flat above c4 because the engine serves 4 streams; the extra requests queue, which shows up as TTFT.

## Prefill, context, and prefix reuse

The harness's input tok/s divides prompt tokens by full request wall time, including the short decode. The last column divides each request's prompt tokens by its TTFT (median shown), which is closer to a published prefill rate.

| Workload | Input tok/s | TTFT p95 | E2E p95 | Prompt tokens / TTFT (median) | Qwen3.8-Flash-Next TF input tok/s |
|---|---:|---:|---:|---:|---:|
| prefill-4k-c1 | 1,218.50 | 2.32s | 3.56s | 1,884.3 | 2,010.45 |
| prefill-32k-c1 | 1,719.72 | 19.56s | 20.80s | 1,705.7 | 2,673.36 |
| prefill-128k-c1 | 1,095.33 | 127.77s | 129.39s | 1,118.5 | 2,614.74 |
| needle-240k-c1 (long-context stage) | 1,959.11 | 125.17s | 125.42s | 1,963.1 | 2,436.01 |
| longctx-unique-60k-c4 (long-context stage) | 2,084.02 | 109.58s | 117.81s | — | not measured |
| prefix-unique-32k-c4 | 1,253.61 | 95.92s | 104.73s | — | — |
| prefix-cold-32k-c4 | 3,213.80 | 37.04s | 40.74s | — | — |
| prefix-warm-32k-c4 | 10,168.82 | 9.15s | 12.83s | — | — |

The 240K passkey was correct (245,718-token prompt, 125.17s to first token). Four concurrent prompts of 61,213-61,619 tokens (about 245.6K tokens in the shared pool at once) all completed, with TTFT p50 71.10s and p95 109.58s, and no out-of-memory event. Warm shared-prefix reuse lowered TTFT p95 from 95.92s (unique) to 9.15s. The cold phase also ran faster than unique (37.04s); because the cache could not be flushed, cold labels do not prove a reset cache.

## Quality and sustained load

- 240K passkey retrieval: 1/1.
- Serial deterministic canaries: 4/4.
- Concurrency-8 deterministic canaries: 8/8.
- Twenty-minute c8 soak: 248 requests, zero errors, **103.17 output tok/s**, 26.40s TTFT p95 and 50.00s E2E p95, with per-request decode of 26.93 tok/s at p50.

## Memory and host telemetry

The harness host monitor collected 435 samples per node during the standard suite and 51 per node during the long-context stage. It does not record GPU memory; the GPU process column comes from a separate 5-second operator memory log covering the whole run.

| Node | Server GPU process memory (max) | Host used (peak) | Lowest MemAvailable (harness / 5 s log) | Swap (peak) | GPU power / temp max |
|---|---:|---:|---:|---:|---:|
| Rank 0 (head) | 107,545 MiB (about 105.0 GiB) | 115.7 GiB | 6.0 / 5.45 GiB | 1,099 MiB | 60.4 W / 78 °C |
| Rank 1 (worker) | 106,128 MiB (about 103.6 GiB) | 113.4 GiB | 8.3 / 7.93 GiB | 1,003 MiB | 63.2 W / 78 °C |

At load, rank 0 reported 0.0 GiB left after its 12.2 GiB reserve at the 262,144-token window. The lowest head MemAvailable (5.45 GiB) came during the tool-eval run, about 1.5 GiB above the 4 GiB memory guard used for this run, which never fired. Nothing else should share either Spark. The engine bound its API and one helper port to loopback and its other ports only to the private QSFP link; no wildcard or LAN bind was observed.

## Tool use

The pinned `tool-eval-standard-v1-b60e2f0` profile ran: a smoke test (score 97), then 69 scenarios in each of three trials, with **thinking on** (the server default). **The result is incomplete (98.6%)**: TC-64 was not scored in any trial (infrastructure failure), so the run is pilot evidence, not a comparative result.

- Mean score **90.0** (median 90.0, stddev 0.0); Pass@3 83.8%; Pass^3 83.8%; reliability gap 0.0.
- **Safety gate PASSED.** TC-60 (cross-turn sleeper injection) and TC-51 (goal-level planning) passed in all three trials. TC-43 (omitted required parameter) and TC-68 failed 3/3; these are not gate scenarios.
- Weakest categories: structured output 40.0% (TC-68 failed, TC-65/66/67/69 partial, TC-64 unscored), error recovery 83.0% (TC-14 partial), safety and boundaries 85.0% (TC-43 failed, TC-57/58 partial), toolset scale 88.0% (TC-40 partial), and context and state 95.0% (TC-50 partial).

## Comparison with the selected Qwen3.8-Flash-Next TensorFold baseline

| | This run (DeepSeek V4.1 Flash 1017, TensorFold 2x) | Qwen3.8-Flash-Next NVFP4, TensorFold 2x (Oct 8/10) |
|---|---|---|
| c1 / c4 / c16 decode | 65.62 / 119.53 / 123.18 | **83.45 / 195.56 / 417.63** |
| c8 decode TTFT p95 | 19.48s | **1.02s** |
| c8 soak | 103.17 (TTFT p95 26.40s) | **432.90** (TTFT p95 1.00s) |
| 128K input tok/s / TTFT p95 | 1,095 / 127.77s | **2,615 / 48.97s** |
| 240K passkey TTFT p95 | 125.17s | **98.98s** |
| Prefix 32K c4 unique / warm TTFT p95 | 95.92s / 9.15s | **43.37s / 0.33s** |
| Quality checks | 13/13 | 13/13 |
| 4 x ~61K concurrent | 4/4, TTFT p95 109.58s | not measured |
| Tool-eval mean / Pass^3 | 90.0 / 83.8% (incomplete 98.6%) | 88.0 / 79.4% (incomplete 98.1%) |
| Safety gate | PASSED | PASSED |
| Context window served | 262,144 | 1,048,576 |
| GPU memory per node | about 104-105 GiB | not captured |

Qwen3.8-Flash-Next remains the selected two-Spark lane: it is faster at every decode concurrency, prefills 128K about 2.4x faster, serves a 4x larger window, and leaves more memory headroom. This DeepSeek lane's tool-eval score is slightly higher, but both tool-eval runs are incomplete, so that difference is not a comparative result. A possible niche is single-user, tool-heavy work at concurrency 1-4.

This is an operational comparison, not a controlled A/B: model, quantization, runtime build, stream count, context window, and run dates all differ. The serving suite ran thinking off for both, and both tool-eval runs used thinking on.

## Validation and method limits

- Server-side metrics and a cache-reset route were unavailable. Scenario prompts remained unique, but cold labels do not prove a fully reset cache.
- The 240K passkey ran in a separate long-context stage after the tool-eval run instead of inside the standard suite.
- GPU memory comes from a separate operator log, not the harness monitor.
- The text-only suite does not validate broad model quality or safety.
- Raw requests, generated text, internal endpoints, SSH targets, usernames, and host identifiers are excluded. Raw JSON and operational evidence remain private.
