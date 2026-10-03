# GLM-5.3 Flash EXL3 TensorFold v0.6.0 two-Spark baseline

Date: 2026-10-01

Status: **PERFORMANCE, STABILITY, AND LONG-CONTEXT PASS; 10/13 total quality checks passed**

> Serving recipe credit: This deployment uses [MiaAI-Lab's GLM-5.3 Flash
> EXL3 TensorFold recipe](https://github.com/MiaAI-Lab/GLM-5.3-Flash-EXL3-2x-DGX-Sparks-TensorFold/tree/978b2252059069b3b4b84f0f7eeb73bc17f28d3f).
> The TensorFold patches, launcher, and GB10 tuning originate from MiaAI-Lab;
> this document reports independent measurements of that exact recipe.

## Configuration

- Model: `GLM-5.3-Flash-EXL3`
- Checkpoint: [`Mia-AiLab/GLM-5.3-Flash-EXL3-TR3-4bpw` at revision `9eaebb7c4e96d983dcd538e18624622ba5b820a8`](https://huggingface.co/Mia-AiLab/GLM-5.3-Flash-EXL3-TR3-4bpw/tree/9eaebb7c4e96d983dcd538e18624622ba5b820a8)
- Weights: EXL3/TR3 4 bpw routed experts; q4 dense projections at runtime
- Serving topology: two DGX Sparks, tensor parallelism 2
- Runtime recipe commit: `978b2252059069b3b4b84f0f7eeb73bc17f28d3f`
- Model revision: `9eaebb7c4e96d983dcd538e18624622ba5b820a8`
- DFlash2 revision: `bf582e4eacc1810f76656d1811693ff6c6737d2a`
- Runtime: TensorFold v0.6.0 with patch hash `ae8d1c789b47`
- Published image digest:
  `sha256:22789f0cb3dc308f0b2ce52a33961b88bd624af1725e91e8aba0a74a671bb969`
- Image ID on both nodes:
  `sha256:0266e5767a4fb7cba90e587c6f69ab59dea24a0cd08ea983d333295717e9bf24`
- Context length: `1048576`
- Active streams: `4`
- Shared KV pool at start: `2777088` tokens
- KV precision: FP8
- Speculative decoding: DFlash2 plus copy drafts
- DFlash2 licensing: CC BY-NC-ND 4.0; this serving combination is therefore
  suitable only for non-commercial use unless separately licensed
- Features: shared-prefix reuse, multi-prefill, thinking, vision, tools, and
  structured output available; benchmark requests disabled thinking
- Inter-node transport: RoCE v2 on the dedicated CX7 link
- GPU clock cap: 2,200 MHz service active on both nodes
- Load generator: separate host, direct OpenAI-compatible endpoint
- Benchmark harness commit: `05dab44b5f6513ad851570183f7091cb4fe7ce60`

The 17-scenario non-thinking suite ran for 40 minutes and 3 seconds. It issued
337 measured requests, 1,249,737 prompt tokens, and 157,075 completion tokens
with zero request errors. The 240K passkey retrieval succeeded; deterministic
canaries passed 9/12, for a combined quality result of 10/13.

## Decode concurrency

Each request used approximately 256 input tokens and a forced 512-token
completion. Throughput is aggregate output tokens per second.

| Concurrency | Output tok/s | Speedup vs c1 | Parallel efficiency | TTFT p95 | E2E p95 |
|---:|---:|---:|---:|---:|---:|
| 1 | 51.49 | 1.00x | 100% | **0.41s** | **11.00s** |
| 2 | 67.95 | 1.32x | 66% | 1.49s | 16.96s |
| 4 | **92.68** | **1.80x** | 45% | **1.06s** | 23.95s |
| 8 | 93.53 | 1.82x | 23% | 24.66s | 46.22s |
| 12 | **96.72** | **1.88x** | 16% | 46.79s | 69.00s |
| 16 | 94.55 | 1.84x | 11% | 71.70s | 92.11s |

Concurrency 1 is the interactive posture. Concurrency 4 delivered 95.8% of
the sweep's peak throughput with a 1.06-second TTFT p95. Offering 8-16
requests mostly measured queueing above the four active streams: c12 added
only 4.4% throughput over c4 while increasing TTFT p95 to 46.79 seconds.

## Prefill and context

| Workload | Input tok/s | TTFT p95 | E2E p95 | Result |
|---|---:|---:|---:|---|
| 4K unique, c1 | 913.31 | 3.91s | 5.37s | Pass |
| 32K unique, c1 | 1,662.87 | 18.25s | 19.75s | Pass |
| 128K unique, c1 | 1,625.71 | 79.30s | 80.73s | Pass |
| 240K passkey, c1 | **1,484.02** | **163.89s** | 165.61s | **1/1 correct** |

The passkey result establishes correct retrieval at 240K tokens, within the
configured 1,048,576-token request window. It does not establish simultaneous
full-window capacity for four requests; all streams draw from one shared pool.

## Prefix-cache effectiveness

Four concurrent requests used approximately 32K input tokens and up to 128
output tokens each.

| Prefix mode | Input tok/s | Output tok/s | TTFT p95 | E2E p95 |
|---|---:|---:|---:|---:|
| Unique | 1,408.66 | 5.50 | 86.38s | 92.80s |
| Shared, first pass | 1,469.34 | 5.72 | 83.05s | 89.30s |
| Shared, retained | **23,661.30** | **92.15** | **0.49s** | **5.53s** |

The retained shared prefix reduced TTFT p95 by 99.4% versus its first pass.
TensorFold does not expose the harness's `/flush_cache` operation, so the
first pass is an observed first-use result rather than a hard-reset cache
measurement. Scenario-specific prompts kept unrelated cases unique, and only
the paired shared-prefix scenarios intentionally reused the same prefix.

## Quality validation

- 240K passkey retrieval: 1/1 correct.
- Serial deterministic canaries: 3/4 correct.
- Concurrency-8 deterministic canaries: 6/8 correct.
- Combined quality result: 10/13.

All three misses were the same exact-string case. Asked to reverse `SPARK38`,
the model returned `83KRAP` instead of `83KRAPS` once serially and twice under
concurrency. Three post-run serial retries reproduced `83KRAP`. The requests
completed normally with no transport, timeout, or server error, so this is a
deterministic answer regression for the measured serving combination rather
than a concurrency-only failure.

## Sustained load

The 20-minute concurrency-8 submission window completed 204 requests and then
drained its final in-flight work, with zero failures.

| Metric | Result |
|---|---:|
| Aggregate output throughput | 84.90 tok/s |
| TTFT p95 | 28.42s |
| E2E p95 | 53.54s |
| Requests completed | 204 |

Live state held four decoding streams with four additional admitted requests.
Both ranks remained running with zero restarts, no Docker OOM flag, and no
fatal, OOM, NCCL, or RoCE error signatures. After the run, active requests
returned to zero; retained shared-prefix states remained by design.

## Operational recommendation

Use concurrency 1 for interactive work and concurrency 4 for
throughput-oriented batches. Avoid offering more than four simultaneous
requests when latency tails matter: c8-c16 added little aggregate throughput
while TTFT p95 rose to 24.66-71.70 seconds.

Compared with the 2026-09-15 refreshed vLLM/TR3 baseline, this run observed
3.69x c1 decode throughput, 3.02x c4 decode throughput, 1.76x 240K prefill
throughput, and 3.88x soak throughput. Those figures are not a controlled
TensorFold-only A/B result. Runtime, recipe, model and drafter revisions,
dense-weight quantization, transport, cache design, context limit, and
scheduling all changed. The prior baseline also passed 13/13 quality checks,
where this serving combination passed 10/13.

## Harness and method notes

- Performance scenarios set `chat_template_kwargs.enable_thinking=false` so
  output budgets and deterministic canaries remained comparable.
- Model weights were local on both ranks; the run did not depend on NFS.
- The harness's generic server-metric parser does not recognize TensorFold's
  metric names. `/health`, container state, and rank logs were checked
  separately before, during, and after the run.
- Raw JSON and generated output remain private because they contain generated
  text and detailed operational timing. Endpoint URLs and SSH targets are not
  published.

```bash
python3 -m unittest discover -s tests -v
python3 scripts/generate_results_summary.py --check
```
