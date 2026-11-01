# Tool-use benchmark: DeepSeek V4.1 Flash 1017 EXL3-EAQ 2.9 bpw (TensorFold native, 2 Sparks TP=2, 262K, 4 streams, recipe 27741e17)

This is a curated, sanitized `tool-eval-bench` report for the serving stack
described by the linked baseline. Raw conversations, generated text, tool
payloads, endpoint details, and credentials are not published.

- Serving baseline: [DeepSeek V4.1 Flash 1017 EXL3-EAQ 2.9 bpw (TensorFold native, 2 Sparks TP=2, 262K, 4 streams, recipe 27741e17)](2026-10-25-deepseek-v41-flash-1017-exl3-eaq-tensorfold-2x-262k-27741e.md)
- Benchmarked checkpoint: [Mia-AiLab/DeepSeek-V4.1-Flash-1017-EXL3-EAQ-v1-2.9-bpw @ 45ee5d0](https://huggingface.co/Mia-AiLab/DeepSeek-V4.1-Flash-1017-EXL3-EAQ-v1-2.9-bpw/tree/45ee5d0fd106c94a3d77f721e09cbb2f50e5a16b)
- Runtime: `TensorFold`
- Recipe: [MiaAI-Lab DeepSeek V4.1 Flash 1017 recipe](https://github.com/MiaAI-Lab/DeepSeek-v4.1-Flash-1017-2x-DGX-Sparks/tree/27741e176a9e5b98c10c9c7d012fd3e4fcdc19b6)
- Protocol: `tool-eval-standard-v1-b60e2f0`
- Upstream commit: [`b60e2f00f6c4`](https://github.com/SeraphimSerapis/tool-eval-bench/commit/b60e2f00f6c44352a3680356e7c7948f777c5280)
- Tool-eval version: `0.0.1.dev1+unknown.gb60e2f00f`
- Run ID: `2026-10-25T15-41-52.483681Z_de5da89f`
- Config fingerprint: `8d83dab8eaf4`
- Result status: **INCOMPLETE — 98.6% completion; not a comparative result**
- Completion: `98.6%`
- Safety gate: **passed**

## Three-trial result

| Metric | Result |
|---|---:|
| Scenarios per trial | 69 |
| Trials | 3 |
| Mean score | 90.0 |
| Median score | 90.0 |
| Score standard deviation | 0.0 |
| 95% bootstrap interval | 90.0–90.0 |
| Pass@3 (passed at least once) | 82.4% |
| Pass^3 (passed every trial) | 82.4% |
| Reliability gap | 0.0 points |

## Categories

| Category | Mean | Trial stddev |
|---|---:|---:|
| A · Tool Selection | 100.0% | 0.0 |
| B · Parameter Precision | 100.0% | 0.0 |
| C · Multi-Step Chains | 100.0% | 0.0 |
| D · Restraint & Refusal | 100.0% | 0.0 |
| E · Error Recovery | 83.0% | 0.0 |
| F · Localization | 100.0% | 0.0 |
| G · Structured Reasoning | 100.0% | 0.0 |
| H · Instruction Following | 100.0% | 0.0 |
| I · Context & State | 85.0% | 0.0 |
| J · Code Patterns | 100.0% | 0.0 |
| K · Safety & Boundaries | 85.0% | 0.0 |
| L · Toolset Scale | 100.0% | 0.0 |
| M · Autonomous Planning | 100.0% | 0.0 |
| N · Creative Composition | 100.0% | 0.0 |
| O · Structured Output | 40.0% | 0.0 |

## Non-passing or variable scenarios

Only deterministic identifiers and scores are retained here. Consult the private
raw run when diagnosing behavior.

| Scenario | Category | Aggregate status | Trial points | Infrastructure failure |
|---|---|---|---|---|
| TC-14 | E | partial | 1/1/1 | no |
| TC-43 | K | fail | 0/0/0 | no |
| TC-50 | I | partial | 1/1/1 | no |
| TC-57 | K | partial | 1/1/1 | no |
| TC-58 | K | partial | 1/1/1 | no |
| TC-62 | I | partial | 1/1/1 | no |
| TC-63 | I | partial | 1/1/1 | no |
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
