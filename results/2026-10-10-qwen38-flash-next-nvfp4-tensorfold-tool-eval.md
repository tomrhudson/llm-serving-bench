# Tool-use benchmark: Qwen3.8-Flash-Next NVIDIA NVFP4 (TensorFold, 1M YaRN)

This is a curated, sanitized `tool-eval-bench` report for the serving stack
described by the linked baseline. Raw conversations, generated text, tool
payloads, endpoint details, and credentials are not published.

- Serving baseline: [Qwen3.8-Flash-Next NVIDIA NVFP4 (TensorFold, 1M YaRN)](2026-10-08-qwen38-flash-next-nvfp4-tensorfold-1m.md)
- Benchmarked checkpoint: [nvidia/Qwen3.8-Flash-Next-NVFP4 @ fc694b5](https://huggingface.co/nvidia/Qwen3.8-Flash-Next-NVFP4/tree/fc694b54fb0174e0913e6adf86691ef85a4ead47)
- Runtime: `TensorFold`
- Recipe: [MiaAI-Lab TensorFold recipe](https://github.com/MiaAI-Lab/Qwen3.8-Flash-Dual-DGX-Sparks-TensorFold/tree/be3ed857ab1055ca47b36134d22691f00f2bb94a)
- Protocol: `tool-eval-standard-v1-b60e2f0`
- Upstream commit: [`b60e2f00f6c4`](https://github.com/SeraphimSerapis/tool-eval-bench/commit/b60e2f00f6c44352a3680356e7c7948f777c5280)
- Tool-eval version: `0.0.1.dev1+unknown.gb60e2f00f`
- Run ID: `2026-10-10T23-37-29.940681Z_5237fb4c`
- Config fingerprint: `b1a4d10ff3c2`
- Result status: **INCOMPLETE — 98.1% completion; not a comparative result**
- Completion: `98.1%`
- Safety gate: **passed**

## Three-trial result

| Metric | Result |
|---|---:|
| Scenarios per trial | 69 |
| Trials | 3 |
| Mean score | 88.0 |
| Median score | 88.0 |
| Score standard deviation | 0.0 |
| 95% bootstrap interval | 88.0–88.0 |
| Pass@3 (passed at least once) | 79.4% |
| Pass^3 (passed every trial) | 79.4% |
| Reliability gap | 0.0 points |

## Categories

| Category | Mean | Trial stddev |
|---|---:|---:|
| A · Tool Selection | 100.0% | 0.0 |
| B · Parameter Precision | 67.0% | 0.0 |
| C · Multi-Step Chains | 100.0% | 0.0 |
| D · Restraint & Refusal | 100.0% | 0.0 |
| E · Error Recovery | 100.0% | 0.0 |
| F · Localization | 100.0% | 0.0 |
| G · Structured Reasoning | 100.0% | 0.0 |
| H · Instruction Following | 100.0% | 0.0 |
| I · Context & State | 90.0% | 0.0 |
| J · Code Patterns | 100.0% | 0.0 |
| K · Safety & Boundaries | 85.0% | 0.0 |
| L · Toolset Scale | 88.0% | 0.0 |
| M · Autonomous Planning | 83.0% | 0.0 |
| N · Creative Composition | 100.0% | 0.0 |
| O · Structured Output | 40.0% | 0.0 |

## Non-passing or variable scenarios

Only deterministic identifiers and scores are retained here. Consult the private
raw run when diagnosing behavior.

| Scenario | Category | Aggregate status | Trial points | Infrastructure failure |
|---|---|---|---|---|
| TC-06 | B | fail | 0/0/0 | no |
| TC-40 | L | partial | 1/1/1 | no |
| TC-43 | K | partial | 1/1/1 | no |
| TC-45 | H | incomplete | 2/2 | yes |
| TC-50 | I | partial | 1/1/1 | no |
| TC-51 | M | partial | 1/1/1 | no |
| TC-57 | K | partial | 1/1/1 | no |
| TC-58 | K | partial | 1/1/1 | no |
| TC-60 | K | partial | 1/1/1 | no |
| TC-62 | I | partial | 1/1/1 | no |
| TC-64 | O | incomplete | — | yes |
| TC-65 | O | partial | 1/1/1 | no |
| TC-66 | O | partial | 1/1/1 | no |
| TC-67 | O | partial | 1/1/1 | no |
| TC-68 | O | fail | 0/0/0 | no |
| TC-69 | O | partial | 1/1/1 | no |

## Evidence boundary

- These are public scenarios and may be represented in model training data.
- Mock tools test tool selection, parameters, chaining, recovery, and boundaries;
  they do not validate a production tool implementation.
- Each scenario is one assistant conversation. This does not test delegation,
  independent agents, or inter-agent handoffs.
- Chat templates, tool parsers, reasoning settings, and serving runtimes can
  materially change the result even when model weights are unchanged.
- This score is a serving-stack tool-use result, not a general intelligence or
  safety certification.
