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
  --base-url https://inference-host:8000/v1 \
  --model served-model-name \
  --suite configs/qwen-native-standard.json \
  --output results/run.json \
  --label my-model-native-context \
  --server-label private-direct-endpoint
```

Bearer credentials are accepted only with an `https://` base URL. Plain HTTP
remains available without `--api-key-env` for isolated, trusted networks, but it
does not protect prompts or responses from network observers.

Optional host telemetry uses existing passwordless SSH access:

```bash
  --monitor-host rank0=user@inference-rank0 \
  --monitor-host rank1=user@inference-rank1
```

The JSON result contains per-request measurements, server metric snapshots,
and host samples. A Markdown summary is written beside it. The endpoint URL
and SSH targets are deliberately omitted from persisted output.

## Standard new-model workflow

The combined runner executes the serving suite, the pinned
[`tool-eval-bench`](https://github.com/SeraphimSerapis/tool-eval-bench) profile,
NVIDIA RULER v1, LongBench v2, and local τ²-Bench in that order.

```bash
python3 scripts/run_combined_benchmark.py \
  --base-url https://inference-host:8000/v1 \
  --model served-model-name \
  --baseline-id matching-catalog-id \
  --suite configs/qwen-native-standard.json \
  --tokenizer /path/to/checkpoint/tokenizer.json \
  --context-window 262144 \
  --label my-model-native-context \
  --server-label private-direct-endpoint
```

Use the tokenizer from the exact served checkpoint and the context window
configured on the server. Run from the load-generator host with `git`, `uv`,
and access to the upstream repositories, datasets, and Python package indexes.
`uv` provisions isolated Python 3.12 environments for the capability adapters.
Allow several GB for dependencies, source checkouts, and datasets. The standalone
serving harness still runs with just Python 3.11 or newer.

Use `--api-key-env NAME` for authenticated HTTPS endpoints. The key is passed to
inference clients through the environment. All capability inference targets the
provided endpoint, including the τ² simulator and assertion judge.
`--disable-capability-thinking` sends `enable_thinking=false` to compatible chat
templates and matches the Qwen pilot's reasoning setting. Otherwise the endpoint
uses its configured default. For the previous two-stage workflow, use
`--serving-and-tools-only` and omit capability inputs.

The RULER essay downloader builds its corpus from public sources. Use
`--ruler-essays /path/to/PaulGrahamEssays.json` to reuse a corpus from an earlier
run. The runner records its SHA-256, the served tokenizer's SHA-256, pinned
source revisions, dataset checksums, and context and reasoning settings. Compare
RULER runs with matching corpus hashes. Compare LongBench rows with the same
prompt cap, and use the same reasoning setting across capability comparisons.

Raw output, conversations, SQLite data, and logs stay under the ignored
`.bench-runs/` directory. The manifest identifies the capability attempt
directory, which contains `summary.json`, per-suite summaries, and logs. A context
window that cannot accommodate a RULER target plus 128 tokens of chat overhead
skips that target. LongBench uses the smaller of 130,816 and the configured
window minus 256 tokens as its prompt cap. Skipped RULER targets, request failures,
and missing or timed-out τ² grades are marked incomplete in the capability summary.
A wrong answer or a graded τ² simulation that reaches its step limit is scored
normally. Review the manifest and stage logs before comparing results.

After review, create the allowlisted public tool report and catalog entry with:

```bash
python3 scripts/import_tool_eval_result.py \
  --raw-dir .bench-runs/RUN_ID \
  --baseline-id matching-catalog-id \
  --report YYYY-MM-DD-matching-catalog-id-tool-eval.md
python3 scripts/generate_results_summary.py
```

The standard tool profile runs a 15-scenario smoke test followed by 69 scenarios
across three trials. Ordinary model failures remain findings and do not stop the
run. Infrastructure failures or an incomplete smoke test stop safely. Tool-use
scores measure the exact model/runtime/chat-template stack against public mock
tools; they are not general intelligence or safety certification.

A comparative tool-use result requires all 69 scenarios to be graded in all
three trials. The runner records missing grades as `tool-eval-incomplete` and
continues to the capability stages after validating the tool artifact. The
capability summary records its own coverage. After correcting a wrapper-only failure,
`--resume-raw-dir` reuses serving and smoke artifacts when their manifest and
validation checks match, including the endpoint and serving suite fingerprints
for newly created manifests. Each retry creates a fresh capability attempt. A
pre-capability manifest can be resumed with `--serving-and-tools-only`.

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

The protocol works with SGLang, vLLM, TensorFold, and llama.cpp servers that
expose OpenAI chat completions and `/tokenize`. The client supports count-based
tokenization and llama.cpp's native `content`/`tokens` API. Copy the JSON and
adjust context lengths for models with smaller native windows.

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
it to version control. Run `python3 scripts/check_publication_hygiene.py` before
committing a curated report; CI also scans the full reachable history.

## Capability benchmarks

| Benchmark | What it measures | Published results |
| --- | --- | --- |
| [tool-eval-bench](https://github.com/SeraphimSerapis/tool-eval-bench) | Mock-tool selection, arguments, multi-step behavior, and safety gates under the pinned three-trial profile. | [Tool-use results by configuration](results/README.md#tool-use-quality) |
| [NVIDIA RULER v1](https://github.com/NVIDIA/RULER) | Synthetic long-context retrieval, tracking, aggregation, and question answering. | 86.92% at 4K, 86.15% at 32K, and 86.15% at 128K across 78 cases. |
| [LongBench v2](https://github.com/THUDM/LongBench) | Multiple-choice reasoning across six long-context domains. | 9/24 correct (37.5%). Ten responses reached the output cap before producing a parseable answer. |
| [τ²-Bench](https://github.com/sierra-research/tau2-bench/blob/main/docs/running-the-benchmark.md) | Tool-using agents completing tasks with a simulated user in airline, retail, and telecom environments. | 5/9 tasks earned full reward in the custom local pilot. |

The standard capability profile follows the sampled workloads in the
[Qwen3.8-Flash-Next pilot report](results/2026-11-21-qwen38-flash-next-nvfp4-tensorfold-external-evals.md):

- **RULER v1** runs two examples from each of 13 tasks at 4K, 32K, and 128K,
  for 78 cases with full context coverage. It reports macro scores by length.
- **LongBench v2** runs 24 direct-answer questions across six domains and reports
  accuracy, truncation, and unparseable answers.
- **Local τ²-Bench** runs three text simulations each for airline, retail, and
  telecom, with one trial per task. The candidate serves as agent, simulated user,
  and natural-language assertion judge. This custom protocol has its own scores
  and uses different simulator and judge settings from the released leaderboard.

## Published baselines

[Build the Spark Bench website](site/README.md) for a browsable catalog of the
published serving configurations. The website uses [HeroUI](https://heroui.com/)
for its design, including buttons, cards, and status chips.

[Compare all published baselines](results/README.md) for the cross-model table,
decode and prefill charts, and the process for adding future results.

[Open the model selection dashboard](results/MODEL-GUIDE.md) for a workload-first
view of what each model family is good at, when not to use it, and which tested
configuration to choose.

The [results comparison](results/README.md#model-checkpoints) and model dashboard
also identify the exact pinned checkpoint used by each recommended benchmark,
the upstream base model, and one community uncensored/abliterated alternative.
Alternative checkpoints are discovery links only unless an individual report
explicitly benchmarks them.

- [GLM-5.3 Flash EXL3 4 bpw, TensorFold 1.3.0, DFlash2, P4, two DGX Sparks, native 1M context](results/2026-11-20-glm53-flash-exl3-tensorfold-130-dflash2-p4-2x-1m.md) — current [MiaAI-Lab recipe](https://github.com/MiaAI-Lab/GLM-5.3-Flash-DGX-Sparks-1104/tree/a691916c16b6287ebb79ef8ee37ea182b5240a29); 13/13 serving checks and the 240K passkey passed; the [three-trial tool evaluation](results/2026-11-20-glm53-flash-exl3-tensorfold-130-dflash2-p4-2x-1m-tool-eval.md) scored 91.0 but failed the TC-51 safety gate in all three trials
- [NVIDIA Nemotron 3.5 Bolt 74B-A9B 24GB, TensorFold, one DGX Spark, native 262K context](results/2026-10-17-nemotron35-bolt-tensorfold-262k.md) — served with [MiaAI-Lab's Bolt TensorFold recipe](https://github.com/MiaAI-Lab/Nemotron-3.5-Bolt-TensorFold-DGX-Spark/tree/6f61d7727ae3fac010f30e240799cc884d295f6e); complete tool-eval run with a failed safety gate
- [Qwen3.8 27B MLX 4-bit, TensorFold, one DGX Spark, native 262K context, thinking off](results/2026-10-17-qwen38-27b-tensorfold-262k.md) — served with [MiaAI-Lab's Qwen3.8 27B TensorFold recipe](https://github.com/MiaAI-Lab/Qwen3.8-27B-DGX-Spark-TensorFold/tree/c11ff138871cf43d12898d79dbfa4dc952d17ca4); incomplete (98.6%) tool-eval run with a failed safety gate (TC-51)
- [Qwen3.8 27B NVFP4, SGLang, one DGX Spark, native 262K context](results/2026-10-02-qwen38-27b-nvfp4-sglang-native-262k.md) — served with [MiaAI-Lab's single-Spark recipe](https://github.com/MiaAI-Lab/Qwen3.8-27B-SGLang-DGX-Spark/tree/5d2df792a2ca7e076cb80b8302f5349d492d6f54)
- [Qwen3.8 27B Uncensored FP8, SGLang, one DGX Spark, native 262K context](results/2026-10-02-qwen38-27b-uncensored-fp8-sglang-native-262k.md) — derivative checkpoint on the same single-Spark recipe family
- [DeepSeek V4 Flash 0731 EXL3/SparkInfer, one DGX Spark, 384K context](results/2026-10-02-deepseek-v4-flash-0731-sparkinfer-384k.md) — concurrency-1 lane with a documented benchmark-only dependency repair
- [GLM-5.3 Flash NVFP4, vLLM, two DGX Sparks, native 262K context, low reasoning](results/2026-10-03-glm53-flash-nvfp4-vllm-native-262k-low-reasoning.md) — 13/13 standard checks with a documented runtime weight-scale warning
- [Qwen3.8 Flash Next, NVIDIA NVFP4, FP8 KV, native 262K, 2200 MHz cap](results/2026-10-03-qwen38-mia-nvidia-fp8kv-native-262k-2200mhz.md) — sustained c8 throughput held at 196.70 tok/s with lower reported GPU-rail power and temperatures than the separate-day uncapped baseline
- [GLM-5.3 Flash EXL3/TR3 4 bpw, TensorFold v0.6.0, two DGX Sparks, native 1M context](results/2026-10-01-glm53-flash-exl3-tensorfold-v060-1m.md) — served with [MiaAI-Lab's TensorFold recipe](https://github.com/MiaAI-Lab/GLM-5.3-Flash-EXL3-2x-DGX-Sparks-TensorFold/tree/978b2252059069b3b4b84f0f7eeb73bc17f28d3f)
- [GLM-5.3 Flash EXL3/TR3 4 bpw, refreshed recipe, two DGX Sparks, 850K context](results/2026-09-15-glm53-flash-exl3-tr3-4bpw-850k.md) — served with [MiaAI-Lab's refreshed two-Spark recipe](https://github.com/MiaAI-Lab/GLM-5.3-Flash-EXL3-2x-DGX-Sparks/tree/a35eaab128233d215b2fc9ac261eddbad23c946d)
- [DeepSeek V4.1 Flash EXL3 2.9 bpw, two DGX Sparks, native 600K context](results/2026-09-15-deepseek-v41-flash-exl3-2.9bpw-600k.md) — served with [MiaAI-Lab's DeepSeek V4.1 EXL3 recipe](https://github.com/MiaAI-Lab/DeepSeek-v4.1-Flash-EXL3-2x-DGX-Sparks/tree/979e68a62c90b24d928f5638596e0ceed90e9f34)
- [Qwen3.8 Flash Next, updated MiaAI recipe, NVIDIA NVFP4, FP8 KV, native 262K](results/2026-09-07-qwen38-mia-nvidia-fp8kv-native-262k.md) — recipe `c2325b2`, compatible checkpoint revision pinned
- [Qwen3.8-Flash-Next-NVFP4, MiaAI-Lab vLLM recipe, two DGX Sparks, 1M YaRN context, 2200 MHz cap](results/2026-09-03-qwen38-flash-next-vllm-mia-yarn-1m-2200mhz.md) — same exact recipe and model as the stock baseline, with a validated GPU clock cap on both ranks
- [Qwen3.8-Flash-Next-NVFP4, MiaAI-Lab vLLM recipe, two DGX Sparks, 1M YaRN context](results/2026-08-31-qwen38-flash-next-vllm-mia-yarn-1m.md) — served with the exact [MiaAI-Lab dual-Spark recipe](https://github.com/MiaAI-Lab/Qwen3.8-Flash-Next-Dual-DGX-Sparks/tree/169fbad266f2791335a3102f0d3d625e7c295563)
- [Qwen3.8-Flash-Next-NVFP4, two DGX Sparks, native 262K context](results/2026-08-29-qwen38-flash-next-nvfp4-native-262k.md) — served with the [Qwen3.8 Flash Next DGX Spark recipe](https://github.com/tomrhudson/qwen38-flash-next-dgx-spark-recipe/tree/main)
- [GLM-5.3-Flash-EXL3, two DGX Sparks, native 1M context](results/2026-08-29-glm53-flash-exl3-native-1m.md) — served with [MiaAI-Lab's original two-Spark recipe](https://github.com/MiaAI-Lab/GLM-5.3-Flash-EXL3-2x-DGX-Sparks/tree/79f10b91f84779b2b1ff2c9327b1a5847cd97f70)
