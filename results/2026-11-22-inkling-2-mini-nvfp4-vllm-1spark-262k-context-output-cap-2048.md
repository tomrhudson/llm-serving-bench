# Inkling 2 Mini · RULER and LongBench v2 at a 2,048-token output cap

Rerun date 2026-11-22. See the [serving baseline](2026-11-21-inkling-2-mini-nvfp4-vllm-1spark-262k.md) and [original capability report](2026-11-21-inkling-2-mini-nvfp4-vllm-1spark-262k-capabilities.md).

This rerun reused the same Inkling 2 Mini NVFP4 checkpoint and vLLM container on one DGX Spark, with
DSpark7, a 262,144-token context window, and default reasoning. The output cap applies to both
reasoning and answer tokens. The benchmark samples, sent prompts, temperatures, and grading rules
were held fixed. RULER used its saved prompts at temperature 0. LongBench v2 reused the original 24
questions, the same tokenizer and zero-shot template, temperature 0.1, and the same 130,816-token
prompt cap with middle truncation. Both evaluations sent requests serially.

## RULER v1

The standard run used upstream task-specific caps of 30–128 output tokens. The rerun uses 2,048 for every task.

| Target | Cases | Standard macro score | 2,048-token macro score | Change (pp) | Standard empty answers | Rerun empty answers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 4K | 26 | 3.85% | 84.62% | +80.77 | 25 | 4 |
| 32K | 26 | 0.00% | 80.77% | +80.77 | 26 | 5 |
| 128K | 26 | 7.69% | 76.92% | +69.23 | 24 | 6 |

In the standard run, 75 of 78 responses hit the output cap without a scorable answer.
With the larger cap, that fell to 15 of 78. Both runs had zero request errors.

## LongBench v2

| Metric | Standard (128 output tokens) | Rerun (2,048 output tokens) |
| --- | ---: | ---: |
| Correct | 0/24 (0.0%) | 4/24 (16.7%) |
| Unparseable | 24 | 17 |
| Unparseable at output cap | 24 | 17 |
| Middle-truncated prompts | 10 | 10 |
| Request errors | 0 | 0 |

| Domain | Standard correct | Rerun correct |
| --- | ---: | ---: |
| Code Repository Understanding | 0/4 | 1/4 |
| Long In-context Learning | 0/4 | 1/4 |
| Long Structured Data Understanding | 0/4 | 0/4 |
| Long-dialogue History Understanding | 0/4 | 1/4 |
| Multi-Document QA | 0/4 | 0/4 |
| Single-Document QA | 0/4 | 1/4 |

These comparisons cover the sampled protocols on this serving configuration. The larger output
cap allows additional reasoning and answer tokens under the same sampling settings.
The [original local τ²-Bench result](2026-11-21-inkling-2-mini-nvfp4-vllm-1spark-262k-capabilities.md) remains available.
