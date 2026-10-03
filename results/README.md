# Published benchmark results

This page compares the curated, sanitized baselines in this repository. It is
generated from [`catalog.json`](catalog.json) so new results can extend the
same tables and charts without hand-editing this page.

Choosing a model for a workload? Open the [model selection dashboard](MODEL-GUIDE.md).

Last updated: 2026-10-03 · Published baselines: 12

## At a glance

| Model | Hardware / runtime | Configured context | Peak decode tok/s | c1 TTFT p95 | Longest-context TTFT p95 | Soak tok/s | Quality | Recommended concurrency | Recipe credit |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
| [GLM-5.3 Flash NVFP4 (vLLM, low reasoning)](2026-10-03-glm53-flash-nvfp4-vllm-native-262k-low-reasoning.md) | 2x NVIDIA DGX Spark (128GB each) / vLLM | 256K | 66.18 @ c16 | 0.45s | 188.82s | 60.90 | 13/13 | Concurrency 1 interactive; 8 batch; 13/13 with accuracy warning | [MiaAI-Lab GLM-5.3 Flash NVFP4 recipe](https://github.com/MiaAI-Lab/GLM-5.3-Flash-NVFP4-Dual-DGX-Spark/tree/aed98a13ca75140d2691cc5c651ea5817d9a3e44) |
| [Qwen3.8 27B NVFP4 (SGLang)](2026-10-02-qwen38-27b-nvfp4-sglang-native-262k.md) | 1x NVIDIA DGX Spark (128GB) / SGLang | 256K | 187.63 @ c16 | 0.18s | 395.05s | 157.80 | 13/13 | Concurrency 8; 13/13 quality | [MiaAI-Lab Qwen3.8 27B SGLang recipe](https://github.com/MiaAI-Lab/Qwen3.8-27B-SGLang-DGX-Spark/tree/5d2df792a2ca7e076cb80b8302f5349d492d6f54) |
| [Qwen3.8 27B Uncensored FP8 (SGLang)](2026-10-02-qwen38-27b-uncensored-fp8-sglang-native-262k.md) | 1x NVIDIA DGX Spark (128GB) / SGLang | 256K | 72.86 @ c4 | 0.28s | 557.96s | 63.89 | 13/13 | Concurrency 4; derivative checkpoint; 13/13 quality | [MiaAI-Lab Qwen3.8 27B SGLang recipe](https://github.com/MiaAI-Lab/Qwen3.8-27B-SGLang-DGX-Spark/tree/5d2df792a2ca7e076cb80b8302f5349d492d6f54) |
| [DeepSeek V4 Flash 0731 EXL3/SparkInfer](2026-10-02-deepseek-v4-flash-0731-sparkinfer-384k.md) | 1x NVIDIA DGX Spark (128GB) / vLLM + SparkInfer | 384K | 31.44 @ c4 | 0.54s | 259.00s | 26.89 | 13/13 | Concurrency 1; benchmark-only dependency repair | [MiaAI-Lab DeepSeek V4 Flash single-Spark recipe](https://github.com/MiaAI-Lab/DeepSeek-v4-Flash-One-DGX-Spark/tree/d4ba142bc1d971eb73a911e207e3e963bbb3c455) |
| [GLM-5.3 Flash EXL3/TR3 4 bpw (TensorFold v0.6.0)](2026-10-01-glm53-flash-exl3-tensorfold-v060-1m.md) | 2x NVIDIA DGX Spark (128GB each) / TensorFold | 1M | 96.72 @ c12 | 0.41s | 163.89s | 84.90 | 10/13 | Concurrency 1 interactive; 4 batch; 10/13 quality | [MiaAI-Lab TensorFold recipe](https://github.com/MiaAI-Lab/GLM-5.3-Flash-EXL3-2x-DGX-Sparks-TensorFold/tree/978b2252059069b3b4b84f0f7eeb73bc17f28d3f) |
| [GLM-5.3 Flash EXL3/TR3 4 bpw (refreshed recipe)](2026-09-15-glm53-flash-exl3-tr3-4bpw-850k.md) | 2x NVIDIA DGX Spark (128GB each) / vLLM | 850K | 30.68 @ c4 | 1.27s | 287.63s | 21.88 | 13/13 | Concurrency 1 interactive; 4 batch; Socket | [MiaAI-Lab refreshed GLM recipe](https://github.com/MiaAI-Lab/GLM-5.3-Flash-EXL3-2x-DGX-Sparks/tree/a35eaab128233d215b2fc9ac261eddbad23c946d) |
| [DeepSeek V4.1 Flash EXL3 2.9 bpw](2026-09-15-deepseek-v41-flash-exl3-2.9bpw-600k.md) | 2x NVIDIA DGX Spark (128GB each) / vLLM | 600K | 44.49 @ c2 | 0.85s | 408.37s | 35.31 | 13/13 | Concurrency 2; unpacked Engram | [MiaAI-Lab DeepSeek V4.1 EXL3 recipe](https://github.com/MiaAI-Lab/DeepSeek-v4.1-Flash-EXL3-2x-DGX-Sparks/tree/979e68a62c90b24d928f5638596e0ceed90e9f34) |
| [Qwen3.8-Flash-Next NVIDIA NVFP4 (Mia vLLM, FP8 KV)](2026-09-07-qwen38-mia-nvidia-fp8kv-native-262k.md) | 2x NVIDIA DGX Spark (128GB each) / vLLM | 256K | 207.77 @ c16 | 0.40s | 99.22s | 197.42 | 13/13 | Concurrency 8; faster prefill, larger KV pool | [MiaAI-Lab updated dual-Spark recipe](https://github.com/MiaAI-Lab/Qwen3.8-Flash-Next-Dual-DGX-Sparks/tree/c2325b22602b51a5faf55fc2bebccc34f3f80b9f) |
| [Qwen3.8-Flash-Next-NVFP4 (Mia vLLM, 2200 MHz)](2026-09-03-qwen38-flash-next-vllm-mia-yarn-1m-2200mhz.md) | 2x NVIDIA DGX Spark (128GB each) / vLLM | 1M | 213.72 @ c8 | 0.36s | 113.18s | 201.58 | 13/13 | 2200 MHz; concurrency 8 | [MiaAI-Lab Qwen dual-Spark recipe](https://github.com/MiaAI-Lab/Qwen3.8-Flash-Next-Dual-DGX-Sparks/tree/169fbad266f2791335a3102f0d3d625e7c295563) |
| [Qwen3.8-Flash-Next-NVFP4 (Mia vLLM)](2026-08-31-qwen38-flash-next-vllm-mia-yarn-1m.md) | 2x NVIDIA DGX Spark (128GB each) / vLLM | 1M | 209.12 @ c12 | 0.43s | 117.30s | 197.71 | 13/13 | Concurrency 8 | [MiaAI-Lab Qwen dual-Spark recipe](https://github.com/MiaAI-Lab/Qwen3.8-Flash-Next-Dual-DGX-Sparks/tree/169fbad266f2791335a3102f0d3d625e7c295563) |
| [Qwen3.8-Flash-Next-NVFP4](2026-08-29-qwen38-flash-next-nvfp4-native-262k.md) | 2x NVIDIA DGX Spark (128GB each) / SGLang | 256K | 215.06 @ c8 | 0.41s | 598.56s | 157.61 | 13/13 | Concurrency 8 | [Qwen3.8 Flash Next DGX Spark recipe](https://github.com/tomrhudson/qwen38-flash-next-dgx-spark-recipe/tree/main) |
| [GLM-5.3-Flash-EXL3](2026-08-29-glm53-flash-exl3-native-1m.md) | 2x NVIDIA DGX Spark (128GB each) / vLLM | 1M | 79.51 @ c16 | 0.95s | 279.80s | 38.53 | 13/13 | Concurrency 1 interactive; 4 batch | [MiaAI-Lab original recipe](https://github.com/MiaAI-Lab/GLM-5.3-Flash-EXL3-2x-DGX-Sparks/tree/79f10b91f84779b2b1ff2c9327b1a5847cd97f70) |

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
