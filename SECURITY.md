# Security policy

## Supported versions

Security fixes are made on the latest commit of the default branch. This
project is a local benchmark client; operators remain responsible for securing
the inference endpoints, SSH accounts, networks, and raw benchmark artifacts
used with it.

## Reporting a vulnerability

Please use [GitHub private vulnerability reporting](https://github.com/tomrhudson/llm-serving-bench/security/advisories/new).
Do not open a public issue for a suspected vulnerability or include credentials,
private endpoints, raw model output, or internal infrastructure details in a
report.

Include the affected revision, reproduction conditions, impact, and any known
workaround. Reports about third-party models, serving runtimes, or deployment
recipes should also be sent to their respective maintainers when the issue is
outside this client.

## Safe operation

- Use HTTPS whenever bearer authentication is configured.
- Treat unauthenticated HTTP as suitable only for isolated, trusted networks.
- Use least-privilege SSH accounts for optional host telemetry.
- Keep raw JSON and generated reasoning private until manually reviewed.
- Run `python3 scripts/check_publication_hygiene.py --history` before changing
  repository visibility or publishing a release.
