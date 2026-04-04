# Security Policy

## Supported Versions

| Version | Supported      |
|---------|----------------|
| 0.2.x   | ✓ Current      |
| 0.1.x   | ✓ LTS          |

## Reporting a Vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

Report via GitHub Security Advisories:
**https://github.com/inteleion-ai/Agentability/security/advisories/new**

Or email: **hello@agentability.io** (subject: `[SECURITY] <short description>`)

Include as much of the following as possible:

- A description of the vulnerability and its potential impact.
- Steps to reproduce or proof-of-concept code.
- Any suggested mitigations.

You will receive an acknowledgement within **48 hours**. We aim to release a
fix within **14 days** of a confirmed critical vulnerability.

We follow responsible disclosure: we will publicly credit reporters (unless
they prefer to remain anonymous) after the fix is released.

## Scope

The following are in scope:

- The `agentability` Python package (`sdk/python/`).
- The FastAPI platform server (`platform/`).
- The React dashboard (`dashboard/`).

The following are **out of scope**:

- Third-party dependencies (report those directly to the upstream project).
- Issues requiring physical access to a machine.
- Social engineering attacks.

## Security Best Practices

When deploying Agentability:

- Always set `AGENTABILITY_API_KEY` to a strong, randomly-generated secret.
- Use HTTPS / TLS 1.3 for all network traffic.
- Restrict database access to the application user only.
- Enable PII redaction in `PolicyEvaluator` for any system processing user data.
- Review the default `no_pii` and `max_cost` rules and extend for your
  compliance requirements.
- Never commit `agentability.db` or any `.db` file — add to `.gitignore`.
