# Comprehensive Survey Report: x402-mcp Repository & MCP Architecture

**Date**: 2026-08-21  
**Investigator**: `survey_explorer_1`  
**Repository**: `C:/Users/Keith/x402-mcp` (`kwizzlesurp10/x402-mcp`)  
**Mission Objective**: Map out the complete repository architecture, files, tools, schemas, build/test scripts, and MCP configuration.

---

## 1. Executive Summary

`x402-mcp` is a production-grade FastAPI + FastMCP server that provides pay-per-call HTTP APIs and Model Context Protocol (MCP) tools over the **x402** micropayment protocol (EIP-3009 transfer authorizations in USDC on Base mainnet `eip155:8453` and Base Sepolia `eip155:84532`).

Key capabilities include:
- **19 MCP Tools** across buyer, seller, fiat (Stripe), autonomous swarm agency, Base blockchain telemetry/gas optimization, and US city open-data property compliance screening.
- **Transports**: `stdio` (`run_stdio.py`), `streamable-http` (`/mcp/mcp` mounted at `/mcp`), and `sse` (`/mcp/sse`).
- **Commerce & Quota Layer**: Preemptive rate-limiting and monthly quota tracking (in-memory or Redis) returning a mandatory `ResponseMeta` envelope on every MCP call.
- **Storefront & Discovery**: Auto-generated live machine surfaces (`/.well-known/mcp`, `/.well-known/x402`, `/.well-known/agent-card.json`, `/.well-known/agents.json`, `/.well-known/mcp/server-card.json`, `/llms.txt`).
- **Mission Control SPA**: React 19 + TypeScript + Vite dashboard bundled into Docker/static hosting.
- **Publishing & Registries**: Configured for Smithery.ai (`smithery.yaml`), MCP Registry (`server.json` via GitHub OIDC action), Cursor (`manifests/cursor-mcp.json`), and Claude Desktop (`.mcp.json.example`).

---

## 2. Repository File & Directory Layout

