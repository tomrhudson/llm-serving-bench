# Model selection dashboard

Use this page to choose among the model families with published DGX Spark
baselines in this repository. For the full cross-configuration numbers and charts,
open the [benchmark summary](README.md).

Last updated: 2026-10-08 · Model families: 5 · Published configurations: 14

## Hardware footprint

Published recipes use 1× DGX Spark, 2× DGX Spark configurations with 128GB of unified memory per system. Multi-node capacity is aggregate capacity across separate systems, not one pooled memory space. Each footprint describes the exact tested serving recipe rather than a universal model requirement.

## Fast decision

| Model | DGX Spark requirement | Position | Good default for | Choose something else when |
|---|---|---|---|---|
| [Qwen3.8-Flash-Next NVFP4](#qwen38-flash-next) | 2 systems / 2 GPUs · 128GB each · 256GB aggregate across nodes | Default high-throughput lane for coding, agents, chat, and RAG | Primary local lane for short- and medium-context coding, tool-using agents, chat, and RAG. | Treating a configured 1M YaRN window as validated 1M model quality; the published runs exercise context only through approximately 240K tokens. |
| [Qwen3.8 27B](#qwen38-27b) | 1 system / 1 GPU · 128GB each · 128GB aggregate | Single-Spark 27B lane with official and uncensored checkpoint choices | A capable local text lane that fits on one DGX Spark without cross-node serving. | Interactive near-window prompts; the official and uncensored baselines took 395 and 558 seconds respectively to first token on the 240K check. |
| [GLM-5.3 Flash](#glm53-flash) | 2 systems / 2 GPUs · 128GB each · 256GB aggregate across nodes | Long-context coding and agentic lane with runtime and context tradeoffs | Complex coding and agentic work at low concurrency, consistent with the upstream model's stated focus. | Exact-string or deterministic transformation workloads on the TensorFold lane until the repeatable reverse-marker regression is understood; its combined result was 10/13. |
| [DeepSeek V4 Flash 0731](#deepseek-v4-flash) | 1 system / 1 GPU · 128GB each · 128GB aggregate | Single-Spark long-context lane built for one request at a time | A dedicated one-Spark lane for long, input-heavy requests where concurrency 1 is acceptable. | Concurrent interactive traffic; aggregate decode stayed near 30 tok/s while c8 TTFT p95 rose to 118.29 seconds. |
| [DeepSeek V4.1 Flash EXL3](#deepseek-v41-flash) | 2 systems / 2 GPUs · 128GB each · 256GB aggregate across nodes | Low-concurrency, input-heavy agentic lane with clean canaries | Input-heavy agentic, reasoning, and long-document work where concurrency 1-2 is sufficient. | High-throughput concurrent chat or agent fleets; c2 was the practical peak and higher concurrency mainly increased queueing. |

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
check, and small deterministic canaries. It does **not** compare broad intelligence,
safety, production vision quality, tool correctness, or quality at the configured
850K/1M request limits. Validate those against the actual application before routing
production work.

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

### Good fit

- Primary local lane for short- and medium-context coding, tool-using agents, chat, and RAG.
- Concurrent interactive traffic: the selected TensorFold baseline sustained 432.90 output tok/s at c8 with 1.00s TTFT p95 and zero soak errors.
- Native-context work through the suite's validated approximately 240K-token prompt.

### Do not choose it when

- Treating a configured 1M YaRN window as validated 1M model quality; the published runs exercise context only through approximately 240K tokens.
- Assuming broad model quality from the 13/13 regression canaries; they cover retrieval and small deterministic checks only.
- Assuming vision or video production readiness from this repository; the published benchmark suite is text-only.

### Configuration call

Use TensorFold at concurrency 8 for interactive service and up to 16 for throughput-heavy work. Keep the native-262K vLLM baseline as the more mature fallback when runtime conservatism or established routing compatibility matters.

Qwen describes the upstream model as an experimental, multimodal agentic architecture. This repository independently validates serving behavior and small regression canaries, not broad capability or safety.

### Published variants

| Configuration | Runtime | Configured context | c1 TTFT p95 | Soak tok/s | Canaries | Operating posture |
|---|---|---:|---:|---:|---:|---|
| [Qwen3.8-Flash-Next NVIDIA NVFP4 (TensorFold, 1M YaRN)](2026-10-08-qwen38-flash-next-nvfp4-tensorfold-1m.md) **(pick)** | TensorFold | 1M | 0.23s | 432.90 | 13/13 | Concurrency 8 interactive; up to 16 batch; 13/13 quality |
| [Qwen3.8-Flash-Next NVIDIA NVFP4 (Mia vLLM, FP8 KV, 2200 MHz)](2026-10-03-qwen38-mia-nvidia-fp8kv-native-262k-2200mhz.md) | vLLM | 256K | 0.42s | 196.70 | 13/13 | 2200 MHz; concurrency 8; longer timeout near 240K |
| [Qwen3.8-Flash-Next NVIDIA NVFP4 (Mia vLLM, FP8 KV)](2026-09-07-qwen38-mia-nvidia-fp8kv-native-262k.md) | vLLM | 256K | 0.40s | 197.42 | 13/13 | Concurrency 8; faster prefill, larger KV pool |
| [Qwen3.8-Flash-Next-NVFP4 (Mia vLLM, 2200 MHz)](2026-09-03-qwen38-flash-next-vllm-mia-yarn-1m-2200mhz.md) | vLLM | 1M | 0.36s | 201.58 | 13/13 | 2200 MHz; concurrency 8 |
| [Qwen3.8-Flash-Next-NVFP4 (Mia vLLM)](2026-08-31-qwen38-flash-next-vllm-mia-yarn-1m.md) | vLLM | 1M | 0.43s | 197.71 | 13/13 | Concurrency 8 |
| [Qwen3.8-Flash-Next-NVFP4](2026-08-29-qwen38-flash-next-nvfp4-native-262k.md) | SGLang | 256K | 0.41s | 157.61 | 13/13 | Concurrency 8 |

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

### Good fit

- A capable local text lane that fits on one DGX Spark without cross-node serving.
- Concurrent interactive traffic on the selected NVFP4 baseline: its c8 soak sustained 157.80 output tok/s with 1.01s TTFT p95 and zero request errors.
- Native-context retrieval work through the suite's validated approximately 240K-token prompt.

### Do not choose it when

- Interactive near-window prompts; the official and uncensored baselines took 395 and 558 seconds respectively to first token on the 240K check.
- Using the uncensored derivative by default in trust-sensitive workflows; it needs workload-specific safety and behavior validation.
- Treating vision or tool quality as benchmarked here; the published suite is text-only.

### Configuration call

Use the RadixArk NVFP4 checkpoint as the default: it is materially faster and has the cleaner upstream relationship. Choose the orcarouter uncensored derivative only when that behavior is an explicit requirement, and cap interactive concurrency at 4.

The two reports share the same single-Spark SGLang runtime family but use different checkpoints and serving limits. Their performance is therefore an operational comparison, not a controlled quantization-only A/B.

### Published variants

| Configuration | Runtime | Configured context | c1 TTFT p95 | Soak tok/s | Canaries | Operating posture |
|---|---|---:|---:|---:|---:|---|
| [Qwen3.8 27B NVFP4 (SGLang)](2026-10-02-qwen38-27b-nvfp4-sglang-native-262k.md) **(pick)** | SGLang | 256K | 0.18s | 157.80 | 13/13 | Concurrency 8; 13/13 quality |
| [Qwen3.8 27B Uncensored FP8 (SGLang)](2026-10-02-qwen38-27b-uncensored-fp8-sglang-native-262k.md) | SGLang | 256K | 0.28s | 63.89 | 13/13 | Concurrency 4; derivative checkpoint; 13/13 quality |

<a id="glm53-flash"></a>
## GLM-5.3 Flash

> Long-context coding and agentic lane with runtime and context tradeoffs

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

### Good fit

- Complex coding and agentic work at low concurrency, consistent with the upstream model's stated focus.
- Long-context interactive or small-batch work: TensorFold delivered 51.49 output tok/s at c1 and 92.68 at c4, while the 240K passkey check passed.
- Tool, thinking, or multimodal workflows after application-specific validation; the serving recipe exposes those features.

### Do not choose it when

- Exact-string or deterministic transformation workloads on the TensorFold lane until the repeatable reverse-marker regression is understood; its combined result was 10/13.
- Latency-sensitive traffic above concurrency 4; c8 and higher mostly added queueing.
- Treating the NVFP4 vLLM lane's 13/13 canaries as broad assurance while its runtime still reports the documented weight-scale accuracy warning.
- Commercial use of the tested TensorFold recipe unless the DFlash2 licensing constraint is separately resolved.
- Treating vision or tool quality as benchmarked here; the published suite is text-only.

### Configuration call

Choose TensorFold when throughput and the 1M request window are the priority and the workload tolerates its documented canary caveat. The vLLM/NVFP4 low-reasoning baseline passed 13/13 checks and has lower c8 queue latency, but its runtime weight-scale warning must be resolved before treating it as the assurance choice.

Z.ai positions GLM-5.3 Flash for coding, agents, multimodal input, and long context. The local results prove performance, stability, and a 240K retrieval check for these quantized recipes only.

### Published variants

| Configuration | Runtime | Configured context | c1 TTFT p95 | Soak tok/s | Canaries | Operating posture |
|---|---|---:|---:|---:|---:|---|
| [GLM-5.3 Flash NVFP4 (vLLM, low reasoning)](2026-10-03-glm53-flash-nvfp4-vllm-native-262k-low-reasoning.md) | vLLM | 256K | 0.45s | 60.90 | 13/13 | Concurrency 1 interactive; 8 batch; 13/13 with accuracy warning |
| [GLM-5.3 Flash EXL3/TR3 4 bpw (TensorFold v0.6.0)](2026-10-01-glm53-flash-exl3-tensorfold-v060-1m.md) **(pick)** | TensorFold | 1M | 0.41s | 84.90 | 10/13 | Concurrency 1 interactive; 4 batch; 10/13 quality |
| [GLM-5.3 Flash EXL3/TR3 4 bpw (refreshed recipe)](2026-09-15-glm53-flash-exl3-tr3-4bpw-850k.md) | vLLM | 850K | 1.27s | 21.88 | 13/13 | Concurrency 1 interactive; 4 batch; Socket |
| [GLM-5.3-Flash-EXL3](2026-08-29-glm53-flash-exl3-native-1m.md) | vLLM | 1M | 0.95s | 38.53 | 13/13 | Concurrency 1 interactive; 4 batch |

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

| Configuration | Runtime | Configured context | c1 TTFT p95 | Soak tok/s | Canaries | Operating posture |
|---|---|---:|---:|---:|---:|---|
| [DeepSeek V4 Flash 0731 EXL3/SparkInfer](2026-10-02-deepseek-v4-flash-0731-sparkinfer-384k.md) **(pick)** | vLLM + SparkInfer | 384K | 0.54s | 26.89 | 13/13 | Concurrency 1; benchmark-only dependency repair |

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
