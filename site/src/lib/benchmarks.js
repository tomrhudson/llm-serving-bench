import catalog from '../../../results/catalog.json';
import suite from '../../../configs/qwen-native-standard.json';

export const repository = 'https://github.com/tomrhudson/llm-serving-bench';
const reports = import.meta.glob('../../../results/*.md', {
  eager: true, import: 'default', query: '?raw',
});
const integer = new Intl.NumberFormat('en-US');
const decimal = new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export const unavailable = 'Unavailable';
export const number = (value) => value == null ? unavailable : integer.format(value);
export const rate = (value) => value == null ? unavailable : decimal.format(value);
export const reportUrl = (file) => `${repository}/blob/main/results/${file}`;
export const modelUrl = (id) => `/models/${id}/`;
export const displayDate = (value) => new Intl.DateTimeFormat('en-US', {
  dateStyle: 'medium', timeZone: 'UTC',
}).format(new Date(value));

function readReport(file) {
  const report = reports[`../../../results/${file}`];
  if (!report) throw new Error(`Missing published report: ${file}`);
  return report;
}

function plain(text = '') {
  return text.replace(/\[([^\]]+)\]\([^)]+\)/g, '$1').replace(/\*\*|`/g, '').trim();
}

function field(markdown, name) {
  // A labeled Markdown list item may continue on an indented line.
  const pattern = new RegExp(`^[-*] (?:\\*\\*)?(?:${name})(?:\\*\\*)?: *(?:\\*\\*)?([^\\n]*(?:\\n {2,}[^\\n]+)*)`, 'im');
  return markdown.match(pattern)?.[1].replace(/\n\s+/g, ' ').trim();
}

function recipe(credit, report) {
  const links = [...credit.matchAll(/\[([^\]]+)\]\((https:\/\/[^)]+)\)/g)];
  const source = links.find(([, , url]) => url.startsWith('https://github.com/')) ?? links[0];
  if (!source) return { text: plain(credit) || unavailable };

  const [, title, href] = source;
  const url = new URL(href);
  const [, author, repo, refKind, ref] = url.pathname.split('/');
  const revision = url.hostname === 'github.com' && /^[a-f\d]{7,40}$/i.test(ref ?? '') && refKind === 'tree' ? ref : undefined;
  const reportedRevision = field(report, 'Runtime recipe commit|Recipe commit')?.match(/[a-f\d]{7,40}/i)?.[0];
  const pinned = revision ?? (url.hostname === 'github.com' ? reportedRevision : undefined);
  return {
    text: plain(credit),
    title,
    author,
    revision: pinned,
    href: pinned ? `${url.origin}/${author}/${repo}/tree/${pinned}` : href,
    label: url.hostname === 'github.com' ? 'Recipe' : 'Model card',
  };
}

function quantization(report, title, label) {
  const explicit = field(report, 'Weight quantization|Quantization');
  if (explicit) return plain(explicit);
  const checkpoint = field(report, 'Checkpoint|Model');
  // Weight formats are read from the title, label or checkpoint. KV cache
  // precision alone does not identify weight quantization.
  const evidence = plain(`${title} ${label} ${checkpoint ?? ''}`);
  const patterns = [
    /\bEXL3(?:[- /](?:EAQ|TR3))?\b(?:[- :\w.]{0,12}?\d+(?:\.\d+)?[- ]?bpw)?/i,
    /\bFP4[- ]Local\b(?: QAD)?/i,
    /\bMLX[- ]4[- ]?bit\b/i,
    /\bIQ2_XXS experts, NVFP4 Mamba projections, and Q8_0 attention, latent, and head projections/i,
    /\bNVFP4(?: GGUF)?\b/i,
    /\bBF16\b/i,
    /\b(?:Uncensored[- ]FP8|FP8 (?:weights|checkpoint))\b/i,
  ];
  for (const pattern of patterns) {
    const match = evidence.match(pattern);
    if (match) {
      if (match[0].toUpperCase() === 'EXL3') {
        const checkpointFormat = plain(checkpoint).match(/\bEXL3[- /](?:EAQ|TR3)\b(?:[- :\w.]{0,12}?\d+(?:\.\d+)?[- ]?bpw)?/i);
        if (checkpointFormat) return checkpointFormat[0].replace(/-(?=\d.*bpw)/i, ' ');
      }
      return match[0];
    }
  }
  // Some reports record the weight format in prose, outside the metadata.
  const described = report.match(/\b(?:the |this )?(BF16) checkpoint\b/i);
  return described?.[1] ?? unavailable;
}

function parseContext(baseline, report) {
  const configured = report.match(/\b([\d,]+)[- ]token request window\b/i)?.[1]
    ?? plain(field(report, 'Configured context|Context length')).match(/^([\d,]+)/)?.[1];
  const configuredTokens = configured ? Number(configured.replaceAll(',', '')) : baseline.context_tokens;
  const prefill = [...(baseline.prefill ?? [])];

  // Some serving reports retain the passkey under long context instead of
  // the catalog's cold prefill series. Read only the primary measurement row.
  const passkey = report.match(/^\|\s*(?:240K passkey(?:, c1)?|needle-240k-c1(?: \(long-context stage\))?)\s*\| *\*{0,2}([\d,.]+)\*{0,2} *\| *\*{0,2}([\d.]+)s?\*{0,2} *\|/im);
  const passed = /(?:^|\n)[-*] (?:\*\*)?240K passkey[^\n:]*: *(?:\*\*)?(?:1\/1|pass(?:ed)?)\b|\bthe 240K passkey (?:was correct|passed)\b|^\|\s*240K passkey, c1[^\n]*\b1\/1 correct\b/im.test(report);
  const skipped = /^[-*] 240K passkey retrieval[^:\n]*: *(?:\*\*)?(?:not measured|not run)\b/im.test(report);

  if (passkey && passed && !prefill.some((row) => row.input_tokens === 245760)) {
    prefill.push({
      input_tokens: 245760,
      input_tps: Number(passkey[1].replaceAll(',', '')),
      ttft_p95_seconds: Number(passkey[2]),
    });
  }

  const longest = Math.max(0, ...prefill.map((row) => row.input_tokens));
  return {
    configuredTokens,
    testedTokens: Math.max(longest, passkey && !skipped ? 245760 : 0) || undefined,
    validatedTokens: passed && !skipped ? 245760 : undefined,
    validation: skipped ? 'Passkey not run' : passed ? 'Passkey passed' : unavailable,
    prefill: prefill.sort((a, b) => a.input_tokens - b.input_tokens),
  };
}

function runtimeProvenance(report, runtime) {
  const runtimeText = field(report, 'Runtime|Serving engine|Engine')
    ?? report.match(/\bRuntime: ([^\n]*?)(?:\. |$)/m)?.[1];
  const image = field(report, 'Runtime image(?: digest)?|Container image|Image digest');
  const first = plain(runtimeText).split(/(?<=[\w`])\.\s|; /)[0];
  return [first && first !== runtime ? first : '', plain(image)].filter(Boolean).join(' · ') || unavailable;
}