```
C:/Users/Keith/x402-mcp/
├── .claude/                             # Claude Code configuration & agent definitions
│   ├── agents/                          # Subagent role specs (archivist, merchant, scout, treasurer, warden, etc.)
│   └── settings.local.json
├── .github/
│   └── workflows/
│       ├── ci.yml                       # GitHub Actions CI (Python 3.12 pytest + Vitest)
│       ├── mcp-registry-publish.yml     # MCP Registry publication via mcp-publisher + GitHub OIDC
│       ├── sale-watch.yml               # Settle/sale monitor workflow
│       ├── storefront-monitor.yml       # Storefront health probe workflow
│       ├── task-watch.yml               # Async task watch workflow
│       └── thread-watch.yml             # Conversation thread watch workflow
├── app/                                 # Main Python backend application
│   ├── adapters/                        # Cross-protocol external adapters
│   │   ├── nevermined_adapter.py        # Nevermined protocol adapter
│   │   └── olas_mech_adapter.py         # Autonolas / Olas Mech adapter
│   ├── city_compliance/                 # US City Open-Data Compliance Network (14 jurisdictions)
│   │   ├── cities/                      # Per-city open-data adapters (mn, sea, nyc, chi, den, sf, lax, bos, phi, orl, nola, moco, gain, kc)
│   │   ├── carto.py                     # Carto SQL API connector
│   │   ├── ckan.py                      # CKAN open data connector
│   │   ├── socrata.py                   # Socrata SODA API connector
│   │   ├── gate.py                      # 402 challenge builder & verification gate
│   │   ├── mcp_tools.py                 # City compliance MCP tool handlers
│   │   ├── models.py                    # City compliance data models & Pydantic schemas
│   │   ├── registry.py                  # City jurisdiction registry singleton
│   │   └── routes.py                    # FastAPI routes under /us/
│   ├── static/                          # Static assets / Mission Control built SPA
│   ├── swarm/                           # Autonomous Buy-Compose-Resell Swarm Agency
│   │   ├── assessor.py                  # Strategic repo signal assessor & profit route ranker
│   │   ├── ledger_writer.py             # Swarm ledger logger
│   │   ├── models.py                    # Composite product & swarm models
│   │   ├── orchestrator.py              # Swarm pipeline coordinator
│   │   ├── policy.py                    # Spend caps and domain allow/denylists
│   │   ├── publisher.py                 # Pinned product listing publisher
│   │   ├── qma.py                       # Quick Market Action evaluator
│   │   ├── registry.py                  # Swarm composite product catalog registry
│   │   ├── roles.py                     # Swarm agent roles (Scout, Warden, Treasurer, Archivist, Sovereign, Merchant)
│   │   └── sovereign.py                 # Dynamic pricing, CAC/LTV modeling, margin floor & revenue reporting
│   ├── agent_surface.py                 # Storefront discovery generator (llms.txt, agent-card.json, x402 manifest)
│   ├── cdp_auth.py                      # Coinbase CDP API Ed25519 authentication
│   ├── cdp_jwt.py                       # CDP JWT generation
│   ├── challenge_cache.py               # Memory cache for active 402 challenges
│   ├── commerce.py                      # In-memory and Redis quota/rate-limit enforcement
│   ├── config.py                        # Pydantic BaseSettings loading from .env
│   ├── dashboard.py                     # Standalone fallback single-file HTML dashboard
│   ├── demand.py                        # Search and demand signal analysis
│   ├── diligence_pack.py                # Multi-city rental diligence pack logic
│   ├── diligence_routes.py              # FastAPI routes under /tasks/us-rental-diligence
│   ├── doctor.py                        # Diagnostic health checks (wallet, CDP, RPC, Redis, files)
│   ├── finality_check.py                # Base mainnet L1/L2 block tag finality verifier
│   ├── keyprovider.py                   # Signing key abstraction (EnvKeyProvider)
│   ├── ledger_io.py                     # Spend/revenue JSONL reader & writer
│   ├── ledger_store.py                  # Ledger persistence store
│   ├── logging_config.py                # Structured logger setup
│   ├── main.py                          # FastAPI root app, routes, middleware, lifespan, and MCP mount
│   ├── manifest.py                      # /.well-known/mcp manifest builder
│   ├── mcp_server.py                    # FastMCP server instance, transport security, and 19 @mcp.tool() definitions
│   ├── mn_compliance.py                 # Minneapolis rental compliance logic & datasets
│   ├── models.py                        # Pydantic models for MCP inputs, outputs, and commerce metadata
│   ├── openapi_spec.py                  # OpenAPI schema customization
│   ├── ops_events.py                    # In-memory SSE event bus for dashboard streaming
│   ├── os_monitor.py                    # Background OS metric sampler (CPU, RAM, Disk, Net)
│   ├── payment_rails.py                 # Payment rail descriptor builder (x402 + Stripe)
│   ├── probe_rate_limit.py              # URL probe rate limiter
│   ├── pulse.py                         # Base Network Pulse synthesis (RPC + spot price)
│   ├── redis_client.py                  # Redis connection helper
│   ├── ssrf_guard.py                    # SSRF protection and URL validation
│   ├── stpaul_compliance.py             # St. Paul open data compliance
│   ├── stripe_payments.py               # Stripe Checkout and webhook verification
│   ├── tools_registry.py                # Canonical MCP tool specs (Single Source of Truth)
│   ├── tx_decision.py                   # Base tx timing & gas optimizer (EIP-1559 math)
│   ├── wallet_read.py                   # Public wallet balance & address inspection
│   ├── x402_middleware_pilot.py         # x402 FastAPI SDK middleware pilot route
│   └── x402_services.py                 # Core x402 client & resource server operations
├── dashboard/                           # Mission Control React 19 + Vite frontend
│   ├── src/                             # TypeScript React source components
│   ├── package.json                     # Dashboard pnpm configuration (Vite, React 19, Vitest, Playwright)
│   ├── tsconfig.json                    # Dashboard TypeScript configuration
│   └── vite.config.ts                   # Vite build & proxy configuration
├── docs/                                # Project documentation
│   ├── CITY-NETWORK.md                  # Detailed US City compliance guide
│   ├── DEPLOY-PLAN.md                   # Cloud deployment plan
│   ├── PRODUCT-FOCUS.md                 # Product strategy & realignment doc
│   ├── SELLER-STOREFRONT.md             # Storefront architecture and seller key isolation
│   ├── SETUP.md                         # Detailed developer onboarding & setup guide
│   ├── USER-GUIDE.md                    # End-user guide for MCP and API endpoints
│   ├── agent-ops.md                     # Agent operations runbook
│   └── architecture.md                  # Comprehensive architectural reference
├── ledger/                              # Ledger storage
│   └── policy.json                      # Spend limits, network allowlists, domain guards
├── manifests/
│   └── cursor-mcp.json                  # Cursor MCP client configuration
├── scripts/                             # Operational & maintenance scripts
│   ├── alerts.py                        # Ops alert checks
│   ├── capture_goal_evidence.py         # Automated test evidence capture
│   ├── dev_up.py                        # Local dev runner
│   ├── sign_ownership_proof.py          # Cryptographic storefront ownership proof signer
│   └── verify_goal.py                   # Verification suite runner
├── tests/                               # 61 pytest test suites
│   ├── conftest.py                      # Session mock x402 facilitator & isolation fixtures
│   ├── test_mcp_tools.py                # MCP tool execution, quota, and schema tests
│   ├── test_mcp_stdio.py                # Real stdio protocol roundtrip tests
│   ├── test_server_json.py              # MCP Registry schema verification
│   ├── test_manifest.py                 # /.well-known/mcp sync tests
│   ├── test_readme.py                   # README tool count & listing assertion tests
│   └── ... (55 additional test files)
├── .env.example                         # Template environment variables
├── .mcp.json.example                    # Claude Desktop / Cursor configuration template
├── CHANGES.md                           # Change log and release history
├── CLAUDE.md                            # Claude Code instructions & architecture rules
├── Dockerfile                           # Multi-stage production container build
├── Makefile                             # Convenience commands (make up, make api, make test)
├── README.md                            # Project overview & documentation
├── ROADMAP.md                           # Future roadmap
├── SECURITY.md                          # Security policy and disclosure
├── docker-compose.yml                   # Docker Compose configuration
├── fly.toml                             # Fly.io deployment config
├── package.json                         # Root build helper (builds dashboard SPA)
├── pyproject.toml                       # Python packaging and pytest configuration
├── render.yaml                          # Render web service deployment blueprint
├── requirements.txt                     # Pinned Python production & test dependencies
├── run_stdio.py                         # stdio MCP entrypoint script
├── server.json                          # MCP Registry publication manifest
├── smithery.yaml                        # Smithery.ai configuration
└── vercel.json                          # Vercel SPA hosting configuration
```

