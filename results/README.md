# Published benchmark results

This page compares the curated, sanitized baselines in this repository. It is
generated from [`catalog.json`](catalog.json) so new results can extend the
same tables and charts without hand-editing this page.

Last updated: 2026-09-15 · Published baselines: 7

## At a glance

| Model | Hardware / runtime | Configured context | Peak decode tok/s | c1 TTFT p95 | Longest-context TTFT p95 | Soak tok/s | Quality | Recommended concurrency | Recipe credit |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
| [GLM-5.3 Flash EXL3/TR3 4 bpw (refreshed recipe)](2026-09-15-glm53-flash-exl3-tr3-4bpw-850k.md) | 2x DGX Spark / vLLM | 830K | 30.68 @ c4 | 1.27s | 287.63s | 21.88 | 13/13 | Concurrency 1 interactive; 4 batch; Socket | [MiaAI-Lab refreshed GLM recipe](https://github.com/MiaAI-Lab/GLM-5.3-Flash-EXL3-2x-DGX-Sparks/tree/a35eaab128233d215b2fc9ac261eddbad23c946d) |
| [DeepSeek V4.1 Flash EXL3 2.9 bpw](2026-09-15-deepseek-v41-flash-exl3-2.9bpw-600k.md) | 2x DGX Spark / vLLM | 586K | 44.49 @ c2 | 0.85s | 408.37s | 35.31 | 13/13 | Concurrency 2; unpacked Engram | [MiaAI-Lab DeepSeek V4.1 EXL3 recipe](https://github.com/MiaAI-Lab/DeepSeek-v4.1-Flash-EXL3-2x-DGX-Sparks/tree/979e68a62c90b24d928f5638596e0ceed90e9f34) |
| [Qwen3.8-Flash-Next NVIDIA NVFP4 (Mia vLLM, FP8 KV)](2026-09-07-qwen38-mia-nvidia-fp8kv-native-262k.md) | 2x DGX Spark / vLLM | 256K | 207.77 @ c16 | 0.40s | 99.22s | 197.42 | 13/13 | Concurrency 8; faster prefill, larger KV pool | [MiaAI-Lab updated dual-Spark recipe](https://github.com/MiaAI-Lab/Qwen3.8-Flash-Next-Dual-DGX-Sparks/tree/c2325b22602b51a5faf55fc2bebccc34f3f80b9f) |
| [Qwen3.8-Flash-Next-NVFP4 (Mia vLLM, 2200 MHz)](2026-09-03-qwen38-flash-next-vllm-mia-yarn-1m-2200mhz.md) | 2x DGX Spark / vLLM | 1M | 213.72 @ c8 | 0.36s | 113.18s | 201.58 | 13/13 | 2200 MHz; concurrency 8 | [MiaAI-Lab Qwen dual-Spark recipe](https://github.com/MiaAI-Lab/Qwen3.8-Flash-Next-Dual-DGX-Sparks/tree/169fbad266f2791335a3102f0d3d625e7c295563) |
| [Qwen3.8-Flash-Next-NVFP4 (Mia vLLM)](2026-08-31-qwen38-flash-next-vllm-mia-yarn-1m.md) | 2x DGX Spark / vLLM | 1M | 209.12 @ c12 | 0.43s | 117.30s | 197.71 | 13/13 | Concurrency 8 | [MiaAI-Lab Qwen dual-Spark recipe](https://github.com/MiaAI-Lab/Qwen3.8-Flash-Next-Dual-DGX-Sparks/tree/169fbad266f2791335a3102f0d3d625e7c295563) |
| [Qwen3.8-Flash-Next-NVFP4](2026-08-29-qwen38-flash-next-nvfp4-native-262k.md) | 2x DGX Spark / SGLang | 256K | 215.06 @ c8 | 0.41s | 598.56s | 157.61 | 13/13 | Concurrency 8 | [Qwen3.8 Flash Next DGX Spark recipe](https://github.com/tomrhudson/qwen38-flash-next-dgx-spark-recipe/tree/main) |
| [GLM-5.3-Flash-EXL3](2026-08-29-glm53-flash-exl3-native-1m.md) | 2x DGX Spark / vLLM | 1M | 79.51 @ c16 | 0.95s | 279.80s | 38.53 | 13/13 | Concurrency 1 interactive; 4 batch | [MiaAI-Lab original recipe](https://github.com/MiaAI-Lab/GLM-5.3-Flash-EXL3-2x-DGX-Sparks/tree/79f10b91f84779b2b1ff2c9327b1a5847cd97f70) |

Peak decode throughput is useful for batch capacity; c1 TTFT is the better
interactive-latency signal. The longest-context column uses the largest shared
prefill scenario available in the standard suite (currently 240K tokens).

## Decode scaling

![Aggregate decode throughput by offered concurrency](assets/decode-throughput.svg)

Each point uses approximately 256 input tokens and a forced 512-token completion.
Concurrency above the server's active-sequence limit includes queueing.

## Long-context prefill

![Time to first token by prompt length](assets/prefill-ttft.svg)

The prompt-length axis is logarithmic. Lower TTFT is better; every plotted
long-context passkey result was correct.

## Sustained load

![Twenty-minute concurrency-eight soak throughput](assets/soak-throughput.svg)

The soak comparison uses the standard 20-minute concurrency-8 workload. Consult
the linked baseline report for TTFT tails, request counts, and model-specific
operational interpretation.

## Adding another baseline

1. Run the standard suite under comparable hardware, prompt, sampling, and
   token-budget conditions.
2. Review and sanitize the generated output into a curated Markdown report;
   keep raw JSON and generated reasoning private.
3. Add one structured entry to `results/catalog.json`, including any recipe
   credit and the metrics used here.
4. Run `python3 scripts/generate_results_summary.py`, then
   `python3 -m unittest discover -s tests -v`.

The generator validates report links and catalog IDs, then rewrites this page
and the SVG assets deterministically. `--check` verifies that committed output
is current without changing files.

## Comparison limits

- These are serving-system results, not general model-quality rankings.
- Hardware, runtime, quantization, cache state, and active-sequence limits can
  materially change throughput and latency.
- Quality canaries catch obvious serving regressions; they are not a broad
  capability evaluation.
- Read the individual report before drawing conclusions from a single chart.
