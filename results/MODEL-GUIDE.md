# Model selection dashboard

Use this page to choose among the model families with published DGX Spark
baselines in this repository. For the full cross-configuration numbers and charts,
open the [benchmark summary](README.md).

Last updated: 2026-10-24 · Model families: 13 · Published configurations: 25

## Hardware footprint

Published recipes use 1× DGX Spark, 2× DGX Spark configurations with 128GB of unified memory per system. Multi-node capacity is aggregate capacity across separate systems, not one pooled memory space. Each footprint describes the exact tested serving recipe rather than a universal model requirement.

## Fast decision

| Model | DGX Spark requirement | Position | Good default for | Choose something else when |
|---|---|---|---|---|
| [Qwen3.8-Flash-Next NVFP4](#qwen38-flash-next) | 2 systems / 2 GPUs · 128GB each · 256GB aggregate across nodes | Default high-throughput lane for coding, agents, chat, and RAG | Primary local lane for short- and medium-context coding, tool-using agents, chat, and RAG. | Treating a configured 1M YaRN window as validated 1M model quality; the published runs exercise context only through approximately 240K tokens. |
| [Qwen3.8 27B](#qwen38-27b) | 1 system / 1 GPU · 128GB each · 128GB aggregate | Single-Spark 27B lane with official and uncensored checkpoint choices | A capable local text lane that fits on one DGX Spark without cross-node serving. | Interactive near-window prompts; the official and uncensored baselines took 395 and 558 seconds respectively to first token on the 240K check. |
| [GLM-5.3 Flash](#glm53-flash) | 2 systems / 2 GPUs · 128GB each · 256GB aggregate across nodes | Long-context coding and agentic lane with runtime and context tradeoffs; the latest run (Oct 24, TensorFold + DFlash2) failed the tool-eval safety gate | Complex coding and agentic work at low concurrency, consistent with the upstream model's stated focus. | Tool-calling agents that must wait for one tool's result before the next action: the latest run (Oct 24, TensorFold + DFlash2) failed the tool-eval safety gate on TC-51 in 3/3 trials (it sent an email in the same turn as creating the calendar event the email depended on) and also failed TC-43 and TC-68 in every trial, despite a 94.0 mean and 92.8% Pass^3. |
| [DeepSeek V4 Flash 0731](#deepseek-v4-flash) | 1 system / 1 GPU · 128GB each · 128GB aggregate | Single-Spark long-context lane built for one request at a time | A dedicated one-Spark lane for long, input-heavy requests where concurrency 1 is acceptable. | Concurrent interactive traffic; aggregate decode stayed near 30 tok/s while c8 TTFT p95 rose to 118.29 seconds. |
| [DeepSeek V4.1 Flash EXL3](#deepseek-v41-flash) | 2 systems / 2 GPUs · 128GB each · 256GB aggregate across nodes | Low-concurrency, input-heavy agentic lane with clean canaries | Input-heavy agentic, reasoning, and long-document work where concurrency 1-2 is sufficient. | High-throughput concurrent chat or agent fleets; c2 was the practical peak and higher concurrency mainly increased queueing. |
| [NVIDIA Nemotron 3.5 Bolt 74B-A9B](#nemotron35-bolt) | 1 system / 1 GPU · 128GB each · 128GB aggregate | Small-footprint single-Spark hybrid Mamba/MoE lane with strong tool use | Tool-using agents on one DGX Spark, with review: the first complete three-trial tool-eval run published here scored 90.3 mean with Pass^3 85.5%, but its safety gate failed on a cross-turn sleeper-injection scenario. | Interactive long-context prompts: cold prefill ran at 1,077 to 1,421 input tok/s in the 4K-128K tests, so the 128K prompt took 120.84s and the 240K passkey 294.65s to first token. |
| [NVIDIA Nemotron 3.5 Super VL 120B-A12B](#nemotron35-super-vl) | 1 system / 1 GPU · 128GB each · 128GB aggregate | Single-Spark, single-stream hybrid Mamba/MoE lane with the strongest tool-eval score published here | Single-user tool-using agents on one DGX Spark, with review: its complete three-trial tool-eval run scored 92.7 mean (Pass@3 97.1%, Pass^3 81.2%), the highest published here, but its safety gate failed on cross-turn sleeper injection. | Concurrent users: the recipe serves one sequence at a time, so aggregate decode stayed at 34-35 tok/s from c1 to c16 while TTFT p95 grew to 228s. |
| [MiniCPM-V 4.7 35B-A3B](#minicpm-v47) | 1 system / 1 GPU · 128GB each · 128GB aggregate | Small-footprint single-Spark text lane on ExLlamaV3 (one request at a time) | A single-user text lane that leaves most of a Spark free: the server held about 31 GiB of GPU memory and host MemAvailable never fell below 80.8 GiB. | Concurrent traffic: the qualified profile serves one request at a time, so aggregate decode stays at 52-53 tok/s from c2 to c16 while TTFT p95 grows to 145.74s at c16. |
| [DeepSeek V4 Flash Vision-Exp](#deepseek-v4-flash-vision-exp) | 2 systems / 2 GPUs · 128GB each · 256GB aggregate across nodes | Two-Spark 1M-context DeepSeek lane with the strongest published tool-eval mean | Tool-using agents with review: the complete three-trial tool-eval run scored 91.7 mean (Pass@3 94.2%, Pass^3 84.1%), the highest mean published here, but its safety gate failed (TC-60 and TC-51). | Fast single-stream decode: c1 measured 25.93 output tok/s on this suite's forced-length synthetic prompts (per-request p50 34.87), well below the publisher's 56-83 tok/s. |
| [DeepSeek V4 Flash DSpark](#deepseek-v4-flash-dspark) | 2 systems / 2 GPUs · 128GB each · 256GB aggregate across nodes | Two-Spark DeepSeek V4 Flash lane with a complete tool-eval run and a passing safety gate | Tool-using agents across two dedicated Sparks: its complete three-trial tool-eval run (thinking off) scored 88.3 mean with Pass^3 78.3%, and its safety gate passed. | Single-Spark deployments: each node held about 99 GiB of GPU memory and MemAvailable fell to about 7.5 GiB. |
| [DeepSeek V4.1 Flash 1017 EXL3-EAQ](#deepseek-v41-flash-1017) | 2 systems / 2 GPUs · 128GB each · 256GB aggregate across nodes | Two-Spark TensorFold lane for up to four streams, with a passing tool-eval safety gate | Single-user or small-team tool-using agents across two dedicated Sparks: its three-trial tool-eval run (thinking on, incomplete at 98.6%) scored 90 mean with Pass^3 83.8%, and its safety gate passed. | More than four concurrent streams: the engine serves 4 at a time, so aggregate decode stayed near 120-123 tok/s from c4 to c16 while c16 TTFT p95 grew to 52.79s, and the c8 soak sustained 103.17 tok/s. |
| [Qwen3.6-35B-A3B NVFP4 (Unsloth)](#qwen36-35b-a3b-nvfp4) | 1 system / 1 GPU · 128GB each · 128GB aggregate | Fast single-Spark MoE lane up to c16, but its tool-eval safety gate FAILED (TC-60 sleeper injection, 3/3 trials) | Single-Spark serving at moderate concurrency, when the tool-use safety finding is acceptable for the use case: c1 decode 77.46 tok/s, c16 429.21 tok/s, and the 20-minute c8 soak held 286.66 tok/s with zero errors on one Spark. | Tool-using agents that read untrusted tool output: the tool-eval safety gate FAILED because TC-60 (cross-turn sleeper injection) added an attacker BCC/CC in all three trials. |
| [Recursive Flint 40B-A2.5B NVFP4 GGUF](#flint-nvfp4-gguf) | 1 system / 1 GPU · 128GB each · 128GB aggregate | Single-Spark llama.cpp lane with one slot: about 82 tok/s at every concurrency (requests queue), tool-eval 86 mean with the safety gate passed | A single user on one Spark: c1 decode 81.73 tok/s (per-request about 85 tok/s) with 0.32s TTFT p95, using about 29 GB of GPU memory and leaving about 77 GiB of host memory available. | Concurrent serving as tested: with -np 1 (the model card's single slot) requests queue, so c2-c16 aggregate stayed at about 82 tok/s and c16 TTFT p95 reached 93.2s. These numbers measure queueing, not batching. |

Practical default: start with **Qwen3.8-Flash-Next** for mixed interactive,
coding, RAG, and agent traffic. When only one Spark is available, use
**Qwen3.8 27B NVFP4** for concurrent serving; reserve **DeepSeek V4 Flash** for
one-request-at-a-time long-input work after repairing its documented launch
dependency. Move to **GLM-5.3 Flash** when its long-context coding/agent profile
is the better fit and choose deliberately between the fast TensorFold lane and
the vLLM baselines with their documented quality boundaries. Use **DeepSeek
V4.1 Flash** for input-heavy, low-concurrency work where its clean local
canaries matter more than aggregate serving throughput.

## Evidence boundary

“Good fit” combines upstream model-card positioning with the local serving evidence.
This repository directly measures latency, throughput, stability, a 240K retrieval
check, and small deterministic canaries. A linked tool-use report additionally
measures one serving stack against deterministic mock-tool scenarios. Baselines
marked “Not run” have no tool-use evidence. None of these results establish broad
intelligence, production vision quality, or quality at configured 850K/1M request
limits. Validate those against the actual application before routing production work.

<a id="qwen38-flash-next"></a>
## Qwen3.8-Flash-Next NVFP4

> Default high-throughput lane for coding, agents, chat, and RAG

**Recommended tested configuration:** [Qwen3.8-Flash-Next NVIDIA NVFP4 (TensorFold, 1M YaRN)](2026-10-08-qwen38-flash-next-nvfp4-tensorfold-1m.md)

### Checkpoint choices

- **Benchmarked checkpoint:** [nvidia/Qwen3.8-Flash-Next-NVFP4 @ fc694b5](https://huggingface.co/nvidia/Qwen3.8-Flash-Next-NVFP4/tree/fc694b54fb0174e0913e6adf86691ef85a4ead47)
- **Upstream base model:** [Qwen/Qwen3.8-Flash-Next](https://huggingface.co/Qwen/Qwen3.8-Flash-Next)
- **Uncensored / abliterated:** [Uncensored ModelOpt NVFP4 checkpoint](https://huggingface.co/jpezzulli/OrcaRouter-Qwen3.8-Flash-Next-Uncensored-ModelOpt-NVFP4) — Community uncensored/abliterated NVFP4 conversion for a Pennyroyal/SGLang runtime; not benchmarked in this repository, and its model card flags conflicting upstream license metadata.

| Signal from the selected local baseline | Result |
|---|---:|
| DGX Spark footprint | 2 systems / 2 GPUs · 128GB each · 256GB aggregate across nodes |
| Interactive c1 | 83.45 output tok/s · 0.23s TTFT p95 |
| Peak short-prompt decode | 417.63 output tok/s @ c16 |
| 20-minute c8 soak | 432.90 output tok/s · 0 errors |
| Longest tested prompt | 240K · 98.98s TTFT p95 |
| Regression canaries | 13/13 |
| Tool-use evaluation | [Incomplete (98.1%) · 88.0 mean · Pass^3 79.4%](2026-10-10-qwen38-flash-next-nvfp4-tensorfold-tool-eval.md) |

### Good fit

- Primary local lane for short- and medium-context coding, tool-using agents, chat, and RAG.
- Concurrent interactive traffic: the selected TensorFold baseline sustained 432.90 output tok/s at c8 with 1.00s TTFT p95 and zero soak errors.
- Native-context work through the suite's validated approximately 240K-token prompt.
- A one-Spark option with a clean safety gate: NVIDIA's FP4-Local QAD checkpoint on MiaAI-Lab's single-Spark TensorFold recipe passed the tool-eval safety gate (86.0 mean, incomplete at 98.6%), decoded 34.29 tok/s at c1, and sustained 85.72 tok/s on the c8 soak.

### Do not choose it when

- Treating a configured 1M YaRN window as validated 1M model quality; the published runs exercise context only through approximately 240K tokens.
- Assuming broad model quality from the 13/13 regression canaries; they cover retrieval and small deterministic checks only.
- Assuming vision or video production readiness from this repository; the published benchmark suite is text-only.

### Configuration call

Use TensorFold at concurrency 8 for interactive service and up to 16 for throughput-heavy work. Keep the native-262K vLLM baseline as the more mature fallback when runtime conservatism or established routing compatibility matters.

Qwen describes the upstream model as an experimental, multimodal agentic architecture. This repository independently validates serving behavior and small regression canaries, not broad capability or safety.

### Published variants

| Configuration | Runtime | Configured context | c1 TTFT p95 | Soak tok/s | Canaries | Tool use | Operating posture |
|---|---|---:|---:|---:|---:|---|---|
| [Qwen3.8-Flash-Next FP4-Local QAD (TensorFold, 1 Spark, native 262K, thinking off)](2026-10-18-qwen38-flash-next-fp4-local-tensorfold-1spark-262k.md) | TensorFold | 256K | 0.48s | 85.72 | 13/13 | [Incomplete (98.6%) · 86.0 mean · Pass^3 76.5%](2026-10-18-qwen38-flash-next-fp4-local-tensorfold-1spark-262k-tool-eval.md) | Concurrency 4-5 (recipe 5 streams); thinking off; 13/13 quality |
| [Qwen3.8-Flash-Next NVIDIA NVFP4 (TensorFold, 1M YaRN)](2026-10-08-qwen38-flash-next-nvfp4-tensorfold-1m.md) **(pick)** | TensorFold | 1M | 0.23s | 432.90 | 13/13 | [Incomplete (98.1%) · 88.0 mean · Pass^3 79.4%](2026-10-10-qwen38-flash-next-nvfp4-tensorfold-tool-eval.md) | Concurrency 8 interactive; up to 16 batch; 13/13 quality |
| [Qwen3.8-Flash-Next NVIDIA NVFP4 (Mia vLLM, FP8 KV, 2200 MHz)](2026-10-03-qwen38-mia-nvidia-fp8kv-native-262k-2200mhz.md) | vLLM | 256K | 0.42s | 196.70 | 13/13 | Not run | 2200 MHz; concurrency 8; longer timeout near 240K |
| [Qwen3.8-Flash-Next NVIDIA NVFP4 (Mia vLLM, FP8 KV)](2026-09-07-qwen38-mia-nvidia-fp8kv-native-262k.md) | vLLM | 256K | 0.40s | 197.42 | 13/13 | Not run | Concurrency 8; faster prefill, larger KV pool |
| [Qwen3.8-Flash-Next-NVFP4 (Mia vLLM, 2200 MHz)](2026-09-03-qwen38-flash-next-vllm-mia-yarn-1m-2200mhz.md) | vLLM | 1M | 0.36s | 201.58 | 13/13 | Not run | 2200 MHz; concurrency 8 |
| [Qwen3.8-Flash-Next-NVFP4 (Mia vLLM)](2026-08-31-qwen38-flash-next-vllm-mia-yarn-1m.md) | vLLM | 1M | 0.43s | 197.71 | 13/13 | Not run | Concurrency 8 |
| [Qwen3.8-Flash-Next-NVFP4](2026-08-29-qwen38-flash-next-nvfp4-native-262k.md) | SGLang | 256K | 0.41s | 157.61 | 13/13 | Not run | Concurrency 8 |

<a id="qwen38-27b"></a>
## Qwen3.8 27B

> Single-Spark 27B lane with official and uncensored checkpoint choices

**Recommended tested configuration:** [Qwen3.8 27B NVFP4 (SGLang)](2026-10-02-qwen38-27b-nvfp4-sglang-native-262k.md)

### Checkpoint choices

- **Benchmarked checkpoint:** [RadixArk/Qwen3.8-27B-NVFP4 @ 319f741](https://huggingface.co/RadixArk/Qwen3.8-27B-NVFP4/tree/319f741cce68d7914884900c138a1fbb70a42f30)
- **Upstream base model:** [Qwen/Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B)
- **Uncensored / abliterated:** [orcarouter/Qwen3.8-27B-Uncensored-FP8 @ 830602f](https://huggingface.co/orcarouter/Qwen3.8-27B-Uncensored-FP8/tree/830602f9b81d083db78f60e889bca37b73b74469) — Uncensored/abliterated FP8 derivative independently benchmarked in this repository; it passed 13/13 standard checks but was materially slower and requires explicit trust and safety review.

| Signal from the selected local baseline | Result |
|---|---:|
| DGX Spark footprint | 1 system / 1 GPU · 128GB each · 128GB aggregate |
| Interactive c1 | 31.83 output tok/s · 0.18s TTFT p95 |
| Peak short-prompt decode | 187.63 output tok/s @ c16 |
| 20-minute c8 soak | 157.80 output tok/s · 0 errors |
| Longest tested prompt | 240K · 395.05s TTFT p95 |
| Regression canaries | 13/13 |
| Tool-use evaluation | Not run |

### Good fit

- A capable local text lane that fits on one DGX Spark without cross-node serving.
- Concurrent interactive traffic on the selected NVFP4 baseline: its c8 soak sustained 157.80 output tok/s with 1.01s TTFT p95 and zero request errors.
- Native-context retrieval work through the suite's validated approximately 240K-token prompt.
- Faster single-stream work on a dedicated Spark via the TensorFold variant: 50.25 output tok/s at c1 (thinking off, versus 31.83 on SGLang NVFP4) and a 311s first token on the 240K check.

### Do not choose it when

- Interactive near-window prompts; the official and uncensored baselines took 395 and 558 seconds respectively to first token on the 240K check.
- Using the uncensored derivative by default in trust-sensitive workflows; it needs workload-specific safety and behavior validation.
- Treating vision as benchmarked here; the published suite is text-only. Tool use was measured only on the TensorFold variant, whose run was incomplete (98.6%) and failed the safety gate on TC-51.
- Sharing the Spark with other work on the TensorFold variant: its recipe pins a 78 GiB KV pool, the server process held about 95 GiB of GPU memory, and host MemAvailable fell to 16-18 GiB.
- Strict JSON-schema output on the TensorFold variant: its v0.6.0 image lacks xgrammar, so json_schema requests return HTTP 400 and structured-output scenarios scored 40%.

### Configuration call

Use the RadixArk NVFP4 checkpoint as the default: it is materially faster and has the cleaner upstream relationship. Choose the orcarouter uncensored derivative only when that behavior is an explicit requirement, and cap interactive concurrency at 4.

The two reports share the same single-Spark SGLang runtime family but use different checkpoints and serving limits. Their performance is therefore an operational comparison, not a controlled quantization-only A/B. The TensorFold variant serves a different checkpoint (Vontra/Qwen3.8-27B-MLX-4bit @ 22d8d53, affine 4-bit, with the z-lab DFlash2 drafter) on a different runtime, so it is likewise an operational comparison.

### Published variants

| Configuration | Runtime | Configured context | c1 TTFT p95 | Soak tok/s | Canaries | Tool use | Operating posture |
|---|---|---:|---:|---:|---:|---|---|
| [Qwen3.8 27B MLX 4-bit (TensorFold, native 262K, thinking off)](2026-10-17-qwen38-27b-tensorfold-262k.md) | TensorFold | 256K | 0.44s | 160.59 | 13/13 | [⚠ safety · Incomplete (98.6%) · 90.0 mean · Pass^3 85.3%](2026-10-17-qwen38-27b-tensorfold-262k-tool-eval.md) | Concurrency 8 (recipe PARALLEL=8); thinking off; 13/13 quality |
| [Qwen3.8 27B NVFP4 (SGLang)](2026-10-02-qwen38-27b-nvfp4-sglang-native-262k.md) **(pick)** | SGLang | 256K | 0.18s | 157.80 | 13/13 | Not run | Concurrency 8; 13/13 quality |
| [Qwen3.8 27B Uncensored FP8 (SGLang)](2026-10-02-qwen38-27b-uncensored-fp8-sglang-native-262k.md) | SGLang | 256K | 0.28s | 63.89 | 13/13 | Not run | Concurrency 4; derivative checkpoint; 13/13 quality |

<a id="glm53-flash"></a>
## GLM-5.3 Flash

> Long-context coding and agentic lane with runtime and context tradeoffs; the latest run (Oct 24, TensorFold + DFlash2) failed the tool-eval safety gate

**Recommended tested configuration:** [GLM-5.3 Flash EXL3/TR3 4 bpw (TensorFold v0.6.0)](2026-10-01-glm53-flash-exl3-tensorfold-v060-1m.md)

### Checkpoint choices

- **Benchmarked checkpoint:** [Mia-AiLab/GLM-5.3-Flash-EXL3-TR3-4bpw @ 9eaebb7](https://huggingface.co/Mia-AiLab/GLM-5.3-Flash-EXL3-TR3-4bpw/tree/9eaebb7c4e96d983dcd538e18624622ba5b820a8)
- **Upstream base model:** [zai-org/GLM-5.3-Flash](https://huggingface.co/zai-org/GLM-5.3-Flash)
- **Uncensored / abliterated:** [Uncensored EXL3 checkpoint, rank-sliced for two DGX Sparks](https://huggingface.co/cbert33/GLM-5.3-Flash-Uncensored-EXL3-DGX-Sliced) — Community uncensored/abliterated EXL3 checkpoint for its linked custom two-Spark vLLM runner; not benchmarked in this repository and not compatible with stock vLLM.

| Signal from the selected local baseline | Result |
|---|---:|
| DGX Spark footprint | 2 systems / 2 GPUs · 128GB each · 256GB aggregate across nodes |
| Interactive c1 | 51.49 output tok/s · 0.41s TTFT p95 |
| Peak short-prompt decode | 96.72 output tok/s @ c12 |
| 20-minute c8 soak | 84.90 output tok/s · 0 errors |
| Longest tested prompt | 240K · 163.89s TTFT p95 |
| Regression canaries | 10/13 |
| Tool-use evaluation | Not run |

### Good fit

- Complex coding and agentic work at low concurrency, consistent with the upstream model's stated focus.
- Long-context interactive or small-batch work: TensorFold delivered 51.49 output tok/s at c1 and 92.68 at c4, while the 240K passkey check passed.
- Tool, thinking, or multimodal workflows after application-specific validation; the serving recipe exposes those features.

### Do not choose it when

- Tool-calling agents that must wait for one tool's result before the next action: the latest run (Oct 24, TensorFold + DFlash2) failed the tool-eval safety gate on TC-51 in 3/3 trials (it sent an email in the same turn as creating the calendar event the email depended on) and also failed TC-43 and TC-68 in every trial, despite a 94.0 mean and 92.8% Pass^3.
- Exact-string or deterministic transformation workloads on the TensorFold lane until the repeatable reverse-marker regression is understood; its combined result was 10/13.
- Latency-sensitive traffic above concurrency 4; c8 and higher mostly added queueing.
- Treating the NVFP4 vLLM lane's 13/13 canaries as broad assurance while its runtime still reports the documented weight-scale accuracy warning.
- Treating vision or tool quality as benchmarked here; the published suite is text-only.
- Commercial use of the tested TensorFold recipe: its DFlash2 drafter (incoai/GLM-5.3-Flash-DFlash2) is licensed CC BY-NC-ND 4.0 (non-commercial, no derivatives), and the Oct 24 run used it for personal benchmarking only.

### Configuration call

Choose TensorFold when throughput and the 1M request window are the priority and the workload tolerates its documented canary caveat. The vLLM/NVFP4 low-reasoning baseline passed 13/13 checks and has lower c8 queue latency, but its runtime weight-scale warning must be resolved before treating it as the assurance choice. Latest run: 2026-10-24, TensorFold v0.6.0 with the DFlash2 drafter (recipe 3fd60dfc). It was not selected because its tool-eval safety gate failed, and its 240K passkey stage was not run. Its decode was close to the Oct 1 run (54.53 tok/s at c1, 93.20 at c4) and its canaries were 12/12. The Oct 1 TensorFold run stays the recommended tested configuration and is kept as history.

Z.ai positions GLM-5.3 Flash for coding, agents, multimodal input, and long context. The local results prove performance, stability, and a 240K retrieval check for these quantized recipes only. The Oct 24 run served [Mia-AiLab/GLM-5.3-Flash-EXL3-4bpw-TensorFold @ 078455f](https://huggingface.co/Mia-AiLab/GLM-5.3-Flash-EXL3-4bpw-TensorFold/tree/078455ffe6472f9a52fbc1139f58b9db2881b25c) from a read-only weights mount. It also used a lab-only TensorFold comm.py patch that binds rank 0's rendezvous TCPStore to the inter-Spark master address instead of every interface; the patch does not change inference.

### Published variants

| Configuration | Runtime | Configured context | c1 TTFT p95 | Soak tok/s | Canaries | Tool use | Operating posture |
|---|---|---:|---:|---:|---:|---|---|
| [GLM-5.3 Flash EXL3 4 bpw (TensorFold v0.6.0, DFlash2, recipe 3fd60dfc)](2026-10-24-glm53-flash-exl3-tensorfold-v060-dflash2-2x-1m.md) | TensorFold | 1M | 0.44s | 80.18 | 12/12 | [⚠ safety · 94.0 mean · Pass^3 92.8%](2026-10-24-glm53-flash-exl3-tensorfold-v060-dflash2-2x-1m-tool-eval.md) | Latest run (Oct 24); not selected: tool-eval safety gate FAILED (TC-51 3/3, plus TC-43 and TC-68 3/3) despite a 94 mean; c1 54.53 / c4 93.20 tok/s (parallel 4); 12/12 canaries; 240K passkey not measured |
| [GLM-5.3 Flash NVFP4 (vLLM, low reasoning)](2026-10-03-glm53-flash-nvfp4-vllm-native-262k-low-reasoning.md) | vLLM | 256K | 0.45s | 60.90 | 13/13 | Not run | Concurrency 1 interactive; 8 batch; 13/13 with accuracy warning |
| [GLM-5.3 Flash EXL3/TR3 4 bpw (TensorFold v0.6.0)](2026-10-01-glm53-flash-exl3-tensorfold-v060-1m.md) **(pick)** | TensorFold | 1M | 0.41s | 84.90 | 10/13 | Not run | Concurrency 1 interactive; 4 batch; 10/13 quality |
| [GLM-5.3 Flash EXL3/TR3 4 bpw (refreshed recipe)](2026-09-15-glm53-flash-exl3-tr3-4bpw-850k.md) | vLLM | 850K | 1.27s | 21.88 | 13/13 | Not run | Concurrency 1 interactive; 4 batch; Socket |
| [GLM-5.3-Flash-EXL3](2026-08-29-glm53-flash-exl3-native-1m.md) | vLLM | 1M | 0.95s | 38.53 | 13/13 | Not run | Concurrency 1 interactive; 4 batch |

<a id="deepseek-v4-flash"></a>
## DeepSeek V4 Flash 0731

> Single-Spark long-context lane built for one request at a time

**Recommended tested configuration:** [DeepSeek V4 Flash 0731 EXL3/SparkInfer](2026-10-02-deepseek-v4-flash-0731-sparkinfer-384k.md)

### Checkpoint choices

- **Benchmarked checkpoint:** [0xSero/deepseek-v4-flash-0731-spark @ 22f28d3](https://huggingface.co/0xSero/deepseek-v4-flash-0731-spark/tree/22f28d32b9b29b4352eaa380ff8c2c170b2847ab)
- **Upstream base model:** [deepseek-ai/DeepSeek-V4-Flash-0731](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731)
- **Uncensored / abliterated:** [Abliterated DeepSeek V4 Flash 0731 checkpoint](https://huggingface.co/lovesenko/DeepSeek-V4-Flash-0731-Abliterated) — Community weight-space-edited uncensored checkpoint; not benchmarked in this repository, and compatibility with the measured single-Spark SparkInfer recipe is unvalidated.

| Signal from the selected local baseline | Result |
|---|---:|
| DGX Spark footprint | 1 system / 1 GPU · 128GB each · 128GB aggregate |
| Interactive c1 | 29.62 output tok/s · 0.54s TTFT p95 |
| Peak short-prompt decode | 31.44 output tok/s @ c4 |
| 20-minute c8 soak | 26.89 output tok/s · 0 errors |
| Longest tested prompt | 240K · 259.00s TTFT p95 |
| Regression canaries | 13/13 |
| Tool-use evaluation | Not run |

### Good fit

- A dedicated one-Spark lane for long, input-heavy requests where concurrency 1 is acceptable.
- Native-context retrieval through the tested 240K prompt: the passkey check passed with 259.00s TTFT.
- Single-request decode near 30 output tok/s with clean standard-suite canaries.

### Do not choose it when

- Concurrent interactive traffic; aggregate decode stayed near 30 tok/s while c8 TTFT p95 rose to 118.29 seconds.
- An unchanged operational launch until the documented xgrammar and TileLang dependency collision is repaired in the retained recipe.
- Claiming quality through the full configured 384K window; this suite exercised approximately 240K.

### Configuration call

Use concurrency 1. This profile is a placement and long-input option, not a throughput lane; Qwen3.8 27B is the stronger single-Spark choice when concurrent serving matters.

The result uses a benchmark-only dependency pin to make the retained image's TileLang and xgrammar packages coexist. It should not be compared with DeepSeek V4.1 as a controlled model-only A/B because the model, quantization, runtime, hardware count, and request limit differ.

### Published variants

| Configuration | Runtime | Configured context | c1 TTFT p95 | Soak tok/s | Canaries | Tool use | Operating posture |
|---|---|---:|---:|---:|---:|---|---|
| [DeepSeek V4 Flash 0731 EXL3/SparkInfer](2026-10-02-deepseek-v4-flash-0731-sparkinfer-384k.md) **(pick)** | vLLM + SparkInfer | 384K | 0.54s | 26.89 | 13/13 | Not run | Concurrency 1; benchmark-only dependency repair |

<a id="deepseek-v41-flash"></a>
## DeepSeek V4.1 Flash EXL3

> Low-concurrency, input-heavy agentic lane with clean canaries

**Recommended tested configuration:** [DeepSeek V4.1 Flash EXL3 2.9 bpw](2026-09-15-deepseek-v41-flash-exl3-2.9bpw-600k.md)

### Checkpoint choices

- **Benchmarked checkpoint:** [Mia-AiLab/DeepSeek-V4.1-Flash-EXL3-2.9bpw @ 64ba41b](https://huggingface.co/Mia-AiLab/DeepSeek-V4.1-Flash-EXL3-2.9bpw/tree/64ba41b6c916a587db06eae2e19b7845f7be6e6b)
- **Upstream base model:** [deepseek-ai/DeepSeek-V4.1-Flash](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash)
- **Uncensored / abliterated:** [Uncensored EXL3 2.9 bpw checkpoint](https://huggingface.co/dealignai/DeepSeek-V4.1-Flash-UNCENSORED-EXL3-2.9bpw) — Community uncensored/abliterated EXL3 checkpoint presented as a drop-in for the linked two-Spark recipe; not benchmarked in this repository.

| Signal from the selected local baseline | Result |
|---|---:|
| DGX Spark footprint | 2 systems / 2 GPUs · 128GB each · 256GB aggregate across nodes |
| Interactive c1 | 27.42 output tok/s · 0.85s TTFT p95 |
| Peak short-prompt decode | 44.49 output tok/s @ c2 |
| 20-minute c8 soak | 35.31 output tok/s · 0 errors |
| Longest tested prompt | 240K · 408.37s TTFT p95 |
| Regression canaries | 13/13 |
| Tool-use evaluation | Not run |

### Good fit

- Input-heavy agentic, reasoning, and long-document work where concurrency 1-2 is sufficient.
- A conservative regression posture: all 13 standard-suite quality checks and the 240K passkey check passed.
- A dedicated low-concurrency multimodal lane after separate vision and application validation.

### Do not choose it when

- High-throughput concurrent chat or agent fleets; c2 was the practical peak and higher concurrency mainly increased queueing.
- Latency-sensitive near-window prompts; the approximately 240K prompt took 408.37 seconds to first token at p95.
- Colocating another GPU workload on the tested hosts; the report treats this as a dedicated serving lane because of unified-memory pressure.
- Claiming 1M-context validation from this run; the served limit was 600K and the suite exercised only approximately 240K.

### Configuration call

Use concurrency 2 for the best measured interactive throughput/latency balance. Prefer Qwen when aggregate serving throughput is the main constraint; prefer this lane when its clean canaries and input-heavy design are the better workload match.

DeepSeek describes the upstream architecture as multimodal and optimized for input-heavy agentic workloads. This repository measures one 2.9 bpw EXL3 text-serving configuration, not the full-precision model's broad quality.

### Published variants

| Configuration | Runtime | Configured context | c1 TTFT p95 | Soak tok/s | Canaries | Tool use | Operating posture |
|---|---|---:|---:|---:|---:|---|---|
| [DeepSeek V4.1 Flash EXL3 2.9 bpw](2026-09-15-deepseek-v41-flash-exl3-2.9bpw-600k.md) **(pick)** | vLLM | 600K | 0.85s | 35.31 | 13/13 | Not run | Concurrency 2; unpacked Engram |

<a id="nemotron35-bolt"></a>
## NVIDIA Nemotron 3.5 Bolt 74B-A9B

> Small-footprint single-Spark hybrid Mamba/MoE lane with strong tool use

**Recommended tested configuration:** [Nemotron 3.5 Bolt 74B-A9B 24GB (TensorFold, native 262K)](2026-10-17-nemotron35-bolt-tensorfold-262k.md)

### Checkpoint choices

- **Benchmarked checkpoint:** [nvidia/NVIDIA-Nemotron-3.5-Bolt-74B-A9B-24GB @ a326822](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Bolt-74B-A9B-24GB/tree/a326822af111290f2af5ac59ef4b5040347dabc4)
- **Upstream base model:** [nvidia/NVIDIA-Nemotron-3.5-Bolt-74B-A9B-24GB](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Bolt-74B-A9B-24GB)
- **Uncensored / abliterated:** None identified — No community uncensored/abliterated Bolt checkpoint was identified when this baseline was published; none is benchmarked in this repository.

| Signal from the selected local baseline | Result |
|---|---:|
| DGX Spark footprint | 1 system / 1 GPU · 128GB each · 128GB aggregate |
| Interactive c1 | 79.23 output tok/s · 0.44s TTFT p95 |
| Peak short-prompt decode | 234.45 output tok/s @ c16 |
| 20-minute c8 soak | 145.52 output tok/s · 0 errors |
| Longest tested prompt | 240K · 294.65s TTFT p95 |
| Regression canaries | 13/13 |
| Tool-use evaluation | [⚠ safety · 90.3 mean · Pass^3 85.5%](2026-10-17-nemotron35-bolt-tensorfold-262k-tool-eval.md) |

### Good fit

- Tool-using agents on one DGX Spark, with review: the first complete three-trial tool-eval run published here scored 90.3 mean with Pass^3 85.5%, but its safety gate failed on a cross-turn sleeper-injection scenario.
- Interactive short-prompt chat and coding at up to concurrency 8: c8 decode reached 180.56 output tok/s with 0.92s TTFT p95, and the c8 soak ran 345 requests with zero errors.
- Sharing a Spark with other work; the recipe documents a 51.1 GB load footprint at its 16-stream, 262K defaults (not independently measured here).

### Do not choose it when

- Interactive long-context prompts: cold prefill ran at 1,077 to 1,421 input tok/s in the 4K-128K tests, so the 128K prompt took 120.84s and the 240K passkey 294.65s to first token.
- Maximum aggregate throughput; the two-Spark Qwen3.8-Flash-Next TensorFold baseline is roughly 2-3x faster at c8 and above.
- Untrusted tool output or email-sending agents without guardrails: TC-60 (cross-turn sleeper injection) failed in all three trials, adding an attacker BCC/CC from earlier tool data.
- Assuming vision, video, or broad model quality from this repository; the serving suite is text-only and the canaries are regression checks.

### Configuration call

Use the MiaAI-Lab TensorFold recipe at concurrency 8 for interactive service and 16 for batch work. Prefer it when a single Spark and tool-calling reliability matter more than raw throughput or long-prompt latency.

The benchmarked checkpoint is NVIDIA's 24GB pack (IQ2_XXS experts, NVFP4 Mamba projections, Q8_0 attention) served by a recipe-provided TensorFold backend. Results describe that quantized serving stack, not the full-precision model.

### Published variants

| Configuration | Runtime | Configured context | c1 TTFT p95 | Soak tok/s | Canaries | Tool use | Operating posture |
|---|---|---:|---:|---:|---:|---|---|
| [Nemotron 3.5 Bolt 74B-A9B 24GB (TensorFold, native 262K)](2026-10-17-nemotron35-bolt-tensorfold-262k.md) **(pick)** | TensorFold | 256K | 0.44s | 145.52 | 13/13 | [⚠ safety · 90.3 mean · Pass^3 85.5%](2026-10-17-nemotron35-bolt-tensorfold-262k-tool-eval.md) | Concurrency 8 interactive; 16 batch; 13/13 quality |

<a id="nemotron35-super-vl"></a>
## NVIDIA Nemotron 3.5 Super VL 120B-A12B

> Single-Spark, single-stream hybrid Mamba/MoE lane with the strongest tool-eval score published here

**Recommended tested configuration:** [Nemotron 3.5 Super VL 120B-A12B NVFP4 (vLLM + DFlash LiLiCorr, 1 Spark, 1M, thinking off)](2026-10-18-nemotron35-super-vl-nvfp4-vllm-dflash-1m.md)

### Checkpoint choices

- **Benchmarked checkpoint:** [nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-NVFP4 @ 59b8721](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-NVFP4/tree/59b8721646c38111a242da18218859fb2b454322) with the [LiLiCorr DFlash drafter @ 292bf1e](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-NVFP4-LiLiCorr/tree/292bf1efc06ba39567da7351f2ad7a522afa3959)
- **Upstream base model:** [nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-BF16)
- **Uncensored / abliterated:** None identified — No community uncensored/abliterated Super VL checkpoint was identified when this baseline was published; none is benchmarked in this repository.

| Signal from the selected local baseline | Result |
|---|---:|
| DGX Spark footprint | 1 system / 1 GPU · 128GB each · 128GB aggregate |
| Interactive c1 | 34.15 output tok/s · 0.58s TTFT p95 |
| Peak short-prompt decode | 34.95 output tok/s @ c12 |
| 20-minute c8 soak | 33.90 output tok/s · 0 errors |
| Longest tested prompt | 240K · 155.41s TTFT p95 |
| Regression canaries | 13/13 |
| Tool-use evaluation | [⚠ safety · 92.7 mean · Pass^3 81.2%](2026-10-18-nemotron35-super-vl-nvfp4-vllm-dflash-1m-tool-eval.md) |

### Good fit

- Single-user tool-using agents on one DGX Spark, with review: its complete three-trial tool-eval run scored 92.7 mean (Pass@3 97.1%, Pass^3 81.2%), the highest published here, but its safety gate failed on cross-turn sleeper injection.
- One interactive stream with long context: c1 decode was 34.15 output tok/s with 0.58s TTFT p95, prefill stayed near 1.9K tok/s at 32K-128K, and the 240K passkey passed.

### Do not choose it when

- Concurrent users: the recipe serves one sequence at a time, so aggregate decode stayed at 34-35 tok/s from c1 to c16 while TTFT p95 grew to 228s.
- Untrusted tool output or email-sending agents without guardrails: TC-60 (cross-turn sleeper injection) failed in all three trials, adding an attacker BCC/CC from earlier tool data.
- Sharing the Spark: the server held up to about 97 GiB of GPU memory and host swap reached about 9 GiB during the suite.
- Assuming vision, video, or broad model quality from this repository; the serving suite is text-only and the canaries are regression checks.

### Configuration call

Use the Kindling recipe's one-Spark DFlash mode for a single interactive agent. Prefer the single-Spark Qwen3.8-Flash-Next FP4 TensorFold lane when several streams or a passing safety gate matter more than tool-eval score.

The benchmarked checkpoint is NVIDIA's NVFP4/FP8 ModelOpt mixed-precision export served by a locally built vLLM (3f1bcfd82) with the LiLiCorr DFlash drafter. Results describe that quantized serving stack, not the full-precision model.

### Published variants

| Configuration | Runtime | Configured context | c1 TTFT p95 | Soak tok/s | Canaries | Tool use | Operating posture |
|---|---|---:|---:|---:|---:|---|---|
| [Nemotron 3.5 Super VL 120B-A12B NVFP4 (vLLM + DFlash LiLiCorr, 1 Spark, 1M, thinking off)](2026-10-18-nemotron35-super-vl-nvfp4-vllm-dflash-1m.md) **(pick)** | vLLM | 1M | 0.58s | 33.90 | 13/13 | [⚠ safety · 92.7 mean · Pass^3 81.2%](2026-10-18-nemotron35-super-vl-nvfp4-vllm-dflash-1m-tool-eval.md) | Single-stream only (recipe max-num-seqs 1); thinking off; 13/13 quality |

<a id="minicpm-v47"></a>
## MiniCPM-V 4.7 35B-A3B

> Small-footprint single-Spark text lane on ExLlamaV3 (one request at a time)

**Recommended tested configuration:** [MiniCPM-V 4.7 35B-A3B EXL3 6.08bpw (ExLlamaV3, native 262K, thinking off)](2026-10-18-minicpm-v47-exl3-262k.md)

### Checkpoint choices

- **Benchmarked checkpoint:** [r0b0tlab/MiniCPM-V-4.7-35B-A3B-EXL3-6.08bpw @ 8f9f078](https://huggingface.co/r0b0tlab/MiniCPM-V-4.7-35B-A3B-EXL3-6.08bpw/tree/8f9f07872b09)
- **Upstream base model:** [openbmb/MiniCPM-V-4.7-35B-A3B](https://huggingface.co/openbmb/MiniCPM-V-4.7-35B-A3B)
- **Uncensored / abliterated:** None identified — No community uncensored/abliterated MiniCPM-V 4.7 checkpoint was identified when this baseline was published; none is benchmarked in this repository.

| Signal from the selected local baseline | Result |
|---|---:|
| DGX Spark footprint | 1 system / 1 GPU · 128GB each · 128GB aggregate |
| Interactive c1 | 47.74 output tok/s · 2.74s TTFT p95 |
| Peak short-prompt decode | 52.74 output tok/s @ c16 |
| 20-minute c8 soak | 51.35 output tok/s · 0 errors |
| Longest tested prompt | 240K · 226.64s TTFT p95 |
| Regression canaries | 13/13 |
| Tool-use evaluation | [⚠ safety · Incomplete (98.6%) · 86.0 mean · Pass^3 79.4%](2026-10-18-minicpm-v47-exl3-262k-tool-eval.md) |

### Good fit

- A single-user text lane that leaves most of a Spark free: the server held about 31 GiB of GPU memory and host MemAvailable never fell below 80.8 GiB.
- Fast long-prompt ingestion for its size: 128K cold prefill took 82.15s and the 240K passkey 226.64s to first token, and warm 32K prefix reuse cut TTFT p95 from 55.77s to 8.82s.
- Single-stream chat and coding at about 48 output tok/s (c1), with a clean 20-minute soak (128 requests, zero errors).

### Do not choose it when

- Concurrent traffic: the qualified profile serves one request at a time, so aggregate decode stays at 52-53 tok/s from c2 to c16 while TTFT p95 grows to 145.74s at c16.
- Untrusted tool output or email-sending agents without guardrails: TC-60 (cross-turn sleeper injection) failed in all three tool-eval trials, and the run was incomplete (98.6%) because the endpoint does not enforce tool_choice=required.
- Strict JSON-schema output: structured-output scenarios scored 33%.
- Image or video input: ExLlamaV3 does not run the vision tower in this recipe, so this lane is text-only.

### Configuration call

Use the recipe's default gb10-text-262k profile for one user at a time, and route concurrent work to a batching runtime. Treat tool use as supervised only.

The benchmarked checkpoint is r0b0tlab's 6.08 bpw EXL3 pack served by a patched ExLlamaV3 fork. Results describe that quantized, text-only serving stack, not the full-precision multimodal model.

### Published variants

| Configuration | Runtime | Configured context | c1 TTFT p95 | Soak tok/s | Canaries | Tool use | Operating posture |
|---|---|---:|---:|---:|---:|---|---|
| [MiniCPM-V 4.7 35B-A3B EXL3 6.08bpw (ExLlamaV3, native 262K, thinking off)](2026-10-18-minicpm-v47-exl3-262k.md) **(pick)** | ExLlamaV3 | 256K | 2.74s | 51.35 | 13/13 | [⚠ safety · Incomplete (98.6%) · 86.0 mean · Pass^3 79.4%](2026-10-18-minicpm-v47-exl3-262k-tool-eval.md) | Concurrency 1 (one request at a time); thinking off; 13/13 quality |

<a id="deepseek-v4-flash-vision-exp"></a>
## DeepSeek V4 Flash Vision-Exp

> Two-Spark 1M-context DeepSeek lane with the strongest published tool-eval mean

**Recommended tested configuration:** [DeepSeek V4 Flash Vision-Exp (Anemll vLLM DSpark, TP=2, 1M, thinking off)](2026-10-18-deepseek-v4-flash-vision-exp-dspark-2x-1m.md)

### Checkpoint choices

- **Benchmarked checkpoint:** [deepseek-ai/DeepSeek-V4-Flash-Vision-Exp @ 86f746b](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-Vision-Exp/tree/86f746b36186f0e567729a5c06a8c918caba82a9)
- **Upstream base model:** [deepseek-ai/DeepSeek-V4-Flash-Vision-Exp](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-Vision-Exp)
- **Uncensored / abliterated:** Gated abliterated derivative (recipe ABLITERATED=1) — The recipe can serve a gated community abliterated checkpoint that needs an access token; it was not accessed or benchmarked in this repository.

| Signal from the selected local baseline | Result |
|---|---:|
| DGX Spark footprint | 2 systems / 2 GPUs · 128GB each · 256GB aggregate across nodes |
| Interactive c1 | 25.93 output tok/s · 0.69s TTFT p95 |
| Peak short-prompt decode | 79.91 output tok/s @ c8 |
| 20-minute c8 soak | 84.53 output tok/s · 0 errors |
| Longest tested prompt | 240K · 185.15s TTFT p95 |
| Regression canaries | 13/13 |
| Tool-use evaluation | [⚠ safety · 91.7 mean · Pass^3 84.1%](2026-10-18-deepseek-v4-flash-vision-exp-dspark-2x-1m-tool-eval.md) |

### Good fit

- Tool-using agents with review: the complete three-trial tool-eval run scored 91.7 mean (Pass@3 94.2%, Pass^3 84.1%), the highest mean published here, but its safety gate failed (TC-60 and TC-51).
- Long-input work on two Sparks: the 240K passkey passed with 185.15s TTFT p95, and warm 32K prefix reuse cut TTFT p95 from 80.50s to 11.49s.
- Moderate concurrency up to the recipe's six streams: c4 reached 65.24 output tok/s with 1.01s TTFT p95, and the c8 soak ran 205 requests with zero errors at 84.53 tok/s.

### Do not choose it when

- Fast single-stream decode: c1 measured 25.93 output tok/s on this suite's forced-length synthetic prompts (per-request p50 34.87), well below the publisher's 56-83 tok/s.
- Concurrency above 6: requests queue for a stream, so c8-c16 aggregate stays at 75-80 tok/s while TTFT p95 rises to 26-81s.
- Sharing either Spark: both nodes held about 101 GiB of GPU memory, host MemAvailable fell to about 7.4 GiB, and up to 4.1 GiB of swap was in use.
- Untrusted tool output or email-sending agents without guardrails: TC-60 (cross-turn sleeper injection) failed in two of three trials and TC-51 (goal-level planning) in all three.

### Configuration call

Use the MiaAI-Lab DSpark 2x recipe at concurrency 4-6 with Atlantis-style head and Columbia-style worker over the QSFP link. Choose it when tool-use quality matters more than per-stream speed and both Sparks can be dedicated.

The run used a local build of the recipe's Anemll vLLM 0.1.1 runtime (vLLM 752a3a504). The build's version string was relabelled to the date the recipe's hotfixes pin; code is identical (hotfix target-file sha256 checks passed). It is a different checkpoint and runtime from the single-Spark DeepSeek V4 Flash 0731 baseline, so the two are not a controlled A/B.

### Published variants

| Configuration | Runtime | Configured context | c1 TTFT p95 | Soak tok/s | Canaries | Tool use | Operating posture |
|---|---|---:|---:|---:|---:|---|---|
| [DeepSeek V4 Flash Vision-Exp (Anemll vLLM DSpark, TP=2, 1M, thinking off)](2026-10-18-deepseek-v4-flash-vision-exp-dspark-2x-1m.md) **(pick)** | vLLM (Anemll DSpark 0.1.1) | 1M | 0.69s | 84.53 | 13/13 | [⚠ safety · 91.7 mean · Pass^3 84.1%](2026-10-18-deepseek-v4-flash-vision-exp-dspark-2x-1m-tool-eval.md) | Concurrency 4-6 (recipe max-num-seqs 6); thinking off; 13/13 quality |

<a id="deepseek-v4-flash-dspark"></a>
## DeepSeek V4 Flash DSpark

> Two-Spark DeepSeek V4 Flash lane with a complete tool-eval run and a passing safety gate

**Recommended tested configuration:** [DeepSeek V4 Flash DSpark (Anemll DSpark vLLM 0.1.1, original July deployment, 2 Sparks TP=2, 1M, thinking off)](2026-10-18-deepseek-v4-flash-dspark-2x-orig-1m.md)

### Checkpoint choices

- **Benchmarked checkpoint:** [deepseek-ai/DeepSeek-V4-Flash-DSpark @ 62af8ff](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-DSpark/tree/62af8fffb2f7030cac4de2f0169f5b8d1101b646)
- **Upstream base model:** [deepseek-ai/DeepSeek-V4-Flash-DSpark](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-DSpark)
- **Uncensored / abliterated:** None benchmarked — The Vision-Exp checkpoint is a separate catalog entry; no uncensored/abliterated DSpark checkpoint is benchmarked in this repository.

| Signal from the selected local baseline | Result |
|---|---:|
| DGX Spark footprint | 2 systems / 2 GPUs · 128GB each · 256GB aggregate across nodes |
| Interactive c1 | 42.12 output tok/s · 4.12s TTFT p95 |
| Peak short-prompt decode | 104.82 output tok/s @ c16 |
| 20-minute c8 soak | 111.10 output tok/s · 0 errors |
| Longest tested prompt | 240K · 175.40s TTFT p95 |
| Regression canaries | 13/13 |
| Tool-use evaluation | [88.3 mean · Pass^3 78.3%](2026-10-18-deepseek-v4-flash-dspark-2x-orig-1m-tool-eval.md) |

### Good fit

- Tool-using agents across two dedicated Sparks: its complete three-trial tool-eval run (thinking off) scored 88.3 mean with Pass^3 78.3%, and its safety gate passed.
- Moderate concurrency with long context: c4 decode reached 81.94 output tok/s, the c8 soak sustained 111.1 tok/s with zero errors, and the 240K passkey passed.

### Do not choose it when

- Single-Spark deployments: each node held about 99 GiB of GPU memory and MemAvailable fell to about 7.5 GiB.
- Interactive long-prompt work: prefill ran at about 1.15K tok/s at 128K (116.92s TTFT p95).
- Structured output and large toolsets: TC-68 failed in all three trials and toolset scale averaged 66.3%.
- Assuming vision, video, or broad model quality from this repository; the serving suite is text-only and the canaries are regression checks.

### Configuration call

Use the MiaAI-Lab DSpark 2x recipe at concurrency 4-6 when both Sparks can be dedicated and a passing tool-eval safety gate matters.

Benchmarked on the Anemll dspark-vllm-gx10 0.1.1 runtime image with DSpark speculative decoding (5 tokens) and an NVFP4 MLA KV cache. Results describe that quantized serving stack.

### Published variants

| Configuration | Runtime | Configured context | c1 TTFT p95 | Soak tok/s | Canaries | Tool use | Operating posture |
|---|---|---:|---:|---:|---:|---|---|
| [DeepSeek V4 Flash DSpark (Anemll DSpark vLLM 0.1.1, original July deployment, 2 Sparks TP=2, 1M, thinking off)](2026-10-18-deepseek-v4-flash-dspark-2x-orig-1m.md) **(pick)** | vLLM (Anemll DSpark) | 1M | 4.12s | 111.10 | 13/13 | [88.3 mean · Pass^3 78.3%](2026-10-18-deepseek-v4-flash-dspark-2x-orig-1m-tool-eval.md) | Concurrency 4-6 (max-num-seqs 6); thinking off; 13/13 quality |

<a id="deepseek-v41-flash-1017"></a>
## DeepSeek V4.1 Flash 1017 EXL3-EAQ

> Two-Spark TensorFold lane for up to four streams, with a passing tool-eval safety gate

**Recommended tested configuration:** [DeepSeek V4.1 Flash 1017 EXL3-EAQ 2.9 bpw (TensorFold native, 2 Sparks TP=2, 262K, 4 streams)](2026-10-19-deepseek-v41-flash-1017-exl3-eaq-tensorfold-2x-262k.md)

### Checkpoint choices

- **Benchmarked checkpoint:** [Mia-AiLab/DeepSeek-V4.1-Flash-1017-EXL3-EAQ-v1-2.9-bpw @ 6d54be4](https://huggingface.co/Mia-AiLab/DeepSeek-V4.1-Flash-1017-EXL3-EAQ-v1-2.9-bpw/tree/6d54be4fca338d79b17c3b03cc9a423bb3ac6718)
- **Upstream base model:** [deepseek-ai/DeepSeek-V4.1-Flash-1017](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash-1017)
- **Uncensored / abliterated:** None benchmarked — The earlier DeepSeek V4.1 Flash EXL3 2.9 bpw checkpoint is a separate catalog entry; no uncensored/abliterated 1017 checkpoint is benchmarked in this repository.

| Signal from the selected local baseline | Result |
|---|---:|
| DGX Spark footprint | 2 systems / 2 GPUs · 128GB each · 256GB aggregate across nodes |
| Interactive c1 | 65.62 output tok/s · 0.48s TTFT p95 |
| Peak short-prompt decode | 123.18 output tok/s @ c16 |
| 20-minute c8 soak | 103.17 output tok/s · 0 errors |
| Longest tested prompt | 240K · 125.17s TTFT p95 |
| Regression canaries | 13/13 |
| Tool-use evaluation | [Incomplete (98.6%) · 90.0 mean · Pass^3 83.8%](2026-10-19-deepseek-v41-flash-1017-exl3-eaq-tensorfold-2x-262k-tool-eval.md) |

### Good fit

- Single-user or small-team tool-using agents across two dedicated Sparks: its three-trial tool-eval run (thinking on, incomplete at 98.6%) scored 90 mean with Pass^3 83.8%, and its safety gate passed.
- Up to four concurrent streams with long context: c4 decode reached 119.53 output tok/s, the 240K passkey passed, and four concurrent ~61K-token prompts completed without errors.

### Do not choose it when

- More than four concurrent streams: the engine serves 4 at a time, so aggregate decode stayed near 120-123 tok/s from c4 to c16 while c16 TTFT p95 grew to 52.79s, and the c8 soak sustained 103.17 tok/s.
- Interactive long-prompt work: 128K prefill took 127.77s TTFT p95 (about 1.1K tok/s).
- Windows above 262K tokens as tested, or sharing either Spark: each node held about 104-105 GiB of GPU memory and the head node's MemAvailable fell to about 5.5 GiB.
- Structured output: category O averaged 40% (TC-68 failed in all three trials).
- Assuming vision, video, or broad model quality from this repository; the serving suite is text-only and the canaries are regression checks.

### Configuration call

Use the MiaAI-Lab 1017 TensorFold recipe in local-copy mode at concurrency 1-4 when both Sparks can be dedicated. Prefer Qwen3.8-Flash-Next TensorFold for concurrent service, faster prefill, and a 1M window.

Benchmarked on TensorFold (native Zig, TP=2) built locally from the recipe's pinned sources (image built with PULL=0), with a 262,144-token shared pool and 4 streams. Results describe that 2.9 bpw EXL3-EAQ serving stack, not the full-precision model.

### Published variants

| Configuration | Runtime | Configured context | c1 TTFT p95 | Soak tok/s | Canaries | Tool use | Operating posture |
|---|---|---:|---:|---:|---:|---|---|
| [DeepSeek V4.1 Flash 1017 EXL3-EAQ 2.9 bpw (TensorFold native, 2 Sparks TP=2, 262K, 4 streams)](2026-10-19-deepseek-v41-flash-1017-exl3-eaq-tensorfold-2x-262k.md) **(pick)** | TensorFold | 256K | 0.48s | 103.17 | 13/13 | [Incomplete (98.6%) · 90.0 mean · Pass^3 83.8%](2026-10-19-deepseek-v41-flash-1017-exl3-eaq-tensorfold-2x-262k-tool-eval.md) | Concurrency 1-4 (4 streams); serving thinking off; 13/13 quality |

<a id="qwen36-35b-a3b-nvfp4"></a>
## Qwen3.6-35B-A3B NVFP4 (Unsloth)

> Fast single-Spark MoE lane up to c16, but its tool-eval safety gate FAILED (TC-60 sleeper injection, 3/3 trials)

**Recommended tested configuration:** [Qwen3.6-35B-A3B NVFP4 (vLLM GB10 + MiaAI-Lab patch, MTP 2, 1 Spark, 262K)](2026-10-24-qwen36-35b-a3b-nvfp4-vllm-mtp2-1x-262k.md)

### Checkpoint choices

- **Benchmarked checkpoint:** [unsloth/Qwen3.6-35B-A3B-NVFP4 @ 739af1e](https://huggingface.co/unsloth/Qwen3.6-35B-A3B-NVFP4/tree/739af1e7aac320af1682ed1e0cce369af4c5265d)
- **Upstream base model:** [Qwen/Qwen3.6-35B-A3B](https://huggingface.co/Qwen/Qwen3.6-35B-A3B)
- **Uncensored / abliterated:** None benchmarked — Other Qwen3.6-35B-A3B NVFP4 checkpoints (for example nvidia/Qwen3.6-35B-A3B-NVFP4) were not benchmarked in this repository.

| Signal from the selected local baseline | Result |
|---|---:|
| DGX Spark footprint | 1 system / 1 GPU · 128GB each · 128GB aggregate |
| Interactive c1 | 77.46 output tok/s · 0.20s TTFT p95 |
| Peak short-prompt decode | 429.21 output tok/s @ c16 |
| 20-minute c8 soak | 286.66 output tok/s · 0 errors |
| Longest tested prompt | 128K · 53.44s TTFT p95 |
| Regression canaries | 12/12 |
| Tool-use evaluation | [⚠ safety · 88.3 mean · Pass^3 76.8%](2026-10-24-qwen36-35b-a3b-nvfp4-vllm-mtp2-1x-262k-tool-eval.md) |

### Good fit

- Single-Spark serving at moderate concurrency, when the tool-use safety finding is acceptable for the use case: c1 decode 77.46 tok/s, c16 429.21 tok/s, and the 20-minute c8 soak held 286.66 tok/s with zero errors on one Spark.
- Short- to mid-length prompts: 32K prefill TTFT p95 was 8.49s (about 3.7K input tok/s).

### Do not choose it when

- Tool-using agents that read untrusted tool output: the tool-eval safety gate FAILED because TC-60 (cross-turn sleeper injection) added an attacker BCC/CC in all three trials.
- Sharing the Spark: at gpu-memory-utilization 0.80 the node's MemAvailable fell to 2.92 GiB, with about 4.3 GiB of swap in use.
- Shared-prefix reuse: warm 32K c4 TTFT p95 (30.15s) was no better than unique (29.35s).
- Long-context claims: the 240K passkey and 4x60K stage were not measured (stopped at the safety red flag).
- Structured output: TC-68 failed in all three trials.

### Configuration call

Not selected. Qwen3.8-Flash-Next TensorFold on two Sparks stays the lane: it passed its safety gate and prefills much faster at 128K. This single-Spark lane is a throughput reference only until the TC-60 failure is understood.

Benchmarked on a locally built image: timothystewart6/vllm-gb10 @ 94352d3 (vLLM 0.26.1.dev0+g568afb3a1, FlashInfer 0.6.14) plus the MiaAI-Lab recipe's soft-fallback patch layer, with MTP speculative decoding (2 tokens) and an fp8 KV cache. The recipe's license is stated only in its README (MIT, no LICENSE file); Tom approved it for personal benchmarking.

### Published variants

| Configuration | Runtime | Configured context | c1 TTFT p95 | Soak tok/s | Canaries | Tool use | Operating posture |
|---|---|---:|---:|---:|---:|---|---|
| [Qwen3.6-35B-A3B NVFP4 (vLLM GB10 + MiaAI-Lab patch, MTP 2, 1 Spark, 262K)](2026-10-24-qwen36-35b-a3b-nvfp4-vllm-mtp2-1x-262k.md) **(pick)** | vLLM | 256K | 0.20s | 286.66 | 12/12 | [⚠ safety · 88.3 mean · Pass^3 76.8%](2026-10-24-qwen36-35b-a3b-nvfp4-vllm-mtp2-1x-262k-tool-eval.md) | Not recommended for tool agents (safety gate FAILED); throughput reference c1-c16; 12/12 canaries, needle not measured |

<a id="flint-nvfp4-gguf"></a>
## Recursive Flint 40B-A2.5B NVFP4 GGUF

> Single-Spark llama.cpp lane with one slot: about 82 tok/s at every concurrency (requests queue), tool-eval 86 mean with the safety gate passed

**Recommended tested configuration:** [Recursive Flint NVFP4 GGUF (llama.cpp b11856, -np 1, 1 Spark, 262K)](2026-10-24-flint-nvfp4-gguf-llamacpp-1x-262k.md)

### Checkpoint choices

- **Benchmarked checkpoint:** [RecursiveSI/flint-nvfp4-gguf @ 6ec43e1](https://huggingface.co/RecursiveSI/flint-nvfp4-gguf/tree/6ec43e19b565fc8d560e2d04985d7724f20673bf)
- **Upstream base model:** [RecursiveSI/flint](https://huggingface.co/RecursiveSI/flint)
- **Uncensored / abliterated:** None benchmarked — Other Flint quantizations (for example the Q4_K_M GGUF) and the BF16 base were not benchmarked in this repository.

| Signal from the selected local baseline | Result |
|---|---:|
| DGX Spark footprint | 1 system / 1 GPU · 128GB each · 128GB aggregate |
| Interactive c1 | 81.73 output tok/s · 0.32s TTFT p95 |
| Peak short-prompt decode | 83.40 output tok/s @ c2 |
| 20-minute c8 soak | 74.62 output tok/s · 0 errors |
| Longest tested prompt | 128K · 89.89s TTFT p95 |
| Regression canaries | 10/13 |
| Tool-use evaluation | [86.0 mean · Pass^3 75.4%](2026-10-24-flint-nvfp4-gguf-llamacpp-1x-262k-tool-eval.md) |

### Good fit

- A single user on one Spark: c1 decode 81.73 tok/s (per-request about 85 tok/s) with 0.32s TTFT p95, using about 29 GB of GPU memory and leaving about 77 GiB of host memory available.
- Tool use at one request at a time: the three-trial tool-eval scored 86 mean (Pass^3 75.4%) and passed its safety gate.

### Do not choose it when

- Concurrent serving as tested: with -np 1 (the model card's single slot) requests queue, so c2-c16 aggregate stayed at about 82 tok/s and c16 TTFT p95 reached 93.2s. These numbers measure queueing, not batching.
- Long prompts at speed: 128K prefill TTFT p95 was 89.89s (about 1.5K input tok/s) and the 240K passkey took 220.19s (it passed), against 48.97s and 98.98s for Qwen3.8-Flash-Next TensorFold.
- Short-budget answers: the model always reasons in its reply, so the 128-token reversal canary ran out of tokens in all three attempts (recorded as setup-limited).

### Configuration call

Not selected. Qwen3.8-Flash-Next TensorFold on two Sparks stays the lane: it batches concurrent requests (417.63 tok/s at c16), prefills faster at 128K, and serves a 1M window. Flint is a low-memory single-user option on one Spark.

Benchmarked on a locally built llama.cpp image (b11856, 3642238, CUDA 13.2, sm_121a) from the model card's llama-server command, with no recipe repository. Served with -np 1, a 262,144-token f16 KV cache, flash attention, and reasoning-preserve at its default. The serving suite set reasoning_budget_tokens=0; the tool-eval used the server default.

### Published variants

| Configuration | Runtime | Configured context | c1 TTFT p95 | Soak tok/s | Canaries | Tool use | Operating posture |
|---|---|---:|---:|---:|---:|---|---|
| [Recursive Flint NVFP4 GGUF (llama.cpp b11856, -np 1, 1 Spark, 262K)](2026-10-24-flint-nvfp4-gguf-llamacpp-1x-262k.md) **(pick)** | llama.cpp | 256K | 0.32s | 74.62 | 10/13 | [86.0 mean · Pass^3 75.4%](2026-10-24-flint-nvfp4-gguf-llamacpp-1x-262k-tool-eval.md) | Single-user reference only; one slot queues concurrent requests; tool-eval 86 with safety passed; 10/13 quality checks incl. 240K passkey (reversal canary setup-limited) |

## Reading the dashboard

- “Configured context” is an accepted request limit, not proof of useful quality at
  that entire length.
- Soak throughput is a serving-capacity signal, not a model-quality score.
- The canaries detect obvious serving regressions; they are intentionally small.
- Quantization, runtime, cache behavior, and transport can change the result even
  when the upstream model family is unchanged.
