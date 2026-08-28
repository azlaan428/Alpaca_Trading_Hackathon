# Security Policy

> **Current project notice (2026-08-28).** This policy applies to **X Quant X**, a
> quantitative paper-trading platform. The voice-agent security examples retained
> below are historical baseline content, not a statement of current product scope.
> Current scope is defined in `alpaca_paper_trading_specifications_x_quant_x/001_xquantx_concept.txt`.

## Current Security Scope

Priority reports include authentication or authorization defects, exposed credentials,
dependency vulnerabilities, market-data integrity defects, risk-gate bypasses,
unauthorized Alpaca paper-order placement, audit-log tampering, and dashboard data
exposure. The MVP has no live-money trading capability.

## Supported Versions

`xquantx` is currently in active hackathon-stage development (assumed LabLab AI Factory / Natively AI, 2026-08-03 to 2026-08-10, window inherited from a sibling project and not yet independently confirmed) and has not yet reached a tagged `1.0.0` release. Security fixes are applied to the `main` branch only until a formal release cadence is established.

| Version | Supported |
| ------- | --------- |
| `main` (pre-release / hackathon build) | :white_check_mark: |
| Any tagged release prior to `1.0.0` | :x: |

This table will be revised once versioned releases begin, per `alpaca_paper_trading_specifications_x_quant_x/015_xquantx_deployment.txt`.

## Reporting a Vulnerability

We take the security of `xquantx` and its Python backend seriously. If you discover a security vulnerability, **please do not open a public GitHub issue**.

Instead, report it privately using one of the following channels, in order of preference:

1. **GitHub Private Vulnerability Reporting** — Use the "Report a vulnerability" button under the **Security** tab of this repository (`psi16181918161phi/X_Voice_X`). This is the preferred channel and creates a private advisory visible only to maintainers.
2. **Direct maintainer contact** — Open a private message to the maintainer, `@psi16181918161phi`, on GitHub if the Security tab is unavailable to you.

Please include as much of the following as possible:

- A clear description of the vulnerability and its potential impact;
- Steps to reproduce, proof-of-concept code, or a minimal reproduction case;
- The affected file(s), module(s), or commit/branch;
- Any known mitigations or workarounds.

### What to expect

| Stage | Target Timeline |
| ----- | ---------------- |
| Initial acknowledgement | Within 5 business days |
| Triage and severity assessment | Within 10 business days of acknowledgement |
| Fix or mitigation plan communicated to reporter | Within 30 days of triage, severity-dependent |
| Public disclosure (coordinated with reporter) | After a fix is released, or by mutual agreement |

These are target timelines for a small, hackathon-stage project, not contractual SLAs.

### Scope

In scope:

- The Python backend implementing xquantx's call orchestration, transcription, scoring/verdict engine, and guardrails (prompt-injection and actor/speaker-role-confusion resistance), including any operating-mode components introduced per `alpaca_paper_trading_specifications_x_quant_x/016_xquantx_operating_modes.txt`;
- Build, packaging, and CI/CD configuration under `alpaca_paper_trading_specifications_x_quant_x/014_xquantx_cicd.txt` and `015_xquantx_deployment.txt`;
- Dependency and supply-chain issues (e.g., vulnerable third-party packages declared in the project's virtual environment per `alpaca_paper_trading_specifications_x_quant_x/007_xquantx_virtual_env.txt`);
- Guardrail bypass reports (e.g., a crafted transcript that causes the scoring/verdict engine to execute injected instructions instead of treating transcript content as untrusted data) are treated as **high-priority security vulnerabilities**, not ordinary bugs.

Out of scope:

- Scoring-calibration disagreements or verdict-threshold tuning requests that are not themselves a security vulnerability;
- Denial-of-service reports that require unrealistic resource assumptions;
- Issues in third-party dependencies that are already publicly disclosed and awaiting an upstream fix (please report those upstream instead).

### Disclosure Policy

We follow **coordinated disclosure**: please give us a reasonable opportunity to investigate and remediate an issue before any public disclosure. We will credit reporters (unless anonymity is requested) once a fix is released, consistent with the attribution terms in [LICENSE.md](LICENSE.md).

### Safe Harbor

We will not pursue legal action against security researchers who make a good-faith effort to comply with this policy, report privately, avoid privacy violations and data destruction, and give us reasonable time to remediate before any public disclosure.

## Reconciliation

| Retained baseline scope | Current X Quant X scope | Authority |
| --- | --- | --- |
| Voice-agent guardrail bypass | Risk-gate bypass, paper-order authorization, market-data integrity, and audit-log integrity | `001_xquantx_concept.txt` Sections 1.3 and 1.9 |
| Voice-call orchestration | Alpaca paper-trading order workflow | `001_xquantx_concept.txt` Section 1.7 |

## Changelog

| Version | Date | Author | Description |
| --- | --- | --- |
| 2026.8.28.1 | 2026-08-28 | GitHub Copilot | Added current X Quant X security scope and historical-baseline reconciliation. |