---

## 3. Comprehensive MCP Tool Inventory (19 Tools)

Every tool call in `app/mcp_server.py` passes through `_execute_tool(name, agent_id, fn)` which:
1. Resolves `agent_id` (or generates a fallback UUID if none supplied).
2. Enforces monthly quota and per-minute rate-limiting *before* executing the handler.
3. Attaches the `ResponseMeta` envelope to the response.
4. Emits a background SSE ops event via `app/ops_events.py`.
5. Returns a formatted JSON string matching `ToolResponse(data=..., meta=ResponseMeta(...))`.

### Common Response Envelope Schema (`ResponseMeta`)

```json
{
  "tier": "free | pro",
  "calls_this_month": 12,
  "quota_remaining": 488,
  "quota_warning": false,
  "rate_limit_remaining": 9,
  "tool_credits_remaining": 0,
  "upgrade_url": "https://.../upgrade",
  "agent_id": "agent-xyz-123"
}
```

---

### Detailed Tool Specifications

| # | Tool Name | Description | Parameters & Types | Required Env | Return Data Content |
|---|-----------|-------------|-------------------|--------------|---------------------|
| 1 | `discover_services` | Query x402 Bazaar for paid HTTP services via HTTPFacilitatorClient | `query`: `str \| None` (default `None`)<br>`limit`: `int` (default `20`, 1-100)<br>`max_price_usdc`: `float \| None` (default `None`)<br>`agent_id`: `str \| None` | None | Discovered services catalog, resource URLs, accepted payment tokens & networks |
| 2 | `get_payment_requirements` | Probe a URL for HTTP 402 payment requirements via x402 SDK | `url`: `str` (required)<br>`method`: `str` (default `"GET"`)<br>`headers`: `dict[str, str] \| None`<br>`agent_id`: `str \| None` | None | HTTP status (402), raw `PAYMENT-REQUIRED` header, decoded requirements (payTo, amount, asset, network, scheme) |
| 3 | `pay_and_fetch` | Pay via x402 client and fetch protected resource | `url`: `str` (required)<br>`method`: `str` (default `"GET"`)<br>`headers`: `dict[str, str] \| None`<br>`body`: `str \| None`<br>`preferred_network`: `str \| None`<br>`max_price_usdc`: `float \| None`<br>`agent_id`: `str \| None` | `EVM_PRIVATE_KEY` | Fetched HTTP response data, HTTP status, `PAYMENT-RESPONSE` settlement receipt |
| 4 | `build_seller_requirements` | Build seller payment requirements and embed Bazaar discovery metadata | `network`: `str` (default `"eip155:84532"`)<br>`pay_to`: `str \| None`<br>`price`: `str` (default `"$0.01"`)<br>`scheme`: `str` (default `"exact"`)<br>`description`: `str`<br>`resource_url`: `str \| None`<br>`mime_type`: `str \| None`<br>`discoverable`: `bool \| None`<br>`discovery_method`: `str`<br>`discovery_input_example`: `dict \| None`<br>`discovery_output_example`: `dict \| None`<br>`agent_id`: `str \| None` | `X402_PAY_TO_ADDRESS` | Base64 `PAYMENT-REQUIRED` header, decoded requirements dict, embedded Bazaar discovery extension |
| 5 | `verify_payment_payload` | Verify `PAYMENT-SIGNATURE` via x402 resource server and facilitator | `payment_signature`: `str` (required)<br>`payment_required`: `str` (required)<br>`agent_id`: `str \| None` | None | Verification status (`valid: bool`), payer wallet address, settlement parameters |
| 6 | `get_supported_networks` | List supported blockchain networks, facilitators, and headers | `agent_id`: `str \| None` | None | Supported networks list (Base mainnet `eip155:8453`, Base Sepolia `eip155:84532`, Solana), facilitators, v2 headers (`PAYMENT-REQUIRED`, `PAYMENT-SIGNATURE`, `PAYMENT-RESPONSE`) |
| 7 | `get_pro_upgrade_requirements` | Build x402 payment challenge for Pro tier subscription upgrade ($29.00) | `agent_id`: `str \| None` | `X402_PAY_TO_ADDRESS` | Pro tier payment challenge, price, payTo address, agent ID binding |
| 8 | `activate_pro_tier` | Verify x402 payment signature and unlock Pro tier limits (50k calls/mo, 120/min) | `payment_signature`: `str` (required)<br>`payment_required`: `str` (required)<br>`agent_id`: `str \| None` | None | Activation status, activated tier (`pro`), updated monthly quota & rate limit |
| 9 | `get_tool_credits_requirements` | Build x402 payment requirements for purchasing per-use tool credits ($1.00/100 credits) | `credits`: `int \| None` (default from config: 100)<br>`agent_id`: `str \| None` | `X402_PAY_TO_ADDRESS` | Credits challenge, price, credits pack amount, agent ID binding |
| 10 | `purchase_tool_credits` | Verify x402 payment signature and credit agent account with tool credits | `payment_signature`: `str` (required)<br>`payment_required`: `str` (required)<br>`credits`: `int \| None`<br>`agent_id`: `str \| None` | None | Credit purchase confirmation, added credits, new `tool_credits_remaining` total |
| 11 | `create_stripe_checkout` | Generate Stripe Checkout Session URL for fiat payment (pro upgrade / credits) | `purpose`: `str` (default `"pro_tier_upgrade"`, enum `pro_tier_upgrade \| tool_credits`)<br>`credits`: `int \| None`<br>`agent_id`: `str \| None` | `STRIPE_SECRET_KEY` | Hosted Checkout URL, Stripe Session ID, purpose, amount in USD |
| 12 | `run_swarm_research` | Run autonomous Swarm Agency pipeline (Scout → Warden → Treasurer → Archivist → Sovereign → Merchant) | `topic`: `str` (required)<br>`max_price_usdc`: `float \| None`<br>`allow_paid_inputs`: `bool \| None`<br>`agent_id`: `str \| None` | `EVM_PRIVATE_KEY`, `X402_PAY_TO_ADDRESS`, `SWARM_ENABLED=true` | Generated `product_id`, research report markdown, cost basis, listing price, purchase URL |
| 13 | `settle_composite_sale` | Verify and settle buyer payment for listed swarm composite product, booking revenue | `product_id`: `str` (required)<br>`payment_signature`: `str` (required)<br>`payment_required`: `str` (required)<br>`agent_id`: `str \| None` | None | Settlement status, product ID, realized revenue amount, full composite product report |
| 14 | `swarm_revenue_report` | Swarm financial intelligence: spend, revenue, LTV:CAC, net margins, source profit scores | `agent_id`: `str \| None` | None | Total spend, total revenue, net margin, margin percentage, LTV:CAC ratio, per-source scores |
| 15 | `get_base_pulse` | Live Base network settlement conditions (EIP-1559 base fee, congestion, USD cost, verdict) | `depth`: `int \| None` (default `12` blocks)<br>`agent_id`: `str \| None` | None | Base fee in gwei, block utilization %, ETH spot price, estimated settlement USD cost, verdict (`settle_now` vs `hold`) |
| 16 | `get_os_metrics` | Host OS telemetry: CPU, memory, swap, disk, network, health verdict, top processes | `include_processes`: `bool` (default `False`)<br>`agent_id`: `str \| None` | None | CPU %, Memory %, Disk %, Network I/O, health verdict (`ok` / `warn` / `critical`), top process table |
| 17 | `list_us_cities` | Free machine catalog of 14 US open-data property compliance endpoints & golden path | `agent_id`: `str \| None` | None | Array of 14 cities (mn, sea, nyc, chi, den, sf, lax, bos, phi, orl, nola, moco, gain, kc) with code, name, state, price ($0.01), paid_url, sample_url, sample_address |
| 18 | `get_us_city_property_sample` | Free fixed-address property compliance sample report for a chosen city code | `city_code`: `str` (required)<br>`agent_id`: `str \| None` | None | Complete address compliance report for fixed sample address (licenses, violations, condemnation status, verdict) |
| 19 | `check_us_city_property` | Paid address compliance check ($0.01 USDC) across 14 US city open data registries | `city_code`: `str` (required)<br>`address`: `str` (required, 1-120 chars)<br>`max_price_usdc`: `float \| None`<br>`preferred_network`: `str \| None`<br>`agent_id`: `str \| None` | `EVM_PRIVATE_KEY` (if unconfigured, returns 402 probe & how-to-pay guide) | Paid compliance report, verdict (`licensed_clean`, `licensed_with_violations`, `unlicensed`, `condemned`), full violations list |

