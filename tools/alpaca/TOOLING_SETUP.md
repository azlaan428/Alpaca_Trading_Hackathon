---
title: "Alpaca Tooling Setup — Paper Trading Hackathon"
author: "Hadrian Hu"
date: "2026-08-19"
version: "2026.1.0.0"
keywords: ["alpaca", "paper-trading", "sdk", "go", "rust", "python", "mcp", "cli"]
---

# Alpaca Tooling Setup

## Submodule Map

| Path | Source | Language | Purpose |
|:-----|:-------|:---------|:--------|
| `tools/alpaca/alpaca-py` | `alpacahq/alpaca-py` | Python | Official Python SDK v3+ |
| `tools/alpaca/alpaca-trade-api-python` | `alpacahq/alpaca-trade-api-python` | Python | Legacy Python SDK (reference) |
| `tools/alpaca/alpaca-trade-api-go` | `alpacahq/alpaca-trade-api-go` | Go | Official Go client |
| `tools/alpaca/alpaca-mcp-server` | `alpacahq/alpaca-mcp-server` | Python | Official MCP server for VS Code / Claude |
| `tools/alpaca/cli` | `alpacahq/cli` | Go | Official CLI for paper trading |

## Python Environment

Virtual environment: `.venv-alpaca-trading` (at repo root)

```powershell
# Activate
.\.venv-alpaca-trading\Scripts\Activate.ps1

# Packages installed
# alpaca-py 0.44.0
# python-dotenv
```

## MCP Server (VS Code)

Config: `.vscode/mcp.json` — uses `uvx alpaca-mcp-server` with `ALPACA_PAPER_TRADE=true`.
Credentials are prompted at session start (never stored in files).

Prerequisites:
- `uv` / `uvx` installed (v0.11+ confirmed available)
- Restart VS Code after adding keys to pick up the new MCP server

## Alpaca CLI

Installed via: `go install github.com/alpacahq/cli/cmd/alpaca@latest`
Binary: `$env:USERPROFILE\go\bin\alpaca.exe`

```powershell
alpaca profile login --api-key   # authenticate with paper keys
alpaca account get               # verify connectivity
alpaca clock                     # check market status
```

## Go SDK

Source: `tools/alpaca/alpaca-trade-api-go` (submodule, pinned to v3.9.1+)

To use in a Go module:
```go
import alpaca "github.com/alpacahq/alpaca-trade-api-go/v3/alpaca"
```

Set env before running:
```powershell
$env:APCA_API_KEY_ID = "PK..."
$env:APCA_API_SECRET_KEY = "..."
$env:APCA_API_BASE_URL = "https://paper-api.alpaca.markets"
```

## Rust — Status: No Official Client

Per `api_refs_paper_trading.md §4.3`: "Reference official or community Alpaca Rust
client on GitHub before implementing."

Checked `github.com/alpacahq` on 2026-08-19: **no official Rust SDK exists**.

Community options to evaluate before implementation:
- Search crates.io for `alpaca` to find current best-maintained crate.
- Fallback: implement a thin `reqwest`-based HTTP client against
  `paper-api.alpaca.markets` following the REST spec directly.

**Do not implement a Rust client until one has been evaluated per spec §4.3.**

## Credentials

Copy `.env.example` → `.env` and populate. The `.env` file is gitignored.
Never commit real API keys.

## Changelog

| Version | Date | Author | Description |
|:--------|:-----|:-------|:------------|
| 2026.1.0.0 | 2026-08-19 | Hadrian Hu | Initial tooling setup: 5 submodules, venv, MCP, CLI, Go SDK, Rust note |