export function installPrompt(config) {
  const report = readReport(config.report);
  const hasRecipe = config.recipe.label === 'Recipe';
  const settings = field(report, 'Serving configuration|Serving settings|Serving');
  if (!hasRecipe && !settings) return;

  const checkpoint = field(report, 'Checkpoint') ?? field(report, 'Model');
  const weights = checkpoint?.match(/\]\((https:\/\/huggingface\.co\/[^)\s]+)\)/)?.[1] ?? plain(checkpoint);
  const drafter = field(report, 'Drafter');
  const configuration = [
    `Configuration: ${config.label}`,
    `Hardware: ${config.hardware}`,
    `Runtime: ${config.runtime}`,
    config.runtimeProvenance !== unavailable && `Tested runtime: ${config.runtimeProvenance}`,
    config.configuredTokens && `Configured context: ${number(config.configuredTokens)} tokens`,
    config.recipe.href && `${hasRecipe ? 'Serving recipe' : 'Model card'}: ${config.recipe.href}`,
    weights && weights !== config.recipe.href && `Tested checkpoint: ${weights}`,
    drafter && `Tested drafter: ${drafter}`,
    settings && `Tested serving settings: ${plain(settings)}`,
    `Benchmark report: ${reportUrl(config.report)}`,
  ].filter(Boolean).join('\n');

  const followSources = hasRecipe
    ? 'Read the recipe README at the linked revision and the benchmark report. Use the recipe’s install and launch steps with the checkpoint and serving settings documented for this run.'
    : 'Read the benchmark report and model card. Use the reported runtime, checkpoint revision, and launch settings to reproduce this configuration.';

  return `Install and serve this Spark Bench configuration on my NVIDIA DGX Spark setup.

${configuration}

1. Inspect the target host or hosts first. Check the Spark count, available memory and disk, runtime prerequisites, and any port or GPU conflicts. For a multi-Spark setup, verify the node-to-node links and SSH access. Tell me what is missing if the machine or cluster does not meet the requirements.
2. ${followSources} Check the checkpoint and any drafter license for my intended use. If a documented revision or setting is unavailable, explain the difference before substituting it.
3. Install and start the model using host-specific paths and settings. Ask before interrupting an existing service or exposing the endpoint beyond the local network.
4. Verify that the API lists the model and completes a short inference request. Report the endpoint, model ID, changes made, and how to stop or restart the service.`;
}

if (catalog.schema_version !== 6) throw new Error('Unsupported benchmark catalog schema');
const models = new Map(catalog.models.map((model) => [model.id, model]));

