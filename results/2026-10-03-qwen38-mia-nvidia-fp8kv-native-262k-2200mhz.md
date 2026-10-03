# Qwen3.8 Flash Next NVIDIA NVFP4 / FP8 KV native 262K at 2200 MHz

Date: 2026-10-03

Status: **PASS — 599/599 measured requests; 13/13 standard-suite quality checks.**

Retain the 2200 MHz cap and use concurrency 8 for the current native-context
lane. Sustained c8 throughput was effectively unchanged from the uncapped
September 7 baseline, while the capped run used substantially less reported
GPU-rail power and stayed cooler. Single-request decode and cold prefill were
slower, most noticeably at 4K. This was a shared-service run with four small
overlapping completions, detailed below.

Serving recipe: [MiaAI-Lab dual-Spark recipe](https://github.com/MiaAI-Lab/Qwen3.8-Flash-Next-Dual-DGX-Sparks/tree/c2325b22602b51a5faf55fc2bebccc34f3f80b9f),
commit `c2325b22602b51a5faf55fc2bebccc34f3f80b9f`.

## Configuration and reproducibility

- Hardware: two NVIDIA DGX Sparks (GB10), one GPU per rank, connected over
  RoCEv2.
- Checkpoint: `nvidia/Qwen3.8-Flash-Next-NVFP4`, revision
  [`fab0aecb760cec45227f6656abcaafa11abca87a`](https://huggingface.co/nvidia/Qwen3.8-Flash-Next-NVFP4/tree/fab0aecb760cec45227f6656abcaafa11abca87a),
  served as `qwen3.8-flash-next`.
- Runtime: vLLM `0.1.dev20073+g8e685d198`, image
  `vllm/vllm-openai:qwen38-flash-next`, digest
  `sha256:fc120ece0a388cc0aa1caad4a9f1cd92113484ab7ec2fd0efadd62585be05bf8`.
- Tensor parallelism 2; expert parallelism enabled; MTP with 3 draft tokens
  and the full draft vocabulary.
- Native context: **262,144 tokens**, YaRN disabled; FP8 KV cache; GPU memory
  utilization 0.835.
- Maximum sequences 8; maximum batched tokens 8,192; vision encoder uses data
  parallelism.
- Stock QSA launch profile; FP8-dense conversion, PLE CPU offload, and NFS
  sharing disabled. Each node has a local checkpoint copy.
- Common engine KV pool: 3,840,536 tokens, or 14.65 times one native context.
- GPU graphics-clock cap: `0,2200` MHz on both ranks, applied by the retained
  host service. Five-second samples observed 2,171–2,197 MHz.
- Load generator: the same separate Linux host and direct endpoint path used
  by the uncapped September 7 baseline.
- Benchmark harness snapshot: `5492d67ccbea65692664b364bdeabebba334978a`;
  suite `qwen-native-standard-v1`. The suite file SHA-256 remained
  `c4c08c74da1430135666861795927a4625e974ac65f7965119d48b50f4720c26`.

The run lasted 32 minutes and 3 seconds. It measured 1,547,318 prompt tokens
and 291,760 completion tokens. Raw request/response JSON, generated reasoning,
telemetry, endpoint details, and host identifiers remain private.

## Decode concurrency

Approximately 256 prompt tokens and a forced 512-token completion per request.
Output throughput is aggregate across concurrent requests.

| Concurrency | Output tok/s | Speedup vs c1 | Efficiency | TTFT p95 | E2E p95 |
|---:|---:|---:|---:|---:|---:|
| 1 | 44.62 | 1.00x | 100% | 0.42s | 11.95s |
| 2 | 80.92 | 1.81x | 91% | 1.09s | 13.29s |
| 4 | 123.95 | 2.78x | 69% | 1.55s | 17.14s |
| 8 | **202.95** | **4.55x** | **57%** | **1.30s** | **21.21s** |
| 12 | 205.06 | 4.60x | 38% | 19.42s | 39.51s |
| 16 | 200.09 | 4.48x | 28% | 21.76s | 41.89s |

Concurrency 12 added only 1.0% throughput over c8 while increasing TTFT p95
from 1.30 seconds to 19.42 seconds. Concurrency 16 was slower. Concurrency 8
remains the practical interactive and agentic serving limit.

## Prefill and prefix reuse

| Workload | Input tok/s | TTFT p95 | E2E p95 |
|---|---:|---:|---:|
| prefill-4k-c1 | 1,118.26 | 2.41s | 3.98s |
| prefill-32k-c1 | 2,527.51 | 11.85s | 13.32s |
| prefill-128k-c1 | 2,559.04 | 49.41s | 51.36s |
| needle-240k-c1 | 2,375.88 | 102.36s | 103.46s |
| prefix-unique-32k-c4 | 2,616.72 | 45.11s | 50.10s |
| prefix-cold-32k-c4 | 6,236.40 | 16.98s | 21.10s |
| prefix-warm-32k-c4 | 12,690.66 | 6.06s | 10.37s |

The 240K passkey passed. Its 103.46-second end-to-end latency leaves limited
headroom under a 120-second upstream timeout when the service is contended.
Clients that routinely submit near-window prompts should use a longer timeout
or remove the cap when lowest long-prefill latency is more important than
power and thermal headroom.

The server did not expose the harness's cache-flush operation. Scenario-specific
prompts and the deliberate shared-prefix pair were retained, but the cold
labels do not establish a fully reset server cache.

## Quality and sustained load

- Standard suite: 599 requests, 0 failures.
- Quality: 13/13 across the 240K retrieval, serial canaries, and concurrent
  canaries.
- Twenty-minute c8 soak: 466 requests, 0 errors, **196.70 output tok/s**,
  TTFT p50/p95 0.76s / 1.16s, E2E p95 26.09s.
- The backend drained to zero running and waiting requests. Abort and error
  completion counters remained zero.

## Host telemetry

Five-second samples from each rank during the benchmark. Power is the reported
GPU rail reading, not wall or whole-system power.

| Rank | Samples | Peak GPU temperature | Mean / peak GPU-rail power | Mean utilization | Graphics clock range | Minimum available RAM | Peak swap used |
|---|---:|---:|---:|---:|---:|---:|---:|
| 0 | 381 | 62°C | 26.69 / 40.65 W | 93.3% | 2,171–2,197 MHz | 3.82 GiB | 5.59 GiB |
| 1 | 382 | 65°C | 26.27 / 41.22 W | 93.7% | 2,171–2,184 MHz | 5.90 GiB | 3.30 GiB |

Both ranks reported their software and hardware thermal-slowdown reasons as
inactive after the run. The memory figures reinforce the dedicated-lane
posture: do not raise GPU memory utilization or colocate another GPU workload
without a new capacity test.

## Comparison with the uncapped native FP8-KV baseline

| Metric | Uncapped Sep 7 | 2200 MHz Oct 3 | Change |
|---|---:|---:|---:|
| c1 output tok/s | 47.34 | 44.62 | -5.8% |
| c4 output tok/s | 133.49 | 123.95 | -7.1% |
| c8 output tok/s | 198.09 | 202.95 | +2.5% |
| c8 soak output tok/s | 197.42 | 196.70 | -0.4% |
| 4K input tok/s | 1,277.50 | 1,118.26 | -12.5% |
| 32K input tok/s | 2,615.32 | 2,527.51 | -3.4% |
| 128K input tok/s | 2,669.18 | 2,559.04 | -4.1% |
| 240K input tok/s | 2,445.56 | 2,375.88 | -2.9% |
| 240K TTFT | 99.22s | 102.36s | +3.2% |
| Rank 0 mean GPU-rail power | 41.81 W | 26.69 W | -36.2% |
| Rank 1 mean GPU-rail power | 41.96 W | 26.27 W | -37.4% |
| Rank 0 peak temperature | 73°C | 62°C | -11°C |
| Rank 1 peak temperature | 74°C | 65°C | -9°C |

The checkpoint revision, runtime image, topology, serving flags, suite, and
load-generator path match the uncapped baseline. The runs occurred on separate
days rather than as an interleaved A/B. The capped run also had a slightly
larger reported KV pool, different available-memory state, and four small
overlapping requests instead of two. Treat small throughput and latency deltas
as run-to-run variation rather than attributing them solely to the clock cap.

The power and temperature differences are large and directionally consistent
with the cap, but they are still separate-run observations rather than direct
wall-power or controlled thermal measurements.

## Shared-service and method limits

- Aggregate server counter deltas showed 603 completions during the 599-request
  benchmark. The four additional completions accounted for 252 prompt tokens
  and 165 completion tokens; router records identified three of them. They are
  excluded from benchmark request and throughput totals, but their resource
  contention cannot be removed from measured latency.
- Both rank containers remained running with zero restarts and no OOM state.
  The final log scan found no traceback, fatal, CUDA OOM, NCCL failure, or
  segmentation-fault signature.
- The standard text suite does not validate image/video serving, broad model
  quality, coding ability, tool-use quality, or safety behavior.
- Streaming TTFT starts at the first content or reasoning token; chunk
  intervals approximate token latency.

## Operational recommendation

Retain the **2200 MHz cap** and use **concurrency 8** for the current native
FP8-KV lane when sustained throughput, thermals, and reported GPU-rail power
matter. The cap preserved soak throughput and all standard quality checks.

Remove the cap, or benchmark a higher limit, when single-request decode or
cold short-prefill latency is the priority. Keep near-240K routed requests on
a timeout above 120 seconds when concurrent traffic is possible.
