# Spark Bench

Static Astro site for the published DGX Spark serving benchmarks. The build
uses [the catalog](../results/catalog.json), its linked serving and tool-eval
reports, and [the standard workload](../configs/qwen-native-standard.json).
Each catalog baseline ID has a permanent path at `/models/<id>/`.

## Local build

Run from the repository root with Node 22.12 or newer.

```sh
npm --prefix site ci
ASTRO_TELEMETRY_DISABLED=1 npm --prefix site run build
npm --prefix site run preview
```

Update the catalog and curated reports through the existing results workflow.
The site reads the structured measurements from the catalog and extracts
provenance and passkey evidence from the serving reports. Keep new report
metadata under labeled fields such as `Runtime:`, `Quantization:`, and
`Configured context:`. Record passkey outcomes explicitly. Use a pinned
recipe link in `recipe_credit` when the exact revision was known.

## Appearance

The Astro templates use HeroUI styles for buttons, cards, and chips. The shared
layout defaults to the browser's system color preference. Visitors can choose
Light or Dark in the header, and that override is saved in their browser.
Choose System to resume following the device setting.

## Installation prompts

The **Install model** button on the homepage’s latest benchmark card, catalog
cards, and benchmark pages opens a prompt visitors can copy and give to an AI
assistant. Prompts use the tested configuration, recipe and benchmark report.
Where the report supplies launch settings in place of a recipe repository, the
prompt uses the report and model card.

## Cloudflare Pages

[Production](https://tomrhudson-ai.com/) also serves from
[llm-serving-bench.pages.dev](https://llm-serving-bench.pages.dev/).

| Setting | Live value |
|---|---|
| Pages project | `llm-serving-bench` |
| Git provider and repository | GitHub · `tomrhudson/llm-serving-bench` |
| Production branch | `main`, automatic deployments enabled |
| Preview branches | All non-production branches |
| Pull request comments | Enabled |
| Framework preset | None |
| Root directory | Repository root |
| Build command | `npm --prefix site ci && npm --prefix site run build` |
| Build output directory | `site/dist` |
| Production and preview variables | `NODE_VERSION=22.23.5`, `ASTRO_TELEMETRY_DISABLED=1`, `SKIP_DEPENDENCY_INSTALL=1` |
| Build watch includes | `site/*`, `results/*`, `configs/qwen-native-standard.json` |
| Build watch excludes | Empty |
| Pages custom domain | `tomrhudson-ai.com` |
| Apex DNS record | Proxied CNAME `@` → `llm-serving-bench.pages.dev`, TTL Auto |

The build command installs the pinned dependencies under `site/`. The
Cloudflare Workers & Pages GitHub app needs access to
`tomrhudson/llm-serving-bench` in its selected repositories for pushes to
trigger builds.

For a pull request, open its Pages preview and load the catalog and a
configuration link directly. After merging, confirm Pages records a
`github:push` production deployment for the merge commit, then check HTTPS
and those same routes at `tomrhudson-ai.com`.
