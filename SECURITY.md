# Security Policy

## What Holds is (and is not)

Holds is a **local / CI evaluation harness** for LLM agent task quality.

It launches user-provided commands, reads result artifacts, and may import trusted custom grader callables. It is **not** a sandbox, production gateway, or hosted prompt store.

## Credentials and sensitive data

- Keep API keys in the environment or a secret manager. Never commit `.env`, live suite secrets, or provider credentials.
- Reports omit raw agent outputs by default. Use `--include-outputs` only when you accept the sensitivity risk.
- Treat suite inputs, captured stdout/stderr tails, and result artifacts as potentially sensitive. Prefer scrubbed fixtures in version control.
- Do not log `Authorization`, API keys, cookies, or unredacted customer content in CI artifacts.

## Subprocess and custom grader trust boundary

- `agent.command` executes as a shell command under the privileges of the user/CI runner.
- `python` graders load `module:function` callables from the local environment and suite directory.
- Holds does **not** isolate, jail, or capability-restrict that code. Review suites and grader modules like any other executable CI dependency.

## Optional Maul integration

When `--enable-maul` is used, Holds may launch the Maul binary and attach resilience reports. Follow [Maul's security policy](https://github.com/invariant-sh/maul/blob/main/SECURITY.md): local/CI only, no public edge exposure, never log forwarded credentials.

## Reporting a vulnerability

If you believe you found a security issue in Holds:

1. **Do not** open a public GitHub issue with exploit details.
2. Open a [private security advisory](https://github.com/invariant-sh/holds/security/advisories/new) on this repository.
3. Include: Holds version/commit, reproduction steps, and impact.

We aim to acknowledge reports within a few business days.

## Safe defaults for operators

- Run Holds on trusted suites in local or CI environments.
- Keep live-provider smoke workflows opt-in and secret-gated.
- Rotate any key that may have been pasted into a shell history, issue, or commit by mistake.
