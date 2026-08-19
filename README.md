# VoiceGate

**Company:** Not yet confirmed (open item) &nbsp;|&nbsp; **Category:** Voice Compliance QA (VCQ, proposed) &nbsp;|&nbsp; **Status:** Hackathon-stage development

An automated compliance and red-team test bench for voice AI agents: simulates callers across
a range of personas and adversarial scenarios, runs each through a five-phase call lifecycle,
transcribes both sides of the conversation, and scores the target agent against statutory
requirements (verification-flagged) and the target company's own published terms, producing a
Pass/Fail/Flag verdict with an explicit rule citation and an advisory-only suggested
system-prompt patch on failure.

Intended for an assumed **LabLab AI Factory** hackathon submission using **Natively AI** (window
inherited from a sibling project, not yet independently confirmed). This repository
(`X_Voice_X`, a `py.typed` Python package) is the authoritative backend implementation target,
not a disposable planning artifact.

## Table of Contents

- [About](#about)
- [Documentation](#documentation)
- [Getting Started](#getting-started)
- [Project Status](#project-status)
- [Contributing](#contributing)
- [Security](#security)
- [License](#license)

## About

See [ABOUT.md](ABOUT.md) for the full product identity, elevator pitch, and project origin.

## Documentation

All product, design, and engineering specifications live in
[`voice_processing_specifications/`](voice_processing_specifications/), governed by a binding
documentation standard (`0000_documentation_standards.txt`). Start at the master index:

- [`voice_processing_specifications/000_index.txt`](voice_processing_specifications/000_index.txt) — full document map
- [`voice_processing_specifications/001_voice_transcription_concept.txt`](voice_processing_specifications/001_voice_transcription_concept.txt) — product identity, concept, MVP scope, open items
- [`voice_processing_specifications/017_voicegate_scoring_rules.txt`](voice_processing_specifications/017_voicegate_scoring_rules.txt) — authoritative scoring/verdict engine

## Getting Started

1. Set up the Python virtual environment per [`voice_processing_specifications/007_voicegate_virtual_env.txt`](voice_processing_specifications/007_voicegate_virtual_env.txt).
2. Review the repository scaffolding in [`voice_processing_specifications/006_voicegate_scaffolding.txt`](voice_processing_specifications/006_voicegate_scaffolding.txt).
3. Review coding standards in [`voice_processing_specifications/005_voicegate_coding_standards.txt`](voice_processing_specifications/005_voicegate_coding_standards.txt) before opening a Pull Request.

## Project Status

Active hackathon-stage development (assumed LabLab AI Factory / Natively AI, window not yet
confirmed). No versioned release has shipped yet; see [SECURITY.md](SECURITY.md) for the
supported-version policy and [`voice_processing_specifications/015_voicegate_deployment.txt`](voice_processing_specifications/015_voicegate_deployment.txt) for the deployment plan.

## Contributing

Contributions are welcome via **mandatory fork-and-Pull-Request** (direct pushes to upstream are not accepted). See [CONTRIBUTION.md](CONTRIBUTION.md) for the full workflow, coding standards, and testing requirements.

## Security

To report a vulnerability, do not open a public issue — see [SECURITY.md](SECURITY.md) for the private reporting process.

## License

See [LICENSE.md](LICENSE.md) for full license terms.
