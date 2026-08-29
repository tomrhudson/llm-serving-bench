# llm-serving-bench

A dependency-free benchmark harness for OpenAI-compatible LLM serving
endpoints. It runs from a separate load-generator host so client work does not
consume the inference server's CPU or unified memory.

The harness measures:

- streaming time to first token (TTFT), end-to-end latency, and chunk ITL;
- input/output throughput and per-request decode rate;
- concurrency speedup and parallel efficiency;
- queue behavior above the engine's effective concurrency limit;
- unique, cold shared-prefix, and warm shared-prefix behavior;
- long-context passkey retrieval;
- deterministic quality canaries under serial and concurrent load;
- selected SGLang cache, speculative-decoding, queue, and retraction metrics;
- optional memory, swap, utilization, temperature, and power over SSH.

No third-party Python packages are required. Python 3.11 or newer is enough.

## Quick start

```bash
python3 -m llm_serving_bench \
  --base-url http://inference-host:8000/v1 \
  --model served-model-name \
  --suite configs/qwen-native-standard.json \
  --output results/run.json \
  --label my-model-native-context \
  --server-label private-direct-endpoint
```

Optional host telemetry uses existing passwordless SSH access:

```bash
  --monitor-host rank0=user@inference-rank0 \
  --monitor-host rank1=user@inference-rank1
```

The JSON result contains per-request measurements, server metric snapshots,
and host samples. A Markdown summary is written beside it. The endpoint URL
and SSH targets are deliberately omitted from persisted output.

## Standard suite

`configs/qwen-native-standard.json` contains the initial reusable matrix:

1. warm-up;
2. fixed 256-input/512-output decode sweeps at concurrency 1, 2, 4, 8, 12,
   and 16;
3. cold 4K, 32K, and 128K prefill tests;
4. unique versus cold/warm shared 32K prefixes;
5. a 240K-token passkey retrieval test;
6. serial and eight-way deterministic canaries;
7. a 20-minute concurrency-8 steady-state soak.

The protocol works with other SGLang and vLLM models that expose OpenAI chat
completions plus the common `/tokenize` endpoint. Copy the JSON and adjust
context lengths for models with smaller native windows.

## Fair comparisons

- Run the client off-cluster over the same network path.
- Keep model, hardware, quantization, sampling, prompt/output token lengths,
  and concurrency fixed for configuration A/B tests.
- Flush prefix cache before cold scenarios and never flush before the paired
  warm scenario.
- Compare actual usage token counts, not character counts.
- Report thinking and non-thinking modes separately.
- Treat speculative-acceptance and Mamba-state metrics as model-specific.
- Do not infer quality from throughput. These canaries detect only obvious
  serving regressions.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

## Result handling

Raw results are ignored because they can contain generated text, model names,
and operational telemetry. Review and sanitize an artifact before force-adding
it to version control.
