  

# About xquantx

> **Current project notice (2026-08-28).** The active project is **X Quant X**, a
> quantitative paper-trading and market-intelligence platform. This document's
> remaining Voice Compliance QA content is preserved as a historical baseline and
> must not be treated as the current product definition. The canonical source is
> `alpaca_paper_trading_specifications_x_quant_x/001_xquantx_concept.txt`.

## Current Project Facts

X Quant X ingests live and historical market data, estimates market regimes, applies
risk gates, and submits paper orders through the Alpaca API. The MVP includes Alpaca
paper trading, a P&L and risk-audit dashboard, optional backtesting, and options paper
trading. Live-money trading is explicitly out of scope.

## Company

**Not yet confirmed** — no company/brand name has been supplied for this project (unlike the
sibling project's confirmed "X Dark X"); this is an open item pending stakeholder
confirmation (see `alpaca_paper_trading_specifications_x_quant_x/001_voice_transcription_concept.txt §1.9`).

## Category

**Voice Compliance QA (VCQ)** — a proposed descriptive category, not a confirmed brand
decision, for automated compliance and red-team testing of voice AI agents.

## Title

**xquantx** — an automated test bench that red-teams a target voice AI agent by simulating
callers across a range of personas and adversarial scenarios, then scores the resulting
conversation against both statutory requirements and the target company's own published terms.

## Elevator Pitch

xquantx runs a target voice agent through a scenario gauntlet: simulated callers vary by
age, emotional state, and adversarial style; each call proceeds through a five-phase lifecycle
(Greeting, Intent Discovery, Resolution Attempt, Compliance Check, Wrap-up); both sides of the
call are transcribed; and the transcript is scored against (a) statutory/regulatory
requirements (e.g. EU AI Act Article 50, California SB 243 — both verification-flagged,
citation-needed) and (b) the target company's own published Terms & Conditions. Every call
receives a Pass/Fail/Flag verdict with an explicit rule citation; a Fail triggers an
advisory-only Suggested Patch Adviser that proposes a system-prompt fix and re-runs the
gauntlet to verify it, never auto-applying a patch without human confirmation. The full
scoring/verdict engine is authoritative in
`alpaca_paper_trading_specifications_x_quant_x/017_xquantx_scoring_rules.txt`.

## Origin

xquantx's repository (`X_Voice_X`) was forked on 2026-08-03 from the sibling project
`DarkStrategy_XParadoxX` ("X Paradox X") per team-lead guidance recorded in
`voice_transcription_concept/voice_chat_concept.md`. The entire `alpaca_paper_trading_specifications_x_quant_x/`
corpus (33 files, formerly `game_specifications/`) was repurposed from game design/mechanics
content to xquantx compliance-testing content while retaining the sibling project's
documentation standards, engineering conventions, and process discipline. See
`alpaca_paper_trading_specifications_x_quant_x/000_index.txt` for the complete document map and its
Reconciliation Table for the full game-to-xquantx repurposing mapping, and
`alpaca_paper_trading_specifications_x_quant_x/001_voice_transcription_concept.txt §1.8` for the product-level
reconciliation.

## Hackathon Context

This repository is intended as the real, shipping Python backend (marked `py.typed`, not a
disposable planning artifact) for an assumed **LabLab AI Factory** hackathon submission, built
using **Natively AI** — this hackathon window (2026-08-03 to 2026-08-10) is inherited from the
sibling project and is an open item pending confirmation. See
`alpaca_paper_trading_specifications_x_quant_x/0001_natively_ai_prompt.txt` for the opening-day master prompt
and delivery pacing plan.

## Project Status

Active, hackathon-stage development. See `alpaca_paper_trading_specifications_x_quant_x/014_xquantx_cicd.txt`
and `015_xquantx_deployment.txt` for the CI/CD and release process, and [SECURITY.md](SECURITY.md)
for the current supported-version policy.

## License

See [LICENSE.md](LICENSE.md) for the full license terms, including any mandatory-fork
contribution policy inherited from the sibling project pending confirmation for xquantx.

## Contributing

See [CONTRIBUTION.md](CONTRIBUTION.md) for the fork-and-Pull-Request workflow, coding
standards, and testing requirements.

## Learn More

- Full specification index: `alpaca_paper_trading_specifications_x_quant_x/000_index.txt`
- Product concept, brand identity, and open items: `alpaca_paper_trading_specifications_x_quant_x/001_voice_transcription_concept.txt`
- Scoring/verdict engine (single source of truth for mechanics): `alpaca_paper_trading_specifications_x_quant_x/017_xquantx_scoring_rules.txt`

## Reconciliation

| Historical statement | Current canonical fact | Authority |
| --- | --- | --- |
| xquantx is a voice-compliance test bench | X Quant X is a quantitative paper-trading platform | `001_xquantx_concept.txt` Sections 1.1 and 1.3 |
| Natively AI is a project dependency | Alpaca paper-trading tools are the primary API dependency | `001_xquantx_concept.txt` Section 1.4.3 |
| Voice-call scoring is the core product workflow | Market-data processing, risk gating, and paper-order execution are the core workflow | `001_xquantx_concept.txt` Section 1.7 |

## Changelog

| Version | Date | Author | Description |
| --- | --- | --- | --- |
| 2026.8.28.1 | 2026-08-28 | GitHub Copilot | Added current X Quant X product reconciliation; preserved prior product wording as a historical baseline. |
