# Qwen3.8-Flash-Next NVIDIA NVFP4 on TensorFold · External benchmark pilots

Date 2026-11-21

- RULER v1 macro scores **86.92%** at 4K, **86.15%** at 32K, **86.15%** at 128K across 78 cases.
- LongBench v2 **9/24 (37.5%)** across six domains.
- τ²-Bench **5/9** tasks earned full reward in the custom local pilot.

All three pilots used Qwen3.8-Flash-Next NVIDIA NVFP4 at revision `fc694b5` on the two-Spark TensorFold configuration with tensor parallelism 2 and a 1,048,576-token YaRN window. Requests used TensorFold’s OpenAI-compatible chat endpoint with thinking disabled. [Serving baseline](2026-10-08-qwen38-flash-next-nvfp4-tensorfold-1m.md), [pinned checkpoint](https://huggingface.co/nvidia/Qwen3.8-Flash-Next-NVFP4/tree/fc694b54fb0174e0913e6adf86691ef85a4ead47).

## NVIDIA RULER v1

| Task | 4K | 32K | 128K |
| --- | --- | --- | --- |
| `niah_single_1` | 100.00 | 100.00 | 100.00 |
| `niah_single_2` | 100.00 | 100.00 | 100.00 |
| `niah_single_3` | 100.00 | 100.00 | 100.00 |
| `niah_multikey_1` | 100.00 | 100.00 | 100.00 |
| `niah_multikey_2` | 100.00 | 100.00 | 100.00 |
| `niah_multikey_3` | 100.00 | 100.00 | 100.00 |
| `niah_multivalue` | 100.00 | 100.00 | 100.00 |
| `niah_multiquery` | 100.00 | 100.00 | 100.00 |
| `vt` | 20.00 | 0.00 | 0.00 |
| `cwe` | 10.00 | 70.00 | 70.00 |
| `fwe` | 100.00 | 100.00 | 100.00 |
| `qa_1` | 100.00 | 100.00 | 100.00 |
| `qa_2` | 100.00 | 50.00 | 50.00 |
| **Macro score** | **86.92** | **86.15** | **86.15** |

| Target | Served input tokens | Cases | Request errors | Empty responses |
| --- | --- | --- | --- | --- |
| 4K | 2,023–4,067 | 26 | 0 | 0 |
| 32K | 29,598–32,712 | 26 | 0 | 0 |
| 128K | 115,656–131,022 | 26 | 0 | 0 |

- Ran NVIDIA's original synthetic task generators at seed 42 with two examples per task and length. Used the checkpoint tokenizer and the upstream base prompt, including its answer lead-in, as a single user message. Greedy decoding with the upstream per-task output caps (30–128 tokens).
- Scored with the upstream post-processing and matching functions. Retrieval, tracking, and extraction award credit for the fraction of reference strings found. The two QA tasks award credit for any matching answer alias. Each length averages the scores of all 13 task variants equally.
- Used NVIDIA’s word list and essay downloader, SQuAD v2 dev, and the pinned HotpotQA dev distractor dataset. [NVIDIA/RULER at `db43f92`](https://github.com/NVIDIA/RULER/tree/db43f92ff634bbce1c33d1fb15858aec4bba509a), [HotpotQA snapshot](https://huggingface.co/datasets/namlh2004/hotpotqa/blob/7e54db4656209750ff487f6fdf8e39a66dba136b/hotpot_dev_distractor_v1.json).

## LongBench v2

| Domain | Correct | Middle-truncated |
| --- | --- | --- |
| Code Repository Understanding | 1/4 (25.0%) | 1 |
| Long In-context Learning | 3/4 (75.0%) | 1 |
| Long Structured Data Understanding | 0/4 (0.0%) | 2 |
| Long-dialogue History Understanding | 1/4 (25.0%) | 0 |
| Multi-Document QA | 3/4 (75.0%) | 1 |
| Single-Document QA | 1/4 (25.0%) | 2 |
| **Overall** | **9/24 (37.5%)** | 7 |

| Upstream length bin | Correct |
| --- | --- |
| Short | 6/12 (50.0%) |
| Medium | 1/7 (14.3%) |
| Long | 2/5 (40.0%) |

Request errors 0. Ten responses hit the 128-token output cap before yielding a parseable answer.

- Sampled 24 of 503 questions using seed 42, four per domain. Selected one short/easy, one medium/hard, one long/easy, and one short/hard per domain from rows sorted by ID. Fell back to another difficulty within the same length when the target difficulty was unavailable, and to medium when a domain lacked the target length.
- Used the upstream 0-shot direct-answer template and answer extraction, at temperature 0.1 and a 128-token output cap. For prompts above 130,816 tokens, kept the first and last 65,408 tokens using the served checkpoint's tokenizer. This capped prompt length at roughly 128K while preserving the question and choices. Reported accuracy uses the entire sample as its denominator.
- Source [THUDM/LongBench at `2e00731`](https://github.com/THUDM/LongBench/tree/2e00731f8d0bff23dc4325161044d0ed8af94c1e) and [LongBench v2 data at `2b48e49`](https://huggingface.co/datasets/THUDM/LongBench-v2/tree/2b48e494f2c7a2f0af81aae178e05c7e1dde0fe9).

<details>
<summary>LongBench v2 sample IDs and prompt lengths</summary>

| Dataset ID | Domain | Length | Difficulty | Served input tokens | Middle-truncated |
| --- | --- | --- | --- | --- | --- |
| `66ebdd1c5a08c7b9b35e113b` | Code Repository Understanding | long | easy | 130,828 | Yes |
| `66ebd3ba5a08c7b9b35e0446` | Code Repository Understanding | medium | hard | 123,417 | No |
| `6708a096bb02136c067d1789` | Code Repository Understanding | short | easy | 26,830 | No |
| `66fcfb5fbb02136c067c93ae` | Code Repository Understanding | short | hard | 32,222 | No |
| `66f2b546821e116aacb2b152` | Long In-context Learning | long | easy | 130,828 | Yes |
| `66f118e1821e116aacb26b79` | Long In-context Learning | medium | hard | 64,116 | No |
| `66f68b33bb02136c067c2303` | Long In-context Learning | short | easy | 30,713 | No |
| `66f2aac2821e116aacb2a9de` | Long In-context Learning | short | hard | 16,909 | No |
| `6724cae7bb02136c067d79be` | Long Structured Data Understanding | long | easy | 130,828 | Yes |
| `66f2abc5821e116aacb2aab7` | Long Structured Data Understanding | medium | hard | 130,828 | Yes |
| `66ed2c87821e116aacb1f149` | Long Structured Data Understanding | short | easy | 19,497 | No |
| `67062a63bb02136c067cf5ac` | Long Structured Data Understanding | short | hard | 58,386 | No |
| `67191791bb02136c067d406c` | Long-dialogue History Understanding | medium | easy | 120,703 | No |
| `67189156bb02136c067d3b8d` | Long-dialogue History Understanding | medium | hard | 121,642 | No |
| `671b08c8bb02136c067d4e19` | Long-dialogue History Understanding | short | easy | 28,986 | No |
| `6719bc01bb02136c067d43fa` | Long-dialogue History Understanding | short | hard | 27,559 | No |
| `66f97dc3bb02136c067c56c8` | Multi-Document QA | long | easy | 130,828 | Yes |
| `66f3fb15821e116aacb303dc` | Multi-Document QA | medium | hard | 84,329 | No |
| `66f245cc821e116aacb28698` | Multi-Document QA | short | easy | 10,362 | No |
| `66ec0874821e116aacb194a4` | Multi-Document QA | short | hard | 45,602 | No |
| `67246d0ebb02136c067d75f0` | Single-Document QA | long | easy | 130,828 | Yes |
| `66ee3c7b821e116aacb20f80` | Single-Document QA | medium | hard | 130,828 | Yes |
| `66f53892821e116aacb33225` | Single-Document QA | short | easy | 72,711 | No |
| `66f91f2cbb02136c067c4b1e` | Single-Document QA | short | hard | 12,878 | No |

</details>

## τ²-Bench

| Domain | Full reward | Mean reward | Termination reasons |
| --- | --- | --- | --- |
| Airline | 2/3 | 0.667 | user_stop × 3 |
| Retail | 2/3 | 0.667 | user_stop × 3 |
| Telecom | 1/3 | 0.333 | max_steps × 2, user_stop × 1 |

- Custom English text run with `--benchmark none`. Used the upstream default agent and user-simulator implementations, with Qwen as the agent, simulator, and natural-language assertion judge. Kept the upstream task prompts and reward criteria. Selected three base tasks per domain from ID-sorted rows with an empty `communicate_info` field, using seed 42. Selected the upstream substring communication scorer. The runner recorded no substring checks and used the local natural-language judge for one retail task. One trial per task, 60-step and 420-second caps, temperature 0, and a 1,024-token answer cap per model call.
- The initial telecom attempt had two timeouts and one step-limit stop. The telecom results above use the same three tasks, seed, and limits with the long-context benchmark client paused.
- The released text protocol uses hosted simulator and judge models. This local pilot measures the behavior of the Qwen agent and Qwen simulator together and can include Qwen judging its own responses. Compare it only with runs using the same pilot settings.
- Source [sierra-research/tau2-bench at `768f3d8`](https://github.com/sierra-research/tau2-bench/tree/768f3d8fe8528b4f32a5096f9ed008ae50f48ead) and [upstream benchmark instructions](https://github.com/sierra-research/tau2-bench/blob/768f3d8fe8528b4f32a5096f9ed008ae50f48ead/docs/running-the-benchmark.md).

<details>
<summary>τ²-Bench task IDs and outcomes</summary>

### Airline

- `1` (reward 1, user_stop, DB, COMMUNICATE)
- `17` (reward 0, user_stop, DB, COMMUNICATE)
- `5` (reward 1, user_stop, DB, COMMUNICATE)

### Retail

- `100` (reward 0, user_stop, DB, NL_ASSERTION)
- `113` (reward 1, user_stop, DB, NL_ASSERTION)
- `50` (reward 1, user_stop, DB, NL_ASSERTION)

### Telecom

- `[mms_issue]airplane_mode_on|bad_network_preference|bad_wifi_calling|break_apn_mms_setting|break_app_sms_permission|data_mode_off|data_usage_exceeded|unseat_sim_card|user_abroad_roaming_disabled_on[PERSONA:None]` (reward 0, max_steps)
- `[mms_issue]airplane_mode_on|bad_network_preference|break_apn_mms_setting|break_app_storage_permission[PERSONA:None]` (reward 1, user_stop, ENV_ASSERTION)
- `[mobile_data_issue]data_mode_off|data_usage_exceeded|user_abroad_roaming_disabled_off[PERSONA:Hard]` (reward 0, max_steps)

</details>

These sample sizes provide a first look at context and simulated tool behavior. The full RULER and LongBench suites and the released τ² leaderboard protocol remain unmeasured on this configuration.
