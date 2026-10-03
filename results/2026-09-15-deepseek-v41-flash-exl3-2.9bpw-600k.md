# DeepSeek V4.1 Flash EXL3 2.9 bpw two-Spark serving baseline

Date: 2026-09-15

Status: **PASS; use concurrency 2 for the best interactive throughput/latency balance**

> Serving recipe credit: This deployment uses [MiaAI-Lab's DeepSeek V4.1 Flash EXL3 2.9 bpw two-DGX-Spark recipe](https://github.com/MiaAI-Lab/DeepSeek-v4.1-Flash-EXL3-2x-DGX-Sparks/tree/979e68a62c90b24d928f5638596e0ceed90e9f34). The serving launcher and GB10 overlay originate from MiaAI-Lab; this document reports independent measurements of that recipe.

## Configuration

- Model: `DeepSeek-v4.1-Flash-EXL3`
- Checkpoint: [`Mia-AiLab/DeepSeek-V4.1-Flash-EXL3-2.9bpw` at revision `64ba41b6c916a587db06eae2e19b7845f7be6e6b`](https://huggingface.co/Mia-AiLab/DeepSeek-V4.1-Flash-EXL3-2.9bpw/tree/64ba41b6c916a587db06eae2e19b7845f7be6e6b)
- Weights: EXL3 2.9 bpw mul1, 39 shards
- Serving topology: two DGX Sparks, tensor parallelism 2 over RoCEv2
- Runtime recipe commit: `979e68a62c90b24d928f5638596e0ceed90e9f34`
- Model revision: `64ba41b6c916a587db06eae2e19b7845f7be6e6b`
- Native Engram revision: `dba1be0a40aa45a94ad051997016db3960a90277`
- Runtime image digest: `sha256:2f0cf3adc0f989c1d446be274df864eb799630175f604c3b22b71b7205971dce`
- Runtime: vLLM `0.1.dev20904+g179dd0fa9`
- Context length: `600000`
- Maximum running sequences: `2`
- Chunked prefill size: `1024`
- Manual KV cache pool: `2684354560` bytes, 798,601-token capacity
- Target KV: native DeepSeek FP8 sparse MLA (`fp8_ds_mla`)
- Speculative decoding: in-checkpoint DSpark k=3
- Engram: native file-backed shards 47 and 48, unpacked
- Prefix caching, tools, and reasoning parser: enabled; vision disabled
- Load generator: separate host, direct OpenAI-compatible endpoint
- Benchmark harness commit: `c86ce28635179c75ce3d5598a712078149b63db0`

The 17-scenario non-thinking suite ran for 71 minutes and 32 seconds. It
issued 222 measured requests, 1,130,840 prompt tokens, and 97,745 completion
tokens with zero request errors. The 240K retrieval and deterministic canaries
passed 13/13.

## Decode concurrency

Each request used approximately 256 input tokens and a forced 512-token
completion. Throughput is aggregate output tokens per second.

| Concurrency | Output tok/s | Speedup vs c1 | Parallel efficiency | TTFT p95 | E2E p95 |
|---:|---:|---:|---:|---:|---:|
| 1 | 27.42 | 1.00x | 100% | **0.85s** | 21.20s |
| 2 | **44.49** | **1.62x** | **81%** | 0.97s | 26.46s |
| 4 | 36.71 | 1.34x | 33% | 33.09s | 61.18s |
| 8 | 41.48 | 1.51x | 19% | 82.41s | 105.86s |
| 12 | 38.30 | 1.40x | 12% | 136.85s | 164.84s |
| 16 | 36.46 | 1.33x | 8% | 208.86s | 235.07s |

Concurrency 2 produced the highest aggregate decode throughput while retaining
sub-second TTFT p95. The server is configured for two active sequences, so
concurrency 4-16 mostly measures queueing rather than added execution capacity.

## Prefill and context

| Workload | Input tok/s | TTFT p95 | E2E p95 | Result |
|---|---:|---:|---:|---|
| 4K unique, c1 | 400.59 | 8.22s | 10.65s | Pass |
| 32K unique, c1 | 559.95 | 57.14s | 59.41s | Pass |
| 128K unique, c1 | 574.38 | 228.63s | 230.75s | Pass |
| 240K passkey, c1 | **601.70** | **408.37s** | 408.37s | **1/1 correct** |

The unpacked, file-backed native Engram path is capacity-safe at 600K but
prefill-heavy. Decode proceeds normally once generation begins. The recipe's
optional packed-Engram path was not used, so these results should not be used
to judge that optimization.

## Prefix-cache effectiveness

Four concurrent requests used approximately 32K input tokens and up to 128
output tokens each.

| Prefix mode | Input tok/s | Output tok/s | TTFT p95 | E2E p95 |
|---|---:|---:|---:|---:|
| Unique | 596.53 | **2.33** | 205.21s | 216.13s |
| Shared, cold | 697.38 | 1.82 | 178.94s | 187.52s |
| Shared, warm | **813.86** | 2.03 | **153.34s** | **160.85s** |

The warm shared prefix reduced TTFT p95 by 14.3% versus the shared cold run and
25.3% versus unique prompts. This vLLM build exposes no cache-reset endpoint,
so the harness recorded cache-flush-unavailable notes. Scenario-specific
prompts kept unrelated cases unique, and the shared cold/warm pair intentionally
reused the same prefix.

## Quality validation

- 240K passkey retrieval: 1/1 correct.
- Serial deterministic canaries: 4/4 correct.
- Concurrency-8 deterministic canaries: 8/8 correct.

## Sustained load

The 20-minute concurrency-8 soak completed 89 requests with zero failures.

| Metric | Result |
|---|---:|
| Aggregate output throughput | 35.31 tok/s |
| TTFT p95 | 97.59s |
| E2E p95 | 126.49s |
| Requests completed | 89 |

Live midpoint state showed two running and six queued requests, with zero
vLLM abort/error counters. Both ranks remained running with zero restarts and
no OOM flag throughout the benchmark.

## Operational recommendation

Use concurrency 2 for interactive and light batch work. It delivered the
highest aggregate decode result, 81% parallel efficiency, and a 0.97-second
TTFT p95. Higher offered concurrency was stable, but its queueing tails make it
unsuitable for latency-sensitive traffic with `max_num_seqs=2`.

Long-prefill latency is the main tradeoff. If 32K-240K prompts are a frequent
workload, benchmark the recipe's optional packed-Engram mode separately before
changing the production deployment.

## Harness and method notes

- Performance scenarios set `chat_template_kwargs.enable_thinking=false` so
  token budgets and deterministic canaries remained comparable. The recipe's
  default thinking mode passed a separate boot warmup but was not benchmarked.
- The run used RoCEv2 on the dedicated CX7 interface. A post-benchmark reload
  later used NCCL socket transport while an RDMA registration issue was
  investigated; that later mode is not represented by these measurements.
- No SSH host samples were persisted because the load generator could not
  authenticate to the Sparks. Container, GPU, memory, metrics, and kernel
  postflight checks were run separately.
- vLLM completed all requests without aborts, errors, restarts, or OOM kills.
  The host kernels did log NVIDIA graphics-context allocation failures under
  unified-memory pressure. Treat this as a dedicated serving lane and do not
  colocate another GPU workload.
- Raw output remains private because it can contain generated text and
  operational telemetry. Endpoint URLs and SSH targets are omitted here.

```bash
python3 -m unittest discover -s tests -v
```
