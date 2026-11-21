# Qwen3.8-Flash-Next NVIDIA NVFP4 on vLLM 0.34.0, two Sparks

Date: 2026-11-21

This configuration was tested for tool use. The [three-trial tool evaluation](2026-11-21-qwen38-flash-next-nvfp4-vllm034-2x-262k-tool-eval.md)
contains the scores, completion rate, and scenario findings.

## Tested configuration

- Hardware: two NVIDIA DGX Sparks (GB10, 128 GB each), one GPU per node over RoCEv2.
- Checkpoint: [nvidia/Qwen3.8-Flash-Next-NVFP4 @ fc694b54](https://huggingface.co/nvidia/Qwen3.8-Flash-Next-NVFP4/tree/fc694b54fb0174e0913e6adf86691ef85a4ead47). Both nodes loaded the eleven original weight shards offline.
- Weight quantization: NVIDIA ModelOpt NVFP4 with mixed precision for the other layers.
- Runtime: stock vLLM 0.34.0, ARM64, CUDA 13.0.2.
- Runtime image: `docker.io/vllm/vllm-openai@sha256:e40eb98263fa13418dda684147d73e8ec4a2b0e056a37e955dc189cd1b11dd16`.
- Serving configuration: multiprocess distributed executor, TP2 plus expert parallelism, three MTP draft tokens, BF16 KV cache, text-only mode, four sequences, 8,192 max batched tokens, chunked prefill, prefix caching, 0.80 GPU memory utilization, and full decode-only CUDA graphs. Tool and reasoning parsers were `qwen3_coder` and `qwen3`, with auto tool choice enabled.
- Configured context: 262,144 tokens.
- Recipe reference: [MiaAI-Lab two-Spark vLLM topology](https://github.com/MiaAI-Lab/Qwen3.8-Flash-Next-Dual-DGX-Sparks/tree/cd839d0b62f6c737178a0c2037733420e0524ebf). The test used stock vLLM with the settings above.

## Why this build was tested

The [two-Spark TensorFold tool-eval rerun](2026-11-21-qwen38-flash-next-nvfp4-tensorfold-tool-eval.md)
left TC-64 ungraded after the endpoint rejected its JSON-schema request. The
earlier vLLM image accepted the schema but failed the harness's
`tool_choice="required"` capability probe. This build passed both targeted
scenarios before the pinned standard run started.

The comparison concerns the tool-use workloads of the two serving stacks. The
262,144-token window is a configured limit. Decode throughput, long-context
retrieval, and sustained load require their own serving measurements.
