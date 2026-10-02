# Model selection dashboard

Use this page to choose among the model families that have published two-DGX-Spark
baselines in this repository. For the full cross-configuration numbers and charts,
open the [benchmark summary](README.md).

Last updated: 2026-10-01 · Model families: 3 · Published configurations: 8

## Hardware footprint

Every currently published recipe uses **2× NVIDIA DGX Spark systems with 128GB
of unified memory each**: two GPUs total and 256GB aggregate capacity across the
two-node deployment. That is two separate 128GB systems, not one pooled 256GB
memory space. This is the validated footprint for these exact serving recipes,
not a claim that every possible quantization of the model requires two DGX Sparks.

## Fast decision

| Model | DGX Spark requirement | Position | Good default for | Choose something else when |
|---|---|---|---|---|
| [Qwen3.8-Flash-Next NVFP4](#qwen38-flash-next) | 2 systems / 2 GPUs · 128GB each · 256GB aggregate across nodes | Default high-throughput lane for coding, agents, chat, and RAG | Primary local lane for short- and medium-context coding, tool-using agents, chat, and RAG. | Treating a configured 1M YaRN window as validated 1M model quality; the published runs exercise context only through approximately 240K tokens. |
| [GLM-5.3 Flash EXL3/TR3](#glm53-flash) | 2 systems / 2 GPUs · 128GB each · 256GB aggregate across nodes | Long-context coding and agentic lane with a speed-versus-assurance choice | Complex coding and agentic work at low concurrency, consistent with the upstream model's stated focus. | Exact-string or deterministic transformation workloads on the TensorFold lane until the repeatable reverse-marker regression is understood; its combined result was 10/13. |
| [DeepSeek V4.1 Flash EXL3](#deepseek-v41-flash) | 2 systems / 2 GPUs · 128GB each · 256GB aggregate across nodes | Low-concurrency, input-heavy agentic lane with clean canaries | Input-heavy agentic, reasoning, and long-document work where concurrency 1-2 is sufficient. | High-throughput concurrent chat or agent fleets; c2 was the practical peak and higher concurrency mainly increased queueing. |

Practical default: start with **Qwen3.8-Flash-Next** for mixed interactive,
coding, RAG, and agent traffic. Move to **GLM-5.3 Flash** when its long-context
coding/agent profile is the better fit and choose deliberately between the fast
TensorFold lane and the clean-canary vLLM lane. Use **DeepSeek V4.1 Flash** for
input-heavy, low-concurrency work where its clean local canaries matter more than
aggregate serving throughput.

## Evidence boundary

“Good fit” combines upstream model-card positioning with the local serving evidence.
This repository directly measures latency, throughput, stability, a 240K retrieval
check, and small deterministic canaries. It does **not** compare broad intelligence,
safety, production vision quality, tool correctness, or quality at the configured
850K/1M request limits. Validate those against the actual application before routing
production work.

<a id="qwen38-flash-next"></a>
## Qwen3.8-Flash-Next NVFP4

> Default high-throughput lane for coding, agents, chat, and RAG

**Recommended tested configuration:** [Qwen3.8-Flash-Next NVIDIA NVFP4 (Mia vLLM, FP8 KV)](2026-09-07-qwen38-mia-nvidia-fp8kv-native-262k.md)

**Upstream:** [Official Qwen model card](https://huggingface.co/Qwen/Qwen3.8-Flash-Next)

| Signal from the selected local baseline | Result |
|---|---:|
| DGX Spark footprint | 2 systems / 2 GPUs · 128GB each · 256GB aggregate across nodes |
| Interactive c1 | 47.34 output tok/s · 0.40s TTFT p95 |
| Peak short-prompt decode | 207.77 output tok/s @ c16 |
| 20-minute c8 soak | 197.42 output tok/s · 0 errors |
| Longest tested prompt | 240K · 99.22s TTFT p95 |
| Regression canaries | 13/13 |

### Good fit

- Primary local lane for short- and medium-context coding, tool-using agents, chat, and RAG.
- Concurrent interactive traffic: the selected vLLM baseline sustained 197.42 output tok/s at c8 with 1.11s TTFT p95 and zero soak errors.
- Native-context work through the suite's validated approximately 240K-token prompt.

### Do not choose it when

- Treating a configured 1M YaRN window as validated 1M model quality; the published runs exercise context only through approximately 240K tokens.
- Strict exact-copy guarantees without task-specific checks; one supplemental marker probe missed once even though the 13/13 standard suite passed.
- Assuming vision or video production readiness from this repository; the published benchmark suite is text-only.

### Configuration call

Use the native-262K vLLM/FP8-KV baseline as the conservative default. The 2200 MHz YaRN baseline is slightly faster and exposes a 1M request limit, but this suite did not validate quality beyond approximately 240K.

Qwen describes the upstream model as an experimental, multimodal agentic architecture. This repository independently validates serving behavior and small regression canaries, not broad capability or safety.

### Published variants

| Configuration | Runtime | Configured context | c1 TTFT p95 | Soak tok/s | Canaries | Operating posture |
|---|---|---:|---:|---:|---:|---|
| [Qwen3.8-Flash-Next NVIDIA NVFP4 (Mia vLLM, FP8 KV)](2026-09-07-qwen38-mia-nvidia-fp8kv-native-262k.md) **(pick)** | vLLM | 256K | 0.40s | 197.42 | 13/13 | Concurrency 8; faster prefill, larger KV pool |
| [Qwen3.8-Flash-Next-NVFP4 (Mia vLLM, 2200 MHz)](2026-09-03-qwen38-flash-next-vllm-mia-yarn-1m-2200mhz.md) | vLLM | 1M | 0.36s | 201.58 | 13/13 | 2200 MHz; concurrency 8 |
| [Qwen3.8-Flash-Next-NVFP4 (Mia vLLM)](2026-08-31-qwen38-flash-next-vllm-mia-yarn-1m.md) | vLLM | 1M | 0.43s | 197.71 | 13/13 | Concurrency 8 |
| [Qwen3.8-Flash-Next-NVFP4](2026-08-29-qwen38-flash-next-nvfp4-native-262k.md) | SGLang | 256K | 0.41s | 157.61 | 13/13 | Concurrency 8 |

<a id="glm53-flash"></a>
## GLM-5.3 Flash EXL3/TR3

> Long-context coding and agentic lane with a speed-versus-assurance choice

**Recommended tested configuration:** [GLM-5.3 Flash EXL3/TR3 4 bpw (TensorFold v0.6.0)](2026-10-01-glm53-flash-exl3-tensorfold-v060-1m.md)

**Upstream:** [Official Z.ai model card](https://huggingface.co/zai-org/GLM-5.3-Flash)

| Signal from the selected local baseline | Result |
|---|---:|
| DGX Spark footprint | 2 systems / 2 GPUs · 128GB each · 256GB aggregate across nodes |
| Interactive c1 | 51.49 output tok/s · 0.41s TTFT p95 |
| Peak short-prompt decode | 96.72 output tok/s @ c12 |
| 20-minute c8 soak | 84.90 output tok/s · 0 errors |
| Longest tested prompt | 240K · 163.89s TTFT p95 |
| Regression canaries | 10/13 |

### Good fit

- Complex coding and agentic work at low concurrency, consistent with the upstream model's stated focus.
- Long-context interactive or small-batch work: TensorFold delivered 51.49 output tok/s at c1 and 92.68 at c4, while the 240K passkey check passed.
- Tool, thinking, or multimodal workflows after application-specific validation; the serving recipe exposes those features.

### Do not choose it when

- Exact-string or deterministic transformation workloads on the TensorFold lane until the repeatable reverse-marker regression is understood; its combined result was 10/13.
- Latency-sensitive traffic above concurrency 4; c8 and higher mostly added queueing.
- Commercial use of the tested TensorFold recipe unless the DFlash2 licensing constraint is separately resolved.
- Treating vision or tool quality as benchmarked here; the published suite is text-only.

### Configuration call

Choose TensorFold when throughput is the priority and the workload tolerates its documented canary caveat. Choose a vLLM baseline when the clean 13/13 regression result matters more than serving speed.

Z.ai positions GLM-5.3 Flash for coding, agents, multimodal input, and long context. The local results prove performance, stability, and a 240K retrieval check for these quantized recipes only.

### Published variants

| Configuration | Runtime | Configured context | c1 TTFT p95 | Soak tok/s | Canaries | Operating posture |
|---|---|---:|---:|---:|---:|---|
| [GLM-5.3 Flash EXL3/TR3 4 bpw (TensorFold v0.6.0)](2026-10-01-glm53-flash-exl3-tensorfold-v060-1m.md) **(pick)** | TensorFold | 1M | 0.41s | 84.90 | 10/13 | Concurrency 1 interactive; 4 batch; 10/13 quality |
| [GLM-5.3 Flash EXL3/TR3 4 bpw (refreshed recipe)](2026-09-15-glm53-flash-exl3-tr3-4bpw-850k.md) | vLLM | 850K | 1.27s | 21.88 | 13/13 | Concurrency 1 interactive; 4 batch; Socket |
| [GLM-5.3-Flash-EXL3](2026-08-29-glm53-flash-exl3-native-1m.md) | vLLM | 1M | 0.95s | 38.53 | 13/13 | Concurrency 1 interactive; 4 batch |

<a id="deepseek-v41-flash"></a>
## DeepSeek V4.1 Flash EXL3

> Low-concurrency, input-heavy agentic lane with clean canaries

**Recommended tested configuration:** [DeepSeek V4.1 Flash EXL3 2.9 bpw](2026-09-15-deepseek-v41-flash-exl3-2.9bpw-600k.md)

**Upstream:** [Official DeepSeek model card](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash)

| Signal from the selected local baseline | Result |
|---|---:|
| DGX Spark footprint | 2 systems / 2 GPUs · 128GB each · 256GB aggregate across nodes |
| Interactive c1 | 27.42 output tok/s · 0.85s TTFT p95 |
| Peak short-prompt decode | 44.49 output tok/s @ c2 |
| 20-minute c8 soak | 35.31 output tok/s · 0 errors |
| Longest tested prompt | 240K · 408.37s TTFT p95 |
| Regression canaries | 13/13 |

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

| Configuration | Runtime | Configured context | c1 TTFT p95 | Soak tok/s | Canaries | Operating posture |
|---|---|---:|---:|---:|---:|---|
| [DeepSeek V4.1 Flash EXL3 2.9 bpw](2026-09-15-deepseek-v41-flash-exl3-2.9bpw-600k.md) **(pick)** | vLLM | 600K | 0.85s | 35.31 | 13/13 | Concurrency 2; unpacked Engram |

## Reading the dashboard

- “Configured context” is an accepted request limit, not proof of useful quality at
  that entire length.
- Soak throughput is a serving-capacity signal, not a model-quality score.
- The canaries detect obvious serving regressions; they are intentionally small.
- Quantization, runtime, cache behavior, and transport can change the result even
  when the upstream model family is unchanged.