---

## 4. Build, Execution, and Testing Mechanics

### 4.1 Development & Run Modes

1. **Stdio MCP Server (Cursor / Claude Desktop)**:
   ```bash
   python run_stdio.py
   ```
   Reads from stdin, writes JSON-RPC to stdout. Uses `app.mcp_server.mcp.run("stdio")`.

2. **HTTP & Streamable HTTP Server (Render / Local Docker)**:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8402
   ```
   Mounts:
   - Streamable HTTP MCP at `POST /mcp/mcp` (or mounted sub-app at `/mcp`).
   - SSE MCP at `GET /mcp/sse`.
   - REST API & machine discovery endpoints at `/health`, `/.well-known/*`, `/us/*`, `/base/*`, `/tasks/*`.
   - Static React Mission Control dashboard at `/dashboard` and `/assets`.

3. **Dashboard Build & Development**:
   - `cd dashboard && pnpm dev` — Runs Vite development server on port 5173 with proxy to 8402.
   - `cd dashboard && pnpm run build` — Compiles React 19 SPA to `dashboard/dist/`.
   - Root `npm run build` — Automates building the SPA and syncing `dist/index.html` and `dist/assets` to root.

### 4.2 Test Suite Architecture

- **Test Framework**: `pytest` (with `pytest-asyncio`, `anyio`, `fakeredis`).
- **Hermetic Isolation**: `tests/conftest.py` starts an in-process local HTTP server on a random port providing mock x402 facilitator (`/facilitator/supported`) and mock CDP discovery (`/discovery/resources`), redirecting `settings.x402_facilitator_url` and `settings.cdp_discovery_url` so no live network calls or wallet spends occur during test runs.
- **Swarm Isolation**: Redirects swarm product persistence to a temporary directory (`tmp_path`) so tests never touch `ledger/products.json`.
- **Test Invariants**:
  - `test_readme.py`: Verifies exact tool count (`19 MCP tools`) and every tool name exists in `README.md`.
  - `test_manifest.py`: Asserts `/.well-known/mcp` manifest contains all `EXPECTED_TOOL_NAMES`.
  - `test_server_json.py`: Validates `server.json` schema, character length limits, and namespace formatting.
  - `test_assessor.py`: Validates signal gathering and profit route ranking logic.

---

## 5. MCP Metadata & Configuration Files

| File | Purpose | Key Content / Schema |
|------|---------|---------------------|
| `smithery.yaml` | Smithery.ai Registry & Deployment Manifest | - `name`: `kwizzlesurp10/x402-mcp`<br>- `version`: `0.1.0`<br>- `remote.url`: `https://x402-mcp.onrender.com/mcp/mcp`<br>- `remote.transport`: `streamable-http`<br>- `startCommand`: `python run_stdio.py`<br>- `env`: `X402_PAY_TO_ADDRESS`, `EVM_PRIVATE_KEY` |
| `server.json` | Official Model Context Protocol Registry Manifest | - `$schema`: `https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json`<br>- `name`: `io.github.kwizzlesurp10-ctrl/x402-mcp`<br>- `remotes`: streamable-http at `https://x402-mcp.onrender.com/mcp/mcp` |
| `manifests/cursor-mcp.json` | Cursor Editor MCP Configuration | Command `python`, args `["${workspaceFolder}/run_stdio.py"]` with env mappings |
| `.mcp.json.example` | Claude Desktop Configuration Example | Configures `x402` (seller) and `x402vault` (buyer) stdio servers |
| `app/manifest.py` | Live `/.well-known/mcp` Endpoint | Dynamic manifest exposing server capabilities, tier quotas, payment rails, and tools list |
| `app/agent_surface.py` | A2A Protocol & Machine Surface | `/.well-known/agent-card.json`, `/.well-known/agents.json`, `/.well-known/x402`, `/llms.txt`, and `/.well-known/mcp/server-card.json` |
| `app/tools_registry.py` | Single Source of Truth for Tool Inventory | `TOOL_SPECS` tuple (19 entries), `TOOL_COUNT` = 19, `EXPECTED_TOOL_NAMES` |

---

## 6. Architectural Constraints & Single-Source-of-Truth Invariants

When adding, modifying, or enhancing MCP tools and schemas:
1. **Single Source of Truth (`app/tools_registry.py`)**:
   Every MCP tool must be listed in `TOOL_SPECS`. If a tool is added/modified, 5 places must be synchronized:
   - `app/mcp_server.py`: `@mcp.tool()` definition and docstring.
   - `app/tools_registry.py`: `TOOL_SPECS` entry (`name`, `description`, `tier`, `requires_env`).
   - `README.md`: Bump the "N MCP tools" header and add/update the row in the Markdown tools table.
   - `tests/test_readme.py`: `f"{TOOL_COUNT} MCP tools"` assertion.
   - `tests/test_assessor.py`: `s["mcp_tools"] == TOOL_COUNT` assertion.
2. **Commerce Chokepoint (`_execute_tool`)**:
   All MCP tool executions must flow through `_execute_tool` to ensure quota consumption, rate limiting, and standard `ResponseMeta` metadata.
3. **Transport Security (`_transport_security()`)**:
   FastMCP's DNS rebinding protection allows `localhost`, `127.0.0.1`, and the host derived from `PUBLIC_BASE_URL` (`x402-mcp.onrender.com`), preventing 421 "Invalid Host header" errors on public streamable-http endpoints.
4. **Key Isolation**:
   Public seller hosts never hold `EVM_PRIVATE_KEY` (spend key); only `X402_PAY_TO_ADDRESS` (receive address) is configured on public storefronts.
