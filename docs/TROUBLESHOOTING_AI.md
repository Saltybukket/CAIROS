# AI Troubleshooting

Run:

```bash
cairos config ai doctor
cairos config ai status
cairos config ai test
```

CAIROS never prints raw API key values. It shows only the configured
environment variable name and whether it is visible.

## HTTP Errors

401 or 403:

```text
Key missing, invalid, expired, restricted, or not allowed for this model/endpoint.
```

Check the env var in the current shell, regenerate the key, and verify account,
org or project permissions.

402:

```text
Payment required / insufficient credits.
```

For OpenRouter paid models, try:

```bash
cairos config ai use-openrouter-free
cairos config ai test
```

429:

```text
Rate limit, quota, billing, credits, or provider throttling.
```

Retry later, use a cheaper/free model, check usage/billing, or switch profiles.

404:

```text
Model or endpoint not found.
```

Check model slug and base endpoint. For Gemini, run
`cairos config ai list-models`.

Network errors usually mean connection, proxy, DNS, TLS, endpoint URL or
provider outage issues.

## Windows Notes

`setx` and PowerShell persistent environment changes require a new terminal.
For the current terminal, use `set NAME=value` in cmd.exe or
`$env:NAME="value"` in PowerShell.
