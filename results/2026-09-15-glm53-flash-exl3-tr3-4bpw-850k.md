# GLM-5.3 Flash EXL3/TR3 4 bpw refreshed two-Spark baseline

Date: 2026-09-15

Status: **PASS; use concurrency 1 for interactive work and concurrency 4 for throughput-oriented batches**

> Serving recipe credit: This deployment uses [MiaAI-Lab's refreshed GLM-5.3 Flash EXL3 two-DGX-Spark recipe](https://github.com/MiaAI-Lab/GLM-5.3-Flash-EXL3-2x-DGX-Sparks/tree/a35eaab128233d215b2fc9ac261eddbad23c946d). The serving launcher and GB10 overlay originate from MiaAI-Lab; this document reports independent measurements of that recipe.

## Configuration

- Model: `GLM-5.3-Flash-EXL3`
- Weights: EXL3/TR3 4 bpw, 120 shards
- Serving topology: two DGX Sparks, tensor parallelism 2
- Runtime recipe commit: `a35eaab128233d215b2fc9ac261eddbad23c946d`
- Model revision: `25a44fdbf16862a46b7cc9921142c6c81350af2f`
- DFlash2 revision: `dc77ff1c99eeb2df044ee3d4f0094eb033fee410`
- Locally built image ID: `sha256:0362b6f91756f892cb17a13f332b9e484862d739b411687108cf4b237f5440de`
- Recipe build stamp: `cad6e72bd28db8be3934893ca72c5c876378befcfa832ccacbe42add6b1ce2fa`
- Runtime: vLLM `0.1.dev20051+g487ecf187`
- Context length: `850000`
- Maximum running sequences: `4`
- Maximum batched tokens: `7168`
- GPU memory utilization: `0.85`
- Target KV: FP8 sparse MLA (`fp8_ds_mla`)
- Speculative decoding: DFlash2 k=7, draft TP2
- Mixed-prefill policy: fair, 256-token chunks, 20% prefill share
- Prefix caching, tools, reasoning, and vision: enabled
- Inter-node transport: NCCL Socket on the dedicated CX7 interface
- Load generator: separate host, direct OpenAI-compatible endpoint
- Benchmark harness commit: `c86ce28635179c75ce3d5598a712078149b63db0`

The 17-scenario non-thinking suite ran for 72 minutes and 6 seconds. It
issued 189 measured requests, 1,097,160 prompt tokens, and 81,291 completion
tokens with zero request errors. The 240K retrieval and deterministic canaries
passed 13/13.

## Decode concurrency

Each request used approximately 256 input tokens and a forced 512-token
completion. Throughput is aggregate output tokens per second.

| Concurrency | Output tok/s | Speedup vs c1 | Parallel efficiency | TTFT p95 | E2E p95 |
|---:|---:|---:|---:|---:|---:|
| 1 | 13.96 | 1.00x | 100% | **1.27s** | **39.99s** |
| 2 | 22.68 | 1.62x | 81% | 15.26s | 58.07s |
| 4 | **30.68** | **2.20x** | 55% | 10.48s | 75.51s |
| 8 | 25.60 | 1.83x | 23% | 125.72s | 177.88s |
| 12 | 27.61 | 1.98x | 16% | 173.89s | 229.41s |
| 16 | 26.88 | 1.93x | 12% | 267.50s | 318.33s |

Concurrency 1 is the interactive posture. Concurrency 4 produced the highest
aggregate decode throughput, but its 10.48-second TTFT p95 is batch-oriented.
The server is configured for four active sequences, and concurrency 8-16 mostly
measures queueing rather than additional execution capacity.

## Prefill and context

| Workload | Input tok/s | TTFT p95 | E2E p95 | Result |
|---|---:|---:|---:|---|
| 4K unique, c1 | 420.55 | 5.27s | 9.97s | Pass |
| 32K unique, c1 | 781.30 | 37.52s | 42.80s | Pass |
| 128K unique, c1 | 873.52 | 147.68s | 151.27s | Pass |
| 240K passkey, c1 | **843.89** | **287.63s** | 291.23s | **1/1 correct** |

The 240K passkey test establishes correct retrieval well inside the configured
850K API limit. Startup reported a 16.38 GiB KV pool and a 984,210-token nominal
capacity, while the hybrid attention/state cache log reported an approximately
57K aligned cached-conversation upper bound for its most constrained group.
Treat 850K as the accepted request limit, not as evidence that several very-long
requests will remain resident concurrently.

## Prefix-cache effectiveness

Four concurrent requests used approximately 32K input tokens and up to 128
output tokens each.

| Prefix mode | Input tok/s | Output tok/s | TTFT p95 | E2E p95 |
|---|---:|---:|---:|---:|
| Unique | 743.24 | 2.90 | 163.59s | 171.63s |
| Shared, first pass | 2,158.32 | 8.41 | 49.28s | 60.88s |
| Shared, warm | **5,549.22** | **21.61** | **11.76s** | **23.57s** |

The warm shared prefix reduced TTFT p95 by 76.1% versus its first pass. This
vLLM build did not provide a cache-reset operation compatible with the harness,
so it recorded cache-flush-unavailable notes. Scenario-specific prompts kept
unrelated cases unique, and the paired shared-prefix scenarios intentionally
reused the same prefix, but the first pass should not be treated as a
hard-reset cache measurement.

## Quality validation

- 240K passkey retrieval: 1/1 correct.
- Serial deterministic canaries: 4/4 correct.
- Concurrency-8 deterministic canaries: 8/8 correct.

## Sustained load

The 20-minute concurrency-8 load window completed 56 requests, then allowed
the final in-flight requests to drain, with zero failures.

| Metric | Result |
|---|---:|
| Aggregate output throughput | 21.88 tok/s |
| TTFT p95 | 181.03s |
| E2E p95 | 230.85s |
| Requests completed | 56 |

Live state typically showed four running requests with the remainder queued.
Both ranks remained running with zero restarts and no Docker OOM flag, and the
vLLM abort, error, and repetition counters remained zero.

## Operational recommendation

Use concurrency 1 when interactive response time matters. Use concurrency 4
for throughput-oriented batches; it delivered the 30.68 tok/s peak in this
sweep. Avoid offering more than four simultaneous requests when latency tails
matter because throughput did not improve while TTFT p95 rose above two minutes.

This result is not a controlled A/B comparison with the 2026-08-29 GLM
baseline. The recipe commit, vLLM build, DFlash topology, context limit,
batched-token limit, scheduling patches, GPU-memory setting, and inter-node
transport differ. Those changes must be isolated before attributing the lower
decode throughput to any one component.

## Harness and method notes

- Performance scenarios set `chat_template_kwargs.enable_thinking=false` so
  token budgets and deterministic canaries remained comparable. The recipe's
  default thinking mode passed its boot-shape warmup but was not benchmarked.
- The recipe's RoCE launch failed before model load on worker memory registration
  (`ibv_reg_mr_iova2: Cannot allocate memory`). The measured run used NCCL
  Socket on the same dedicated CX7 interfaces; no broader container privileges
  were added.
- Model weights were local on both ranks; the run did not depend on NFS.
- No SSH host samples were persisted. Container, memory, metrics, and kernel
  postflight checks were run separately.
- vLLM completed every measured request without an abort, error, restart, or
  OOM kill. Under near-full unified memory, both kernels logged transient NVIDIA
  graphics-context allocation failures. They stopped without affecting
  inference, but this should remain a dedicated serving lane with no colocated
  GPU workload.
- Raw output remains private because it can contain generated text and
  operational telemetry. Endpoint URLs and SSH targets are omitted here.

```bash
python3 -m unittest discover -s tests -v
```
