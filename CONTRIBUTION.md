# Contributing to xquantx

Thank you for your interest in contributing to **xquantx**, an automated compliance and red-team test bench for voice AI agents (company name not yet confirmed; category proposed as **Voice Compliance QA (VCQ)**). This document explains how to propose changes, the rules that govern contributions, and the standards your contribution must meet.

Before contributing, please read [LICENSE.md](LICENSE.md) in full — it is not a standard open-source license, and contributing implies you accept its terms, including Section 2.3 (Contribution License Grant).

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Licensing and the Mandatory Fork Policy](#licensing-and-the-mandatory-fork-policy)
- [Ways to Contribute](#ways-to-contribute)
- [Before You Start](#before-you-start)
- [Development Setup](#development-setup)
- [Coding and Documentation Standards](#coding-and-documentation-standards)
- [Testing Requirements](#testing-requirements)
- [Commit Message Conventions](#commit-message-conventions)
- [Branch Naming](#branch-naming)
- [Pull Request Process](#pull-request-process)
- [Reporting Issues](#reporting-issues)
- [Reporting Security Vulnerabilities](#reporting-security-vulnerabilities)
- [Contributor Recognition](#contributor-recognition)

## Code of Conduct

Be respectful, assume good faith, and keep discussion focused on the work. Harassment, personal attacks, and discriminatory language are not tolerated in issues, Pull Requests, or any project space. Violations may result in removal of comments, rejection of contributions, or a ban from the repository at maintainer discretion.

## Licensing and the Mandatory Fork Policy

`xquantx` is source-available under a modified CC BY-NC 4.0 license (see [LICENSE.md](LICENSE.md)), not a permissive open-source license. Two consequences follow directly for contributors:

1. **Forking is mandatory.** All contributions — code, tests, documentation, or `alpaca_paper_trading_specifications_x_quant_x/` edits — must be made from a personal fork of `psi16181918161phi/X_Voice_X`, on a branch in that fork, submitted upstream as a Pull Request. This is the mechanism by which every contribution is permanently attributed to its author in Git and GitHub history (LICENSE.md §2.2).
2. **You license your contribution to the confirmed copyright holder** (LICENSE.md §2.1, once named), per LICENSE.md §2.3, while retaining your own copyright and the right to reuse your own contribution elsewhere under the terms of Section 1.

Direct commits or pushes to upstream branches by non-maintainers are not accepted, even for trivial fixes.

## Ways to Contribute

- **Bug reports** — reproducible defects in call orchestration, the scoring/verdict engine, guardrails, or tooling.
- **Bug fixes** — Pull Requests that resolve an open, triaged issue.
- **New features** — please open an issue to discuss scope *before* investing significant work; not all proposals fit the MVP boundaries in `alpaca_paper_trading_specifications_x_quant_x/001_voice_transcription_concept.txt §1.10`.
- **Tests** — additional unit (`009`), integration (`011`), performance (`012`), or end-to-end (`013`) coverage, including guardrail (prompt-injection/actor-role-confusion) test cases.
- **Documentation** — corrections or additions to `alpaca_paper_trading_specifications_x_quant_x/`, always compliant with `0000_documentation_standards.txt`.
- **Triage** — helping label, reproduce, and prioritize open issues.

## Before You Start

1. Search existing issues and Pull Requests to avoid duplicate work.
2. For anything beyond a small fix, open an issue describing the problem and your proposed approach, and wait for maintainer feedback.
3. Read the relevant specification file(s) in `alpaca_paper_trading_specifications_x_quant_x/` — this repository treats them as the single source of truth (see `alpaca_paper_trading_specifications_x_quant_x/000_index.txt`). Code that contradicts an existing spec will not be merged without a corresponding spec update in the same Pull Request.

## Development Setup

1. Fork the repository and clone your fork.
2. Set up the Python virtual environment exactly as described in `alpaca_paper_trading_specifications_x_quant_x/007_xquantx_virtual_env.txt`.
3. Follow the package/module layout in `alpaca_paper_trading_specifications_x_quant_x/006_xquantx_scaffolding.txt` — do not introduce new top-level packages without discussion.

## Coding and Documentation Standards

- **Code style**: `alpaca_paper_trading_specifications_x_quant_x/005_xquantx_coding_standards.txt` (SOLID, ACID, JPL Power-of-Ten, and Clean Code discipline).
- **Modules and imports**: `alpaca_paper_trading_specifications_x_quant_x/023_xquantx_modules_imports.txt`.
- **Naming conventions**: `alpaca_paper_trading_specifications_x_quant_x/024_xquantx_naming_conventions.txt`.
- **Data structures and algorithms**: `alpaca_paper_trading_specifications_x_quant_x/019_xquantx_data_structures_algorithms.txt`.
- **Logging**: `alpaca_paper_trading_specifications_x_quant_x/020_xquantx_logging_standards.txt`.
- **Data formats**: `alpaca_paper_trading_specifications_x_quant_x/021_xquantx_data_standards.txt`.
- **Specification edits**: must comply with `alpaca_paper_trading_specifications_x_quant_x/0000_documentation_standards.txt` in full (table of contents, abstract, hierarchical enumeration, summary/reconciliation tables, changelog). **Never delete existing text** in a specification file — extend or reconcile it instead, per that file's own binding instruction.

## Testing Requirements

Every Pull Request that changes behavior must include or update tests, per the applicable tier:

- Unit tests: `alpaca_paper_trading_specifications_x_quant_x/009_xquantx_unit_tests.txt`
- Integration tests: `alpaca_paper_trading_specifications_x_quant_x/011_xquantx_integration_tests.txt`
- Performance tests (if touching hot paths): `alpaca_paper_trading_specifications_x_quant_x/012_xquantx_performance_tests.txt`
- End-to-end tests (if touching UI/call-flow): `alpaca_paper_trading_specifications_x_quant_x/013_xquantx_end2end_testing.txt`

All tests must pass locally and in CI (`alpaca_paper_trading_specifications_x_quant_x/014_xquantx_cicd.txt`) before review, including the mandatory guardrail-test-suite gate.

## Commit Message Conventions

Use [Conventional Commits](https://www.conventionalcommits.org/) style:

```
<type>(<scope>): <short summary>

[optional body]

[optional footer(s)]
```

Common `<type>` values: `feat`, `fix`, `docs`, `test`, `refactor`, `perf`, `chore`, `ci`. Example: `fix(scoring-engine): correct rule-citation lookup for CA SB 243`.

## Branch Naming

Use `<type>/<short-description>` on your fork, e.g. `feat/persona-catalog-extension`, `fix/verdict-scoring-off-by-one`, `docs/017-scoring-rules-clarification`.

## Pull Request Process

1. Push your branch to your fork and open a Pull Request against `main` on `psi16181918161phi/X_Voice_X`.
2. Fill in the Pull Request template (what changed, why, linked issue, testing performed).
3. Ensure CI is green (`alpaca_paper_trading_specifications_x_quant_x/014_xquantx_cicd.txt` gates).
4. Address review feedback; at least one maintainer approval is required before merge.
5. Maintainers merge via squash-merge to keep `main` history linear; your original commits remain visible in your fork.

## Reporting Issues

Open a GitHub issue with a clear title, reproduction steps (if a bug), expected vs. actual behavior, and environment details. For product-design disagreements, cite the relevant `alpaca_paper_trading_specifications_x_quant_x/` section rather than re-arguing scoring behavior from first principles — propose a reconciliation edit instead.

## Reporting Security Vulnerabilities

Do **not** open a public issue for security vulnerabilities. See [SECURITY.md](SECURITY.md) for the private reporting process.

## Contributor Recognition

Because all contributions arrive via fork and Pull Request (LICENSE.md §2.2), your authorship is preserved permanently in this repository's Git and Pull Request history. Significant contributors may also be listed in [ABOUT.md](ABOUT.md) at maintainer discretion.
