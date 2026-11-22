# Inkling 2 Mini NVFP4 (vLLM, DSpark7, 1 Spark, 262K) · Capability benchmarks

Configuration and serving results are in the [baseline report](2026-11-21-inkling-2-mini-nvfp4-vllm-1spark-262k.md).
The run uses `spark-bench-capability-samples-v1` and the endpoint's default reasoning mode.
A [2,048-token output-cap rerun](2026-11-22-inkling-2-mini-nvfp4-vllm-1spark-262k-context-output-cap-2048.md) compares RULER and LongBench v2 with these original scores.

## RULER v1

3.85% at 4K · 0.00% at 32K · 7.69% at 128K

78 cases across 3 lengths and 13 task variants. 0 request errors. 75 replies had no scorable answer, including 75 that hit the task output cap.

| Target | Macro score | Cases | Requests with errors | Served prompt tokens |
| --- | ---: | ---: | ---: | --- |
| 4K | 3.85% | 26 | 0 | 2,686–4,047 |
| 32K | 0.00% | 26 | 0 | 30,965–32,719 |
| 128K | 7.69% | 26 | 0 | 117,453–131,022 |

Essay corpus SHA-256 `8d31e1b660e0f2180bcca6d238e18f77921df9d158611582b860da1762b6d3dd`.

## LongBench v2

0/24 correct (0.0%)

All 24 responses hit the output cap before giving a parseable answer.
Ten prompts were middle-truncated. There were zero request errors.

Prompt cap 130,816 tokens and output cap 128 tokens.

| Domain | Correct | Cases | Unparseable | Truncated |
| --- | ---: | ---: | ---: | ---: |
| Code Repository Understanding | 0 | 4 | 4 | 2 |
| Long In-context Learning | 0 | 4 | 4 | 1 |
| Long Structured Data Understanding | 0 | 4 | 4 | 2 |
| Long-dialogue History Understanding | 0 | 4 | 4 | 2 |
| Multi-Document QA | 0 | 4 | 4 | 1 |
| Single-Document QA | 0 | 4 | 4 | 2 |

## Local τ²-Bench

6/9 tasks earned full reward

8/9 tasks graded. Same local endpoint for agent, user, and judge. Retail task 100 remained ungraded after both allowed attempts. The assistant reached the 1,024-token cap without returning a usable message, which τ² recorded as an infrastructure error.

This custom local protocol uses mock tools and local judges. Released leaderboard scores use a different setup.

Airline ran in the combined workflow. Retail and telecom were retried with an explicit path to the same pinned τ² source after the initial process could not import it. The original attempts stopped before model requests. The retry reused the same Inkling container, tasks, settings, and budgets.

| Domain | Full reward | Graded | Expected | Mean graded reward | Termination |
| --- | ---: | ---: | ---: | ---: | --- |
| airline | 3 | 3 | 3 | 1.000 | user_stop × 3 |
| retail | 2 | 2 | 3 | 1.000 | user_stop × 2, infrastructure_error × 1 |
| telecom | 1 | 3 | 3 | 0.333 | user_stop × 1, max_steps × 2 |

Coverage status **incomplete**.

- [RULER @ db43f92](https://github.com/NVIDIA/RULER/tree/db43f92ff634bbce1c33d1fb15858aec4bba509a)
- [LongBench @ 2e00731](https://github.com/THUDM/LongBench/tree/2e00731f8d0bff23dc4325161044d0ed8af94c1e)
- [tau2-bench @ 768f3d8](https://github.com/sierra-research/tau2-bench/tree/768f3d8fe8528b4f32a5096f9ed008ae50f48ead)
