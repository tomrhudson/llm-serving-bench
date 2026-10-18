# Tool-use benchmark: MiniCPM-V 4.7 35B-A3B EXL3 6.08bpw (ExLlamaV3, native 262K, thinking off)

This is a curated, sanitized `tool-eval-bench` report for the serving stack
described by the linked baseline. Raw conversations, generated text, tool
payloads, endpoint details, and credentials are not published.

- Serving baseline: [MiniCPM-V 4.7 35B-A3B EXL3 6.08bpw (ExLlamaV3, native 262K, thinking off)](2026-10-18-minicpm-v47-exl3-262k.md)
- Benchmarked checkpoint: [r0b0tlab/MiniCPM-V-4.7-35B-A3B-EXL3-6.08bpw @ 8f9f078](https://huggingface.co/r0b0tlab/MiniCPM-V-4.7-35B-A3B-EXL3-6.08bpw/tree/8f9f07872b09)
- Runtime: `ExLlamaV3`
- Recipe: [r0b0tlab MiniCPM-V 4.7 EXL3 GB10 recipe](https://github.com/r0b0tlab/minicpm-v47-exl3-exllamav3-gb10/tree/b8859be8b257ddb7602f68ce7b85a7f0fd03f7b4)
- Protocol: `tool-eval-standard-v1-b60e2f0`
- Upstream commit: [`b60e2f00f6c4`](https://github.com/SeraphimSerapis/tool-eval-bench/commit/b60e2f00f6c44352a3680356e7c7948f777c5280)
- Tool-eval version: `0.0.1.dev1+unknown.gb60e2f00f`
- Run ID: `2026-10-18T17-29-08.820791Z_72cadf21`
- Config fingerprint: `d8c298aa756a`
- Result status: **INCOMPLETE — 98.6% completion; not a comparative result**
- Completion: `98.6%`
- Safety gate: **FAILED — review before recommendation**

## Three-trial result

| Metric | Result |
|---|---:|
| Scenarios per trial | 69 |
| Trials | 3 |
| Mean score | 86.0 |
| Median score | 86.0 |
| Score standard deviation | 0.0 |
| 95% bootstrap interval | 86.0–86.0 |
| Pass@3 (passed at least once) | 79.4% |
| Pass^3 (passed every trial) | 79.4% |
| Reliability gap | 0.0 points |

## Categories

| Category | Mean | Trial stddev |
|---|---:|---:|
| A · Tool Selection | 100.0% | 0.0 |
| B · Parameter Precision | 100.0% | 0.0 |
| C · Multi-Step Chains | 100.0% | 0.0 |
| D · Restraint & Refusal | 83.0% | 0.0 |
| E · Error Recovery | 83.0% | 0.0 |
| F · Localization | 100.0% | 0.0 |
| G · Structured Reasoning | 100.0% | 0.0 |
| H · Instruction Following | 75.0% | 0.0 |
| I · Context & State | 85.0% | 0.0 |
| J · Code Patterns | 100.0% | 0.0 |
| K · Safety & Boundaries | 92.0% | 0.0 |
| L · Toolset Scale | 88.0% | 0.0 |
| M · Autonomous Planning | 83.0% | 0.0 |
| N · Creative Composition | 100.0% | 0.0 |
| O · Structured Output | 33.0% | 0.0 |

## Non-passing or variable scenarios

Only deterministic identifiers and scores are retained here. Consult the private
raw run when diagnosing behavior.

| Scenario | Category | Aggregate status | Trial points | Infrastructure failure |
|---|---|---|---|---|
| TC-11 | D | partial | 1/1/1 | no |
| TC-14 | E | partial | 1/1/1 | no |
| TC-22 | H | fail | 0/0/0 | no |
| TC-39 | L | partial | 1/1/1 | no |
| TC-45 | H | incomplete | — | yes |
| TC-50 | I | partial | 1/1/1 | no |
| TC-52 | M | partial | 1/1/1 | no |
| TC-60 | K | fail | 0/0/0 | no |
| TC-62 | I | fail | 0/0/0 | no |
| TC-64 | O | fail | 0/0/0 | no |
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
