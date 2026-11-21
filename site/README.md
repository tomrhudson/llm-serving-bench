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

## Cloudflare Pages

Use the existing GitHub repository with these settings.

| Setting | Value |
|---|---|
| Production branch | `main` |
| Framework preset | None |
| Root directory | Repository root |
| Build command | `npm --prefix site ci && npm --prefix site run build` |
| Build output directory | `site/dist` |
| Production and preview variables | `NODE_VERSION=22`, `ASTRO_TELEMETRY_DISABLED=1` |
| Build watch includes | `site/*`, `results/*`, `configs/qwen-native-standard.json` |
| Build watch excludes | Empty |

Verify the site branch's preview and open a configuration URL directly before
merging the PR. After the production deployment serves those same routes over
HTTPS on the project's `pages.dev` hostname, check the Cloudflare zone and
existing apex DNS. Attach `tomrhudson-ai.com` through Pages Custom domains and
verify the certificate, catalog, and a configuration route on the custom host.