export const baselines = catalog.baselines.map((baseline) => {
  const report = readReport(baseline.report);
  const title = plain(report.match(/^# (.+)$/m)?.[1]) || baseline.label;
  // Use the measurement date when the report distinguishes it from its date label.
  const date = report.match(/^Date: \d{4}-\d{2}-\d{2} \(measured (\d{4}-\d{2}-\d{2})\)/m)?.[1] ?? baseline.date;
  const sparks = Number(baseline.hardware.match(/^(\d+)\s*[x×]\s*NVIDIA DGX Spark/i)?.[1]);
  const model = models.get(baseline.model_id);
  if (!sparks || !model) throw new Error(`Unrecognized hardware or model in ${baseline.id}`);

  const tool = baseline.tool_eval;
  if (tool) readReport(tool.report); // Fail the build on a dangling report.
  if (baseline.external_evals) readReport(baseline.external_evals.report);
  return {
    ...baseline,
    toolOnly: Boolean(tool && !baseline.decode.length),
    ...parseContext(baseline, report),
    date,
    model,
    title,
    sparks,
    engine: baseline.runtime.startsWith('vLLM') ? 'vLLM' : baseline.runtime,
    c1: baseline.decode?.find((row) => row.concurrency === 1),
    quantization: quantization(report, title, baseline.label),
    runtimeProvenance: runtimeProvenance(report, baseline.runtime),
    recipe: recipe(baseline.recipe_credit ?? '', report),
    safetyGate: tool?.safety_passed == null ? 'unavailable' : tool.safety_passed ? 'passed' : 'failed',
    toolStatus: tool?.status ?? 'unavailable',
    comparativeTool: tool?.status === 'complete' && tool.completion_rate === 100,
  };
}).sort((a, b) => b.date.localeCompare(a.date));

export const families = [...models.values()].map((model) => ({
  ...model,
  configs: baselines.filter((baseline) => baseline.model_id === model.id),
})).filter((model) => model.configs.length > 0)
  .sort((a, b) => Number(b.configs.length > 1) - Number(a.configs.length > 1) || a.name.localeCompare(b.name));

export const engines = [...new Set(baselines.map((baseline) => baseline.engine))].sort();
export const sparkCounts = [...new Set(baselines.map((baseline) => baseline.sparks))].sort((a, b) => a - b);

export function peakDecode(points) {
  let peak;
  for (const point of points ?? []) {
    if (point.output_tps != null && (!peak || point.output_tps > peak.output_tps)) peak = point;
  }
  return peak;
}

const decode = suite.scenarios.find((scenario) => scenario.name === 'decode-c1');
const soak = suite.scenarios.find((scenario) => scenario.name.startsWith('soak-'));
const passkey = suite.scenarios.find((scenario) => scenario.name === 'needle-240k-c1');
export const decodeWorkload = `~${decode.prompt_tokens} input / ${decode.output_tokens} output tokens per request`;
export const soakWorkload = `~${soak.prompt_tokens} input / ${soak.output_tokens} output tokens per request`;
export const passkeyTokens = passkey.prompt_tokens;
export const soakMinutes = soak.duration_seconds / 60;
export const soakConcurrency = soak.concurrency;

export function benchmarkLeaders(sparks) {
  const configs = new Map(baselines.map((config) => [config.id, config]));

  function rank(measure, direction = -1) {
    // Read the same catalog series as the README charts. The site may enrich
    // individual detail pages with additional passkey evidence from reports.
    const ranked = catalog.baselines.flatMap((baseline) => {
      const config = configs.get(baseline.id);
      if (sparks != null && config.sparks !== sparks) return [];
      const result = measure(baseline);
      return Number.isFinite(result?.value) ? [{ ...result, config }] : [];
    }).sort((a, b) => direction * (a.value - b.value) || b.config.date.localeCompare(a.config.date) || a.config.id.localeCompare(b.config.id));

    const seen = new Set();
    const leaders = [];
    for (const row of ranked) {
      if (seen.has(row.config.model_id)) continue;
      seen.add(row.config.model_id);
      leaders.push(row);
      if (leaders.length === 5) break;
    }
    return leaders;
  }

  return {
    decode: rank((baseline) => {
      const peak = peakDecode(baseline.decode);
      return { value: peak?.output_tps, concurrency: peak?.concurrency };
    }),
    prefill: rank((baseline) => ({
      value: baseline.prefill?.find((point) => point.input_tokens === passkeyTokens)?.ttft_p95_seconds,
    }), 1),
    soak: rank((baseline) => {
      const result = baseline.soak;
      if (result?.minutes === soakMinutes && result.concurrency === soakConcurrency && result.errors === 0) {
        return { value: result.output_tps };
      }
    }),
  };
}
