If you have a paper account, you can call:

* * Trading API endpoints on `<span class="cm-s-material-palenight" data-testid="SyntaxHighlighter">paper-api.alpaca.markets</span>`
  * Market Data API endpoints on `<span class="cm-s-material-palenight" data-testid="SyntaxHighlighter">data.alpaca.markets</span>`

[docs.alpaca.markets/us/docs/getting-started](https://docs.alpaca.markets/us/docs/getting-started) -- for more information on paper trading API requests.

**WE should also add cli, api, sdk, MCP in VS Code support for Go, Rust as part of tooling series submodules: for GOLANG, Rust, and others. Check GitHub for alpaca.**

---

## AI Agent Instructions — Paper Trading API (Strictly Enumerated, Hierarchical)

### 1. Endpoint Configuration

1.1. Use `paper-api.alpaca.markets` for ALL Trading API calls.
1.2. Use `data.alpaca.markets` for ALL Market Data API calls.
1.3. Never mix paper and live endpoint base URLs in the same agent session.
1.4. Never assume an endpoint — verify against this document before making any request.

### 2. Authentication

2.1. Every request MUST include the following HTTP headers:

- 2.1.1. `APCA-API-KEY-ID`: Paper account API key ID.
- 2.1.2. `APCA-API-SECRET-KEY`: Paper account API secret key.

2.2. Do NOT use live account credentials against paper endpoints.
2.3. Do NOT hardcode credentials in source files; read from environment variables only.

### 3. Request Construction

3.1. Use HTTPS exclusively; reject any HTTP-only configurations.
3.2. Set `Content-Type: application/json` for all POST/PATCH/PUT requests.
3.3. Validate all request parameters against the official Alpaca API schema before sending.
3.4. Do not invent or guess query parameters; only use documented parameters.

### 4. Tooling & SDK Usage

4.1. Python SDK: Use `alpaca-trade-api` or `alpaca-py`; confirm which is installed before import.
4.2. Go (GOLANG): Reference official Alpaca Go client on GitHub (`alpacahq/alpaca-trade-api-go`).
4.3. Rust: Reference official or community Alpaca Rust client on GitHub before implementing.
4.4. CLI: Use Alpaca's official CLI tooling if available; do not build ad-hoc CLI wrappers without confirming no official tool exists.
4.5. For any language not listed above, check `github.com/alpacahq` for an official client before using a third-party library.

### 5. Error Handling

5.1. On HTTP 4xx: Log the full response body; do NOT retry without fixing the request.
5.2. On HTTP 429 (rate limit): Back off exponentially; minimum wait = 1 second; maximum retries = 5.
5.3. On HTTP 5xx: Retry up to 3 times with exponential backoff; alert if all retries fail.
5.4. Never silently swallow errors; every exception must be logged with the originating request details.

### 6. Order Management

6.1. Confirm account is in paper mode before placing any order.
6.2. Validate symbol existence and tradability before order submission.
6.3. Do not place market orders outside market hours unless `extended_hours: true` is explicitly set and the asset supports it.
6.4. Always record the returned `order_id` for every submitted order.

### 7. Data Integrity

7.1. Do not cache market data for more than 60 seconds for real-time decisions.
7.2. Always timestamp data retrieval; never use data of unknown age.
7.3. Cross-validate prices from `data.alpaca.markets` before acting; do not act on a single data point anomaly.

### 8. Reference

8.1. Primary documentation: [docs.alpaca.markets/us/docs/getting-started](https://docs.alpaca.markets/us/docs/getting-started)
8.2. GitHub organization: [github.com/alpacahq](https://github.com/alpacahq)
8.3. If a behavior is undocumented, do NOT assume it is permitted — halt and request human clarification.
