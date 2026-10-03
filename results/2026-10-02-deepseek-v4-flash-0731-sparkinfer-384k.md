# DeepSeek V4 Flash 0731 SparkInfer single-Spark serving baseline

Date: 2026-10-02

Status: **PASS after a benchmark-only dependency repair; use concurrency 1**

> Serving recipe: [MiaAI-Lab DeepSeek V4 Flash single-Spark recipe](https://github.com/MiaAI-Lab/DeepSeek-v4-Flash-One-DGX-Spark/tree/d4ba142bc1d971eb73a911e207e3e963bbb3c455).

## Configuration

- Model: `0xSero/deepseek-v4-flash-0731-spark`, revision
  `22f28d32b9b29b4352eaa380ff8c2c170b2847ab`
- Served model: `deepseek-v4-flash-0731`
- Hardware: one NVIDIA DGX Spark with 128GB unified memory
- Runtime: vLLM with SparkInfer/B12X container
  `ghcr.io/0xsero/deepseek-v4-flash-0731-spark-sparkinfer@sha256:2e077489a83a0360952828051fe7f7a32c1801e5ce8436d85f7267583d614ff4`
- Load generator: separate host, direct OpenAI-compatible endpoint
- Context length: `384000`
- Maximum running sequences: `1`
- Maximum batched tokens: `8224`
- GPU memory utilization: `0.94`
- KV cache: native 432-byte `nvfp4_ds_mla` records
- Speculative decoding: DSpark K5 with a K64 draft
- Benchmark mode: thinking disabled per request

The 17-scenario standard suite ran for 64 minutes and 45 seconds. It issued
204 measured requests with zero transport or serving errors.

### Startup repair boundary

The retained launcher did not pass its startup gate unchanged. Its boot hook
upgraded `xgrammar` from 0.1.27 to 0.2.8, which also upgraded
`apache-tvm-ffi` from the image's 0.1.10 to 0.1.14.post1. That made the
image's TileLang 0.1.9 fail during mHC initialization.

For this benchmark only, the boot hook pinned `xgrammar==0.2.4` and restored
`apache-tvm-ffi==0.1.10`. Both TileLang and xgrammar then imported, the
recipe's kernel self-test passed, and the model served normally. The retained
deployment files were not changed. Treat the launcher as needing this narrow
dependency repair before its next operational use.

## Decode concurrency

Each request used approximately 256 input tokens and a forced 512-token
completion. Throughput is aggregate output tokens per second.

| Concurrency | Output tok/s | Speedup vs c1 | Parallel efficiency | TTFT p95 | E2E p95 |
|---:|---:|---:|---:|---:|---:|
| 1 | **29.62** | 1.00x | 100% | **0.54s** | **19.18s** |
| 2 | 31.03 | 1.05x | 52% | 21.04s | 36.37s |
| 4 | 31.44 | 1.06x | 27% | 54.29s | 70.40s |
| 8 | 31.08 | 1.05x | 13% | 118.29s | 133.13s |
| 12 | 29.40 | 0.99x | 8% | 195.33s | 213.92s |
| 16 | 29.60 | 1.00x | 6% | 263.50s | 281.85s |

The server intentionally admits one sequence. Aggregate throughput was flat
above concurrency 1 while queueing increased nearly linearly, so c1 is the
only interactive operating point.

## Prefill and context

| Workload | Input tok/s | TTFT p95 | E2E p95 | Result |
|---|---:|---:|---:|---|
| 4K unique, c1 | 653.49 | 3.95s | 6.63s | Pass |
| 32K unique, c1 | 1,046.89 | 28.94s | 31.84s | Pass |
| 128K unique, c1 | 1,020.75 | 126.73s | 129.03s | Pass |
| 240K passkey, c1 | 947.57 | 259.00s | 259.31s | **1/1 correct** |

The configured 384K window was functional through the suite's 240K retrieval
check. This run did not validate quality between 240K and the configured
limit.

## Prefix-cache observation

Four offered requests used approximately 32K input tokens and 128 output
tokens each. The endpoint did not expose a cache-flush operation, so these
numbers are observational rather than a controlled cold-cache A/B.

| Prefix mode | Output tok/s | TTFT p95 | E2E p95 |
|---|---:|---:|---:|
| Unique | 3.82 | 124.04s | 128.93s |
| Shared, nominally cold | 7.73 | 46.78s | 50.96s |
| Shared, warm | **17.95** | **24.47s** | **27.48s** |

Prefix reuse helped materially, but the one-sequence admission limit still
queued the four offered requests.

## Quality validation

- 240K passkey retrieval: 1/1 correct.
- Serial deterministic canaries: 4/4 correct.
- Concurrency-8 deterministic canaries: 8/8 correct.

These checks detect obvious serving regressions; they are not a broad model
quality evaluation.

## Sustained load

The 20-minute concurrency-8 offer completed 71 requests and 36,352 output
tokens with zero failures. The harness then drained the single-sequence queue.

| Metric | Result |
|---|---:|
| Aggregate output throughput | 26.89 tok/s |
| TTFT p95 | 150.18s |
| E2E p95 | 169.53s |
| Per-request decode p50 | 29.26 tok/s |
| Request throughput | 0.053 req/s |

## Operational recommendation

Use **concurrency 1** for this 384K profile. Offered concurrency above one is
queue depth, not serving parallelism. The lane is useful when one-Spark
placement and long input processing matter more than concurrent throughput.

Postflight reported the exact served model, empty running and waiting queues,
zero restarts, `OOMKilled=false`, and no logged traceback, OOM, segmentation,
or NCCL failure. The benchmark-only container was then removed.

## Method notes

- The suite used `chat_template_kwargs.thinking=false`; this runtime uses
  `thinking`, not `enable_thinking`, for the non-thinking template mode.
- Explicit cache flush was unavailable. Prompts remained unique where the
  scenario required uniqueness, but cold-cache claims are intentionally
  limited.
- Streaming TTFT is measured at the first content or reasoning token.
- Chunk intervals approximate inter-token latency because a streaming chunk
  can contain more than one token.
- Raw JSON was retained privately but was not published because it contains
  generated model output and operational telemetry. This report contains no
  endpoint URL, SSH target, username, credential, or internal address.
