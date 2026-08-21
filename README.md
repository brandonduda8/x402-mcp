# x402 Micropayments MCP

[![smithery badge](https://smithery.ai/badge/kwizzlesurp10/x402-mcp)](https://smithery.ai/server/kwizzlesurp10/x402-mcp)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Base Mainnet](https://img.shields.io/badge/Network-Base%20Mainnet%20(8453)-0052FF.svg)](https://base.org)
[![A2A Protocol](https://img.shields.io/badge/Identity-A2A%20v1.0%20Agent%20Card-green.svg)](https://github.com/kwizzlesurp10-ctrl/x402-mcp)

Production Model Context Protocol (MCP) server for the [x402](https://x402.org) HTTP micropayment protocol — **live on Base mainnet (`eip155:8453`), providing autonomous crypto commerce, data monetization, and municipal compliance screening for AI agents**.

Autonomous AI agents discover paid HTTP services, probe `402 Payment Required` headers, execute EIP-3009 transfer authorizations in USDC, monetize their own APIs with x402 Bazaar discovery metadata, and screen US municipal open data across 14 jurisdictions.

---

## Quickstart & 1-Click Installation

Install `kwizzlesurp10/x402-mcp` into your favorite MCP client using the [Smithery CLI](https://smithery.ai/server/kwizzlesurp10/x402-mcp):

### 1-Click CLI Installation

```bash
# Claude Desktop
npx -y @smithery/cli install kwizzlesurp10/x402-mcp --client claude

# Cursor
npx -y @smithery/cli install kwizzlesurp10/x402-mcp --client cursor

# Windsurf
npx -y @smithery/cli install kwizzlesurp10/x402-mcp --client windsurf
```

### Manual Client Configuration

#### Claude Desktop (`claude_desktop_config.json` / `.mcp.json`)

```json
{
  "mcpServers": {
    "x402-micropayments": {
      "command": "python",
      "args": ["run_stdio.py"],
      "env": {
        "X402_PAY_TO_ADDRESS": "0xAB745e5F576667037696e78ba7dA28E193E4423D",
        "EVM_PRIVATE_KEY": "",
        "X402_FACILITATOR_URL": "https://x402.org/facilitator"
      }
    }
  }
}
```

#### Cursor (`manifests/cursor-mcp.json` or Settings > Features > MCP)

```json
{
  "mcpServers": {
    "x402": {
      "command": "python",
      "args": ["${workspaceFolder}/run_stdio.py"],
      "env": {
        "X402_PAY_TO_ADDRESS": "0xAB745e5F576667037696e78ba7dA28E193E4423D",
        "SWARM_SELL_NETWORK": "eip155:84532"
      }
    }
  }
}
```

#### Remote Streamable HTTP (Any Remote MCP Client)

```json
{
  "mcpServers": {
    "x402-remote": {
      "url": "https://x402-mcp.onrender.com/mcp/mcp",
      "transport": "streamable-http"
    }
  }
}
```

---

## Live on Base Mainnet

- **Public Storefront & API:** `https://x402-mcp.onrender.com`
- **Facilitator Settlement:** Coinbase CDP Facilitator on Base mainnet (`eip155:8453`) and Base Sepolia (`eip155:84532`).
- **Machine Discovery Surfaces:**
  - `GET /.well-known/mcp` — Standard Model Context Protocol manifest
  - `GET /.well-known/agent-card.json` — A2A Protocol v1.0 Agent ID Card
  - `GET /.well-known/mcp/server-card.json` — SEP-1649 MCP Server Card
  - `GET /llms.txt` — LLM-optimized service directory
  - `GET /us/cities` — Free machine catalog of 14 US municipal open-data endpoints

---

## Features

- **20 MCP tools** for buyer settlement, seller monetization, Stripe fiat checkout, x402 commerce, autonomous swarm agency, US city property compliance, Base gas telemetry, and A2A machine identity — canonical inventory in `app/tools_registry.py` (guarded by `tests/test_readme.py` and `tests/test_manifest.py`).
- **4 MCP prompts** (`onboarding_flow`, `x402_tool_selector`, `generate_quote`, `troubleshoot_payment`) providing zero-shot operational guidance for LLM orchestrators.
- **4 MCP resources** (`x402://agent-card`, `x402://server-card`, `x402://tools-manifest`, `x402://pricing-table`) exposing real-time machine descriptors.
- **A2A Protocol v1.0 Agent ID Cards:** Native machine identity cards embedded in every tool annotation and accessible via `get_agent_card`.
- **x402/Coinbase Rail (Primary):** EIP-3009 transfer authorizations in USDC on Base mainnet, challenge generation, facilitator verification, and x402 Bazaar discovery indexing.
- **Stripe Payment Rail (Fiat Alternative):** Credit/debit card checkout via `create_stripe_checkout` for subscriptions and credit packs.
- **Commerce & Quota Layer:** Preemptive quota burn-down (500 free calls/month, 10 calls/min rate limit), returning a mandatory `ResponseMeta` envelope on every call.
- **Dual Transport:** Zero-crash `stdio` (Cursor, Claude Desktop, Windsurf) and `Streamable HTTP / SSE` (Render, Docker, Kubernetes).
- **Hermetic Test Suite:** 61 test suites with 600+ assertions, including in-process mock x402 facilitator and CDP discovery fixtures.

---

## Agent ID Cards & Machine Identity

`x402-mcp` implements the **Agent-to-Agent (A2A) Protocol v1.0** and **SEP-1649 Server Card** standards for verifiable machine identity and autonomous agent discovery.

### Server Identity & Tool Capabilities

AI agents can inspect the server's identity, supported payment networks, security schemes, and granular tool skill cards using either:
1. **MCP Tool:** `get_agent_card` (accepts optional `target_id` to inspect specific skills).
2. **MCP Resource:** `x402://agent-card` (returns complete A2A Agent Card JSON).
3. **HTTP Discovery:** `GET https://x402-mcp.onrender.com/.well-known/agent-card.json`.

### Per-Agent Quota Tracking & Isolation (`agent_id`)

Every tool in `x402-mcp` accepts an optional `agent_id` string parameter.
- **Free Tier:** 500 calls/month, 10 calls/minute per `agent_id`.
- **Pro Tier:** 50,000 calls/month, 120 calls/minute. Upgrade via `get_pro_upgrade_requirements` or `create_stripe_checkout`.
- **Tool Credits:** Per-use credits for high-volume workflows via `purchase_tool_credits`.

### Standard Response Envelope (`ResponseMeta`)

Every tool response is wrapped in a structured JSON envelope containing execution data and real-time quota telemetry:

```json
{
  "data": {
    "status": "success",
    "result": "..."
  },
  "meta": {
    "tier": "free",
    "calls_this_month": 14,
    "quota_remaining": 486,
    "quota_warning": false,
    "rate_limit_remaining": 9,
    "tool_credits_remaining": 0,
    "upgrade_url": "https://x402-mcp.onrender.com/upgrade",
    "agent_id": "agent-alpha-007"
  }
}
```

---

## MCP Tools Reference (20 Tools)

### 1. Buyer & Payment Client Tools

| Tool | Role | Tier / Cost | Description |
|------|------|-------------|-------------|
| `discover_services` | `indexer` | Free | Query x402 Bazaar for paid HTTP services accepting EIP-3009 micropayments. |
| `get_payment_requirements` | `oracle` | Free | Probe target URL for HTTP 402 `PAYMENT-REQUIRED` terms without paying. |
| `pay_and_fetch` | `settler` | Paid (x402) | Sign EIP-3009 payment authorization using `EVM_PRIVATE_KEY` and fetch protected resource. |

#### Parameter Specifications:

- **`discover_services`**
  | Parameter | Type | Required | Default | Description |
  |-----------|------|:--------:|---------|-------------|
  | `query` | `string` | Optional | `None` | Search keyword to filter services by name or description |
  | `limit` | `integer` | Optional | `20` | Maximum number of services to return (range: 1-100) |
  | `max_price_usdc` | `number` | Optional | `None` | Maximum price threshold in USDC per call |
  | `agent_id` | `string` | Optional | `None` | Calling agent identifier for quota tracking |

- **`get_payment_requirements`**
  | Parameter | Type | Required | Default | Description |
  |-----------|------|:--------:|---------|-------------|
  | `url` | `string` | **Required** | — | Target HTTP URL to probe for HTTP 402 challenge headers |
  | `method` | `string` | Optional | `"GET"` | HTTP method to use for the probe request |
  | `headers` | `object` | Optional | `None` | Dictionary of custom HTTP request headers |
  | `agent_id` | `string` | Optional | `None` | Calling agent identifier for quota tracking |

- **`pay_and_fetch`**
  | Parameter | Type | Required | Default | Description |
  |-----------|------|:--------:|---------|-------------|
  | `url` | `string` | **Required** | — | Protected HTTP URL requiring x402 payment authorization |
  | `method` | `string` | Optional | `"GET"` | HTTP method to use for the payment request |
  | `headers` | `object` | Optional | `None` | Custom HTTP request headers |
  | `body` | `string` | Optional | `None` | HTTP request body string for POST/PUT |
  | `preferred_network` | `string` | Optional | `None` | Preferred CAIP-2 network (e.g. `'eip155:8453'`) |
  | `max_price_usdc` | `number` | Optional | `None` | Maximum price willing to pay in USDC |
  | `agent_id` | `string` | Optional | `None` | Calling agent identifier for quota tracking |

---

### 2. Seller & Monetization Tools

| Tool | Role | Tier / Cost | Description |
|------|------|-------------|-------------|
| `build_seller_requirements` | `broker` | Free | Build x402 v2 `PAYMENT-REQUIRED` challenge with Bazaar discovery extension. |
| `verify_payment_payload` | `verifier` | Free | Verify buyer's `PAYMENT-SIGNATURE` via facilitator before releasing data. |
| `get_supported_networks` | `oracle` | Free | List supported CAIP-2 chains, facilitators, and protocol v2 headers. |

#### Parameter Specifications:

- **`build_seller_requirements`**
  | Parameter | Type | Required | Default | Description |
  |-----------|------|:--------:|---------|-------------|
  | `network` | `string` | Optional | `"eip155:84532"` | CAIP-2 network identifier where seller receives funds |
  | `pay_to` | `string` | Optional | `None` | Seller EVM address (defaults to `X402_PAY_TO_ADDRESS`) |
  | `price` | `string` | Optional | `"$0.01"` | Price string (e.g. `"$0.01"` or `"0.05"`) |
  | `scheme` | `string` | Optional | `"exact"` | Payment scheme type |
  | `description` | `string` | Optional | `"Paid API access"` | Description of monetized service |
  | `resource_url` | `string` | Optional | `None` | Canonical URL to embed in Bazaar discovery extension |
  | `mime_type` | `string` | Optional | `"application/json"` | MIME type of response payload |
  | `discoverable` | `boolean` | Optional | `None` | Whether endpoint is listed publicly in x402 Bazaar |
  | `discovery_method` | `string` | Optional | `"GET"` | HTTP method for Bazaar invocation |
  | `discovery_input_example` | `object` | Optional | `None` | Example request input JSON object |
  | `discovery_output_example` | `object` | Optional | `None` | Example response output JSON object |
  | `agent_id` | `string` | Optional | `None` | Calling agent identifier for quota tracking |

- **`verify_payment_payload`**
  | Parameter | Type | Required | Default | Description |
  |-----------|------|:--------:|---------|-------------|
  | `payment_signature` | `string` | **Required** | — | Base64 or JSON string of buyer's `PAYMENT-SIGNATURE` |
  | `payment_required` | `string` | **Required** | — | Base64 or JSON string of seller's `PAYMENT-REQUIRED` |
  | `agent_id` | `string` | Optional | `None` | Calling agent identifier for quota tracking |

- **`get_supported_networks`**
  | Parameter | Type | Required | Default | Description |
  |-----------|------|:--------:|---------|-------------|
  | `agent_id` | `string` | Optional | `None` | Calling agent identifier for quota tracking |

---

### 3. Commerce & Subscription Tools

| Tool | Role | Tier / Cost | Description |
|------|------|-------------|-------------|
| `get_pro_upgrade_requirements` | `broker` | Free | Build x402 payment challenge for Pro tier subscription ($29.00 USDC). |
| `activate_pro_tier` | `settler` | Paid (x402) | Verify payment and unlock Pro limits (50k calls/mo, 120/min). |
| `get_tool_credits_requirements` | `broker` | Free | Build x402 payment challenge for purchasing tool credit packs ($1.00/100 credits). |
| `purchase_tool_credits` | `settler` | Paid (x402) | Verify payment and credit per-use tool balance to agent. |
| `create_stripe_checkout` | `checkout` | Free | Generate Stripe Checkout Session URL for fiat payment (card/bank). |

#### Parameter Specifications:

- **`get_pro_upgrade_requirements`**
  | Parameter | Type | Required | Default | Description |
  |-----------|------|:--------:|---------|-------------|
  | `agent_id` | `string` | Optional | `None` | Calling agent identifier for quota tracking |

- **`activate_pro_tier`**
  | Parameter | Type | Required | Default | Description |
  |-----------|------|:--------:|---------|-------------|
  | `payment_signature` | `string` | **Required** | — | Signed `PAYMENT-SIGNATURE` authorizing Pro tier fee |
  | `payment_required` | `string` | **Required** | — | Pro upgrade `PAYMENT-REQUIRED` challenge |
  | `agent_id` | `string` | Optional | `None` | Calling agent identifier for quota tracking |

- **`get_tool_credits_requirements`**
  | Parameter | Type | Required | Default | Description |
  |-----------|------|:--------:|---------|-------------|
  | `credits` | `integer` | Optional | `100` | Number of tool credits to purchase |
  | `agent_id` | `string` | Optional | `None` | Calling agent identifier for quota tracking |

- **`purchase_tool_credits`**
  | Parameter | Type | Required | Default | Description |
  |-----------|------|:--------:|---------|-------------|
  | `payment_signature` | `string` | **Required** | — | Signed `PAYMENT-SIGNATURE` authorizing credits fee |
  | `payment_required` | `string` | **Required** | — | Tool credits `PAYMENT-REQUIRED` challenge |
  | `credits` | `integer` | Optional | `100` | Number of credits being purchased |
  | `agent_id` | `string` | Optional | `None` | Calling agent identifier for quota tracking |

- **`create_stripe_checkout`**
  | Parameter | Type | Required | Default | Description |
  |-----------|------|:--------:|---------|-------------|
  | `purpose` | `string` | Optional | `"pro_tier_upgrade"` | Checkout purpose (`"pro_tier_upgrade"` or `"tool_credits"`) |
  | `credits` | `integer` | Optional | `None` | Number of credits if purchasing tool credits pack |
  | `agent_id` | `string` | Optional | `None` | Calling agent identifier for quota tracking |

---

### 4. Swarm Agency & Autonomous Resale Tools

| Tool | Role | Tier / Cost | Description |
|------|------|-------------|-------------|
| `run_swarm_research` | `investigator` | Free / Paid | Run 6-role swarm pipeline to synthesize and list composite research products. |
| `settle_composite_sale` | `settler` | Sell-side | Verify buyer payment for a listed swarm product and book realized revenue. |
| `swarm_revenue_report` | `telemetry` | Free | Swarm financial intelligence: spend, revenue, net margins, LTV:CAC, source scores. |

#### Parameter Specifications:

- **`run_swarm_research`**
  | Parameter | Type | Required | Default | Description |
  |-----------|------|:--------:|---------|-------------|
  | `topic` | `string` | **Required** | — | Research topic or intelligence domain for swarm to investigate |
  | `max_price_usdc` | `number` | Optional | `None` | Maximum budget in USDC to spend on upstream data feeds |
  | `allow_paid_inputs` | `boolean` | Optional | `False` | Whether to permit buying upstream paid data feeds |
  | `agent_id` | `string` | Optional | `None` | Calling agent identifier for quota tracking |

- **`settle_composite_sale`**
  | Parameter | Type | Required | Default | Description |
  |-----------|------|:--------:|---------|-------------|
  | `product_id` | `string` | **Required** | — | Canonical product ID of listed research artifact |
  | `payment_signature` | `string` | **Required** | — | Buyer's signed `PAYMENT-SIGNATURE` payload |
  | `payment_required` | `string` | **Required** | — | Original `PAYMENT-REQUIRED` challenge for product |
  | `agent_id` | `string` | Optional | `None` | Calling agent identifier for quota tracking |

- **`swarm_revenue_report`**
  | Parameter | Type | Required | Default | Description |
  |-----------|------|:--------:|---------|-------------|
  | `agent_id` | `string` | Optional | `None` | Calling agent identifier for quota tracking |

---

### 5. Blockchain Pulse, Telemetry & Identity Tools

| Tool | Role | Tier / Cost | Description |
|------|------|-------------|-------------|
| `get_base_pulse` | `oracle` | Free | Live Base RPC gas conditions, EIP-1559 trend, utilization, USD cost, and verdict. |
| `get_os_metrics` | `telemetry` | Free | Host OS telemetry: CPU, memory, swap, disk, network, health verdict, top processes. |
| `get_agent_card` | `identity` | Free | Retrieve A2A Protocol v1.0 Agent ID Card and tool capability registry. |

#### Parameter Specifications:

- **`get_base_pulse`**
  | Parameter | Type | Required | Default | Description |
  |-----------|------|:--------:|---------|-------------|
  | `depth` | `integer` | Optional | `12` | Number of recent Base blocks to analyze |
  | `agent_id` | `string` | Optional | `None` | Calling agent identifier for quota tracking |

- **`get_os_metrics`**
  | Parameter | Type | Required | Default | Description |
  |-----------|------|:--------:|---------|-------------|
  | `include_processes` | `boolean` | Optional | `False` | Whether to include top memory-consuming processes table |
  | `agent_id` | `string` | Optional | `None` | Calling agent identifier for quota tracking |

- **`get_agent_card`**
  | Parameter | Type | Required | Default | Description |
  |-----------|------|:--------:|---------|-------------|
  | `target_id` | `string` | Optional | `None` | Specific skill ID, tool name, or agent ID to inspect |
  | `agent_id` | `string` | Optional | `None` | Calling agent identifier for quota tracking |

---

### 6. US City Open-Data Property Compliance Network Tools

| Tool | Role | Tier / Cost | Description |
|------|------|-------------|-------------|
| `list_us_cities` | `indexer` | Free | Machine catalog of 14 US municipal property compliance endpoints. |
| `get_us_city_property_sample` | `oracle` | Free | Free fixed-address property compliance sample report for a chosen city code. |
| `check_us_city_property` | `investigator` | $0.01 USDC | Paid address compliance check across 14 US municipal open-data registries. |

#### Parameter Specifications:

- **`list_us_cities`**
  | Parameter | Type | Required | Default | Description |
  |-----------|------|:--------:|---------|-------------|
  | `agent_id` | `string` | Optional | `None` | Calling agent identifier for quota tracking |

- **`get_us_city_property_sample`**
  | Parameter | Type | Required | Default | Description |
  |-----------|------|:--------:|---------|-------------|
  | `city_code` | `string` | **Required** | — | 2-4 letter city code (e.g. `'mn'`, `'sea'`, `'chi'`, `'nyc'`, `'den'`, `'sf'`, `'lax'`) |
  | `agent_id` | `string` | Optional | `None` | Calling agent identifier for quota tracking |

- **`check_us_city_property`**
  | Parameter | Type | Required | Default | Description |
  |-----------|------|:--------:|---------|-------------|
  | `city_code` | `string` | **Required** | — | 2-4 letter jurisdiction code (e.g. `'mn'`, `'sea'`, `'nyc'`) |
  | `address` | `string` | **Required** | — | Street address to inspect (1-120 characters) |
  | `max_price_usdc` | `number` | Optional | `0.01` | Maximum price willing to pay in USDC |
  | `preferred_network` | `string` | Optional | `None` | CAIP-2 payment network identifier (`'eip155:8453'`) |
  | `agent_id` | `string` | Optional | `None` | Calling agent identifier for quota tracking |

---

## MCP Prompts Reference (4 Prompts)

`x402-mcp` exposes 4 structured MCP Prompts to steer AI reasoning models:

| Prompt Name | Arguments | Description |
|-------------|-----------|-------------|
| `onboarding_flow` | `agent_name: str = "agent"` | Step-by-step onboarding walkthrough for new AI agents connecting to the server. |
| `x402_tool_selector` | `goal: str = "compliance"`, `domain: str | None = None` | Dynamic decision tree mapping operational goals to the safest and most cost-effective MCP tools. |
| `generate_quote` | `service_name: str`, `price_usdc: str`, `network: str`, `pay_to: str | None` | Interactive quote and payment challenge generator for sellers looking to monetize HTTP APIs. |
| `troubleshoot_payment` | `error_code: str`, `details: str | None` | Automated diagnostic analysis and remediation runbook for x402 payment, signature, and quota errors. |

---

## MCP Resources Reference (4 Resources)

`x402-mcp` provides real-time machine-readable resources accessible via standard MCP resource URIs:

| Resource URI | MIME Type | Description |
|--------------|-----------|-------------|
| `x402://agent-card` | `application/json` | Full A2A Protocol v1.0 Agent ID Card and complete capability manifest. |
| `x402://server-card` | `application/json` | SEP-1649 MCP Server Card for Smithery.ai, Glama.ai, and client indexing. |
| `x402://tools-manifest` | `application/json` | Canonical manifest exposing registered tools, quotas, and endpoints. |
| `x402://pricing-table` | `application/json` | Live pricing matrix for free tier, Pro subscription, credit packs, and paid endpoints. |

---

## Sample AI Agent Queries & Interactions

Below are realistic prompts and multi-turn workflows demonstrating how autonomous AI agents utilize `x402-mcp`:

### 1. Real Estate Compliance Workflow
> **Agent Prompt:** *"I am evaluating a rental property at 1700 Penn Ave N in Minneapolis. Check whether it has an active rental license and any building code violations."*
1. Agent calls `list_us_cities()` to verify Minneapolis (`mn`) is supported.
2. Agent calls `get_us_city_property_sample(city_code="mn")` to inspect response shape for free.
3. Agent calls `check_us_city_property(city_code="mn", address="1700 Penn Ave N")`, automatically paying $0.01 USDC on Base to retrieve the verified compliance record.

### 2. Base Network Gas & Settlement Timing
> **Agent Prompt:** *"Is Base network congested right now, and should I execute an on-chain settlement transaction immediately or wait?"*
1. Agent calls `get_base_pulse(depth=12)`.
2. Model receives live EIP-1559 base fee (e.g. `0.008 gwei`), 42% block utilization, estimated USD transfer cost (`$0.0001`), and verdict: `"settle_now"`.

### 3. Service Discovery & Protected API Consumption
> **Agent Prompt:** *"Find an x402 service offering financial market data under $0.05 USDC, probe its payment terms, and fetch the report."*
1. Agent calls `discover_services(query="financial", max_price_usdc=0.05)`.
2. Agent calls `get_payment_requirements(url="https://api.example.com/market-intel")`.
3. Agent calls `pay_and_fetch(url="https://api.example.com/market-intel", max_price_usdc=0.05)`, settling via EIP-3009.

### 4. Seller API Monetization
> **Agent Prompt:** *"I want to monetize my AI summarization endpoint at https://ai.example.com/summarize for $0.02 USDC on Base mainnet."*
1. Agent calls `generate_quote(service_name="AI Summarizer", price_usdc="$0.02", network="eip155:8453")`.
2. Agent calls `build_seller_requirements(network="eip155:8453", price="$0.02", description="AI Summarizer", resource_url="https://ai.example.com/summarize", discoverable=True)`.
3. Server generates `PAYMENT-REQUIRED` challenge with embedded x402 Bazaar discovery extension.

---

## Environment Variables Reference

| Variable | Required | Description |
|----------|:--------:|-------------|
| `X402_PAY_TO_ADDRESS` | Selling | Base wallet address (`0x...`) where x402 micropayments settle. |
| `CDP_API_KEY_ID` | Base Mainnet | Coinbase CDP API Key ID for Base mainnet (`eip155:8453`) settlement. |
| `CDP_API_KEY_SECRET` | Base Mainnet | Coinbase CDP API Key Secret (Ed25519) for mainnet facilitator auth. |
| `EVM_PRIVATE_KEY` | Buying | EVM private key (`0x...`) for signing EIP-3009 payments in `pay_and_fetch` / `check_us_city_property`. **Never configure spend keys on public seller storefronts.** |
| `SWARM_SELL_NETWORK` | Optional | CAIP-2 network for product listings (default: `eip155:84532`, set `eip155:8453` for mainnet). |
| `STRIPE_SECRET_KEY` | Fiat Rail | Stripe API secret key (`sk_live_...` / `sk_test_...`) for card checkout. |
| `STRIPE_WEBHOOK_SECRET` | Fiat Rail | Stripe webhook signing secret (`whsec_...`) for webhook verification. |
| `X402_FACILITATOR_URL` | Optional | Fallback testnet facilitator URL (default: `https://x402.org/facilitator`). |
| `DEFAULT_AGENT_ID` | Optional | Fallback agent identifier for unannotated MCP calls (default: `smithery-agent`). |

---

## Local Development & Testing

### Run Tests

The test suite runs hermetically with zero external network dependencies:

```bash
# Run complete test suite
pytest -v

# Run README and manifest synchronization tests
pytest tests/test_readme.py tests/test_manifest.py tests/test_server_json.py -v
```

### Start Local Servers

```bash
# Start Stdio MCP Server (for Cursor / Claude Desktop)
python run_stdio.py

# Start FastAPI Streamable HTTP & SSE Server
uvicorn app.main:app --host 0.0.0.0 --port 8402
```

---

## License

Apache-2.0. Compatible with the x402 Foundation ecosystem.