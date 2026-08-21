# Smithery.ai Quality Score Guidelines, Agent ID Card Specification, and Production Checklist

## 1. Executive Summary & Quality Score Rubric

The Smithery.ai registry evaluates Model Context Protocol (MCP) servers on a **0–100 Quality Score** scale. The score determines search ranking, registry trust tier, automated agent client discovery (e.g. Claude Desktop, Cursor, Windsurf), and hosted proxy routing reliability. 

A score of **51/100** represents a minimally functioning server with severe metadata, schema, and machine-readability gaps. A score of **100/100** represents an exemplary, production-grade MCP server with complete tool annotations, embedded Agent ID cards, explicit JSON schemas, valid `smithery.yaml` configuration, and structured documentation.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                    SMITHERY.AI QUALITY SCORE BREAKDOWN                       │
├──────────────────────────────────────┬────────┬──────────────┬───────────────┤
│ Evaluation Dimension                 │ Points │ Current Repo │ Target Score  │
├──────────────────────────────────────┼────────┼──────────────┼───────────────┤
│ 1. Tool Metadata, Schemas & Annotations│ 35 pts │ 15 / 35      │ 35 / 35       │
│ 2. Agent ID Cards & Machine Identity  │ 25 pts │  0 / 25      │ 25 / 25       │
│ 3. Server Config & Transports (`yaml`)│ 20 pts │ 16 / 20      │ 20 / 20       │
│ 4. Documentation & Package Metadata  │ 20 pts │ 20 / 20      │ 20 / 20       │
├──────────────────────────────────────┼────────┼──────────────┼───────────────┤
│ TOTAL QUALITY SCORE                  │ 100 pts│ 51 / 100     │ 100 / 100     │
└──────────────────────────────────────┴────────┴──────────────┴───────────────┘
```

---

### Root Cause Analysis: Why `kwizzlesurp10/x402-mcp` Scored 51/100

| Defect / Missing Requirement | Score Impact | Current State in Repository | Required Fix |
| :--- | :--- | :--- | :--- |
| **Missing Agent ID Cards on Tools** | **-25 pts** | No MCP tools in `app/mcp_server.py` declare Agent ID cards or agent identity descriptors. | Attach structured `agent_card` metadata objects inside `@mcp.tool(annotations={...})` for all 19 tools. |
| **Missing Tool Behavioral Annotations** | **-10 pts** | FastMCP tools lack `readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`, and `title`. | Add standard MCP ToolAnnotations to all 19 `@mcp.tool()` definitions. |
| **Non-Standard `smithery.yaml`** | **-4 pts** | `smithery.yaml` uses a non-standard `config:` block under `startCommand` instead of `configSchema` + `commandFunction`. | Replace with standard `configSchema` (JSON schema) and `commandFunction` (JS launcher). |
| **Sparse `package.json` Metadata** | **-4 pts** | `package.json` contains only 8 lines with no description, author, license, keywords, or repo URLs. | Fully populate standard NPM metadata fields in root `package.json`. |
| **Unannotated Tool Parameters** | **-3 pts** | FastMCP function arguments lack `Annotated[T, Field(description="...")]` schemas. | Add typing `Annotated` with Pydantic `Field(description=...)` for every parameter. |
| **Missing Smithery Badge & Quickstart** | **-3 pts** | `README.md` lacks the official Smithery badge and `npx @smithery/cli` install command. | Add official Smithery badge, quickstart commands, and LLM sample prompts. |

---

## 2. Agent ID Card Specification for MCP Tools and Servers

### 2.1 Overview & Conceptual Architecture
An **Agent ID Card** (or **AgentCard**) is a framework-agnostic digital identity and capability contract for autonomous AI agents and tool servers. Standardized across the **Agent-to-Agent (A2A) Protocol v1.0**, **SEP-1649 (MCP Server Cards)**, and registry ecosystems (Smithery.ai, Glama.ai, Open Agent Registry), Agent ID cards bridge low-level function calling with high-level agentic orchestration.

In an MCP architecture, Agent ID cards operate at two complementary tiers:
1. **Server-Level Agent Card (`/.well-known/agent-card.json`):** Describes the host identity, security schemes (e.g. x402 EIP-3009), communication endpoints, and provider metadata.
2. **Tool/Skill-Level Agent ID Card (Embedded in Tool Annotations):** Attached directly to individual MCP tool definitions, giving AI reasoning engines granular information on tool role, archetype, domain, safety profile, cost model, and execution semantics.

---

### 2.2 Tool-Level Agent ID Card Schema

Every MCP tool exposed by a compliant server should declare an `agent_card` object inside its MCP tool annotations:

```typescript
interface ToolAgentIdCard {
  /** Unique canonical identifier for the agent skill */
  id: string;
  /** Human and model-readable skill name */
  name: string;
  /** Functional archetype of the tool */
  role: "verifier" | "broker" | "settler" | "oracle" | "investigator" | "indexer" | "telemetry" | "checkout";
  /** Problem domain */
  domain: "micropayments" | "real-estate-compliance" | "blockchain-gas-optimization" | "commerce" | "systems-ops";
  /** Interface version */
  version: string;
  /** Cost model / settlement requirement */
  pricing: {
    model: "free" | "paid_per_call" | "subscription_upgrade" | "credit_pack";
    price_usdc?: string;
    network?: string;
    settlement_protocol?: "x402-v2" | "stripe-fiat" | "none";
  };
  /** Execution guarantees and safety profile */
  execution_profile: {
    read_only: boolean;
    destructive: boolean;
    idempotent: boolean;
    open_world: boolean;
  };
  /** Supported input and output formats */
  input_modes: ("application/json" | "text/plain")[];
  output_modes: ("application/json" | "text/plain")[];
  /** Categorization tags */
  tags: string[];
  /** Concrete user prompt examples demonstrating when to call this tool */
  examples: string[];
}
```

---

### 2.3 FastMCP Implementation Pattern

In Python FastMCP servers, Agent ID cards and behavioral annotations are attached via the `annotations` parameter in `@mcp.tool()`:

```python
from typing import Annotated
from pydantic import Field

@mcp.tool(
    name="check_us_city_property",
    description=(
        "Paid address-level housing license, building violation, and code compliance "
        "check for supported US jurisdictions via x402 micropayments. Settles USDC on "
        "Base mainnet if EVM_PRIVATE_KEY is configured; otherwise returns payment probe."
    ),
    annotations={
        "title": "US City Property Compliance Check",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
        "agent_card": {
            "id": "us-city-property-check",
            "name": "US City Property Compliance Checker",
            "role": "investigator",
            "domain": "real-estate-compliance",
            "version": "0.1.0",
            "pricing": {
                "model": "paid_per_call",
                "price_usdc": "$0.01",
                "network": "eip155:8453",
                "settlement_protocol": "x402-v2",
            },
            "execution_profile": {
                "read_only": True,
                "destructive": False,
                "idempotent": True,
                "open_world": True,
            },
            "input_modes": ["application/json"],
            "output_modes": ["application/json"],
            "tags": ["property", "compliance", "housing", "violations", "x402", "usdc", "base"],
            "examples": [
                "Check rental license and code violations for 1700 Penn Ave N in Minneapolis (city=mn)",
                "Is 123 Main St in Seattle licensed for rental operations? (city=sea)",
            ],
        },
    },
)
async def check_us_city_property(
    city_code: Annotated[str, Field(description="2-4 letter city jurisdiction code (e.g., mn, sea, chi, nyc)")],
    address: Annotated[str, Field(description="Street address to inspect (1-120 characters)")],
    max_price_usdc: Annotated[float | None, Field(description="Maximum price willing to pay in USDC (default: 0.01)")] = None,
    preferred_network: Annotated[str | None, Field(description="CAIP-2 payment network (e.g., eip155:8453)")] = None,
    agent_id: Annotated[str | None, Field(description="Optional calling agent identifier for quota tracking")] = None,
) -> str:
    ...
```

---

## 3. Comprehensive Smithery Production Checklist (100/100 Requirements)

### Checklist Category A: Tool Metadata & Schema Quality (35 Points)

- [ ] **A1. Explicit Tool Names:** Tool names must be lower snake_case, unique, and strictly descriptive (e.g. `discover_services`, `check_us_city_property`).
- [ ] **A2. Model-Centric Docstrings:** Tool descriptions must be written for the LLM runtime:
  - State the core capability and output shape.
  - State prerequisites (e.g., required environment variables or prior tool invocations).
  - Explicitly document side effects or payment triggers.
- [ ] **A3. Property Descriptions on All Arguments:** Every argument in every tool must have an explicit description via `Annotated[T, Field(description="...")]` or Pydantic schemas.
- [ ] **A4. Behavioral Annotations (`ToolAnnotations`):** Every tool must declare standard behavioral flags:
  - `title`: Human/agent friendly display name.
  - `readOnlyHint`: `True` if the tool only inspects/reads data; `False` if it alters state or spends funds.
  - `destructiveHint`: `True` if irreversible or financial loss possible; `False` otherwise.
  - `idempotentHint`: `True` if repeated calls with identical parameters yield identical results.
  - `openWorldHint`: `True` if the tool interacts with external APIs, network RPCs, or blockchains.
- [ ] **A5. Return Envelope & Error Handling:** Return responses must follow structured JSON serialization with both `data` and `meta` envelopes (e.g., quota status, error classification).

---

### Checklist Category B: Agent ID Card Integration (25 Points)

- [ ] **B1. Tool-Level Agent ID Cards:** Every registered MCP tool must embed an `agent_card` object inside its annotations matching the specification in Section 2.2.
- [ ] **B2. Role & Archetype Classification:** Every tool must be categorized with a valid role (`verifier`, `broker`, `settler`, `oracle`, `investigator`, `indexer`, `telemetry`, `checkout`).
- [ ] **B3. Pricing & Settlement Metadata:** Every tool must explicitly declare whether it is free, pay-per-call (with asset, network, price), or upgrade-gated.
- [ ] **B4. Realistic Invocation Examples:** Every tool Agent Card must include at least 2 realistic prompt examples demonstrating natural language queries that trigger the tool.
- [ ] **B5. Server-Level Agent Card (`/.well-known/agent-card.json`):** The server must serve an A2A Protocol v1.0 Agent Card at `/.well-known/agent-card.json`.

---

### Checklist Category C: Server Configuration & Deployment (`smithery.yaml`) (20 Points)

- [ ] **C1. Canonical `smithery.yaml` Schema:** The configuration must follow Smithery's standardized structure:
  ```yaml
  startCommand:
    type: stdio
    configSchema:
      type: object
      properties:
        X402_PAY_TO_ADDRESS:
          type: string
          description: "Base mainnet wallet address to receive x402 micropayments"
        EVM_PRIVATE_KEY:
          type: string
          description: "Optional buyer private key for automated x402 signing"
        X402_FACILITATOR_URL:
          type: string
          description: "Facilitator endpoint URL (default: https://x402.org/facilitator)"
          default: "https://x402.org/facilitator"
    commandFunction: |-
      (config) => ({
        command: 'python',
        args: ['run_stdio.py'],
        env: {
          ...(config.X402_PAY_TO_ADDRESS ? { X402_PAY_TO_ADDRESS: config.X402_PAY_TO_ADDRESS } : {}),
          ...(config.EVM_PRIVATE_KEY ? { EVM_PRIVATE_KEY: config.EVM_PRIVATE_KEY } : {}),
          ...(config.X402_FACILITATOR_URL ? { X402_FACILITATOR_URL: config.X402_FACILITATOR_URL } : {})
        }
      })
  ```
- [ ] **C2. Remote Streamable HTTP & SSE Declaration:** Declare remote capabilities (`url`, `transport: "streamable-http"`, `capabilities: { tools: true }`).
- [ ] **C3. Container / Dockerfile Compliance:** Provide a multi-stage, secure `Dockerfile` that supports non-root execution and passes healthchecks.
- [ ] **C4. Zero-Crash StdIO Transport:** `run_stdio.py` must run reliably without unexpected stdout writes (all logging directed to stderr).

---

### Checklist Category D: Documentation, README & Package Metadata (20 Points)

- [ ] **D1. Official Smithery Badge:** `README.md` must display the official Smithery badge at the top:
  ```markdown
  [![smithery badge](https://smithery.ai/badge/kwizzlesurp10/x402-mcp)](https://smithery.ai/server/kwizzlesurp10/x402-mcp)
  ```
- [ ] **D2. Automated Installation Instructions:** Provide single-command CLI installation for Claude Desktop, Cursor, and Windsurf:
  ```bash
  npx -y @smithery/cli install kwizzlesurp10/x402-mcp --client claude
  npx -y @smithery/cli install kwizzlesurp10/x402-mcp --client cursor
  ```
- [ ] **D3. Complete Tool Inventory Table:** README must list all 19 tools with their purpose, tier, parameters, and required environment variables.
- [ ] **D4. LLM Query & Prompt Examples:** README must include prompt examples showing how users and AI models interact with each tool subsystem.
- [ ] **D5. Environment Variable Matrix:** Complete reference table with variable name, description, required status, and security considerations.
- [ ] **D6. Root `package.json` Metadata:** Ensure `package.json` contains:
  - `name`: "x402-mcp"
  - `version`: "0.1.0"
  - `description`: Comprehensive summary of x402 MCP server
  - `keywords`: `["mcp", "model-context-protocol", "x402", "micropayments", "base", "usdc", "smithery", "ai-agents"]`
  - `author`: "kwizzlesurp10-ctrl"
  - `license`: "MIT"
  - `repository`: `{"type": "git", "url": "https://github.com/kwizzlesurp10-ctrl/x402-mcp.git"}`
  - `homepage`: "https://github.com/kwizzlesurp10-ctrl/x402-mcp#readme"

---

## 4. Detailed Specification for All 19 MCP Tools

Below is the exhaustive specification for each of the 19 tools in `x402-mcp`, including exact behavioral annotations, Agent ID cards, and parameter typing:

```
┌────┬─────────────────────────────────┬──────────────┬───────────────┬───────────────────────────────┐
│ #  │ Tool Name                       │ Role         │ Tier / Price  │ Behavioral Annotations        │
├────┼─────────────────────────────────┼──────────────┼───────────────┼───────────────────────────────┤
│ 1  │ discover_services               │ indexer      │ Free          │ readOnly=T, destr=F, idemp=T  │
│ 2  │ get_payment_requirements        │ oracle       │ Free          │ readOnly=T, destr=F, idemp=T  │
│ 3  │ pay_and_fetch                   │ settler      │ Paid (x402)   │ readOnly=F, destr=T, idemp=F  │
│ 4  │ build_seller_requirements       │ broker       │ Free          │ readOnly=T, destr=F, idemp=T  │
│ 5  │ verify_payment_payload          │ verifier     │ Free          │ readOnly=T, destr=F, idemp=T  │
│ 6  │ get_supported_networks          │ oracle       │ Free          │ readOnly=T, destr=F, idemp=T  │
│ 7  │ get_pro_upgrade_requirements    │ broker       │ Free          │ readOnly=T, destr=F, idemp=T  │
│ 8  │ activate_pro_tier               │ settler      │ Paid (x402)   │ readOnly=F, destr=T, idemp=F  │
│ 9  │ get_tool_credits_requirements   │ broker       │ Free          │ readOnly=T, destr=F, idemp=T  │
│ 10 │ purchase_tool_credits           │ settler      │ Paid (x402)   │ readOnly=F, destr=T, idemp=F  │
│ 11 │ create_stripe_checkout          │ checkout     │ Fiat          │ readOnly=F, destr=F, idemp=T  │
│ 12 │ run_swarm_research              │ investigator │ Free / Paid   │ readOnly=F, destr=F, idemp=F  │
│ 13 │ settle_composite_sale           │ settler      │ Sell-side     │ readOnly=F, destr=T, idemp=F  │
│ 14 │ swarm_revenue_report            │ telemetry    │ Free          │ readOnly=T, destr=F, idemp=T  │
│ 15 │ get_base_pulse                  │ oracle       │ Free          │ readOnly=T, destr=F, idemp=T  │
│ 16 │ get_os_metrics                  │ telemetry    │ Free          │ readOnly=T, destr=F, idemp=T  │
│ 17 │ list_us_cities                  │ indexer      │ Free          │ readOnly=T, destr=F, idemp=T  │
│ 18 │ get_us_city_property_sample     │ oracle       │ Free (sample) │ readOnly=T, destr=F, idemp=T  │
│ 19 │ check_us_city_property          │ investigator │ $0.01 USDC    │ readOnly=T, destr=F, idemp=T  │
└────┴─────────────────────────────────┴──────────────┴───────────────┴───────────────────────────────┘
```

### 4.1 Tool Specifications in Detail

#### 1. `discover_services`
- **Title:** "Discover x402 Services"
- **Docstring:** "Discover x402 Bazaar paid HTTP services via x402 HTTPFacilitatorClient. Queries active decentralized services accepting EIP-3009 micropayments."
- **Annotations:** `readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True`
- **Agent Card:**
  - `id`: `x402-discover-services`
  - `role`: `indexer`
  - `domain`: `micropayments`
  - `pricing`: `{"model": "free"}`
  - `examples`: `["Find available paid APIs for real estate data", "Search for x402 services under 0.05 USDC"]`

#### 2. `get_payment_requirements`
- **Title:** "Probe HTTP 402 Payment Requirements"
- **Docstring:** "Probe a target URL for HTTP 402 PAYMENT-REQUIRED terms and returns structured payment requirements (payTo, amount, asset, network, scheme)."
- **Annotations:** `readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True`
- **Agent Card:**
  - `id`: `x402-probe-requirements`
  - `role`: `oracle`
  - `domain`: `micropayments`
  - `pricing`: `{"model": "free"}`
  - `examples`: `["Probe https://x402-mcp.onrender.com/us/sea/property-check for payment terms"]`

#### 3. `pay_and_fetch`
- **Title:** "Pay via x402 and Fetch Resource"
- **Docstring:** "Sign an EIP-3009 payment authorization using EVM_PRIVATE_KEY, pay the HTTP 402 challenge, and fetch the protected resource."
- **Annotations:** `readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=True`
- **Agent Card:**
  - `id`: `x402-pay-and-fetch`
  - `role`: `settler`
  - `domain`: `micropayments`
  - `pricing`: `{"model": "paid_per_call", "settlement_protocol": "x402-v2"}`
  - `examples`: `["Pay 0.01 USDC and fetch the protected compliance report from https://x402-mcp.onrender.com/us/sea/property-check?address=123+Main+St"]`

#### 4. `build_seller_requirements`
- **Title:** "Build Seller Payment Requirements"
- **Docstring:** "Generate standard x402 v2 payment requirements challenge for sellers to protect their HTTP endpoints."
- **Annotations:** `readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False`
- **Agent Card:**
  - `id`: `x402-seller-requirements-builder`
  - `role`: `broker`
  - `domain`: `commerce`
  - `pricing`: `{"model": "free"}`
  - `examples`: `["Generate payment requirements to charge $0.05 USDC on Base for my API"]`

#### 5. `verify_payment_payload`
- **Title:** "Verify Payment Payload"
- **Docstring:** "Verify a buyer's PAYMENT-SIGNATURE against PAYMENT-REQUIRED challenge using facilitator settlement."
- **Annotations:** `readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True`
- **Agent Card:**
  - `id`: `x402-verify-payment`
  - `role`: `verifier`
  - `domain`: `micropayments`
  - `pricing`: `{"model": "free"}`
  - `examples`: `["Verify inbound EIP-3009 signature payload before serving data"]`

#### 6. `get_supported_networks`
- **Title:** "Get Supported Networks & Headers"
- **Docstring:** "List supported payment networks (Base mainnet, Base Sepolia), default facilitators, and protocol v2 header specifications."
- **Annotations:** `readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False`
- **Agent Card:**
  - `id`: `x402-supported-networks`
  - `role`: `oracle`
  - `domain`: `micropayments`
  - `pricing`: `{"model": "free"}`
  - `examples`: `["What blockchain networks and headers does this x402 server support?"]`

#### 7. `get_pro_upgrade_requirements`
- **Title:** "Get Pro Tier Upgrade Requirements"
- **Docstring:** "Generate x402 payment requirements to upgrade the calling agent to the Pro tier (unlimited monthly calls, increased rate limits)."
- **Annotations:** `readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False`
- **Agent Card:**
  - `id`: `x402-pro-upgrade-requirements`
  - `role`: `broker`
  - `domain`: `commerce`
  - `pricing`: `{"model": "subscription_upgrade"}`
  - `examples`: `["How do I upgrade this agent to Pro tier via x402?"]`

#### 8. `activate_pro_tier`
- **Title:** "Activate Pro Tier"
- **Docstring:** "Verify x402 payment signature for Pro tier upgrade and immediately unlock higher quota limits for the agent."
- **Annotations:** `readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=True`
- **Agent Card:**
  - `id`: `x402-activate-pro`
  - `role`: `settler`
  - `domain`: `commerce`
  - `pricing`: `{"model": "subscription_upgrade"}`
  - `examples`: `["Activate Pro tier with signed x402 payment authorization"]`

#### 9. `get_tool_credits_requirements`
- **Title:** "Get Tool Credits Requirements"
- **Docstring:** "Build x402 payment requirements for purchasing per-use tool credit packs."
- **Annotations:** `readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False`
- **Agent Card:**
  - `id`: `x402-tool-credits-requirements`
  - `role`: `broker`
  - `domain`: `commerce`
  - `pricing`: `{"model": "credit_pack"}`
  - `examples`: `["Buy 100 tool credits for this agent"]`

#### 10. `purchase_tool_credits`
- **Title:** "Purchase Tool Credits"
- **Docstring:** "Verify x402 payment and credit per-use tool call balance to the agent account."
- **Annotations:** `readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=True`
- **Agent Card:**
  - `id`: `x402-purchase-tool-credits`
  - `role`: `settler`
  - `domain`: `commerce`
  - `pricing`: `{"model": "credit_pack"}`
  - `examples`: `["Settle x402 payment to add 50 tool credits"]`

#### 11. `create_stripe_checkout`
- **Title:** "Create Stripe Checkout Session"
- **Docstring:** "Create a Stripe Checkout Session URL for fiat payment rail (credit card/bank) for Pro tier or credit packs."
- **Annotations:** `readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=True`
- **Agent Card:**
  - `id`: `x402-stripe-checkout`
  - `role`: `checkout`
  - `domain`: `commerce`
  - `pricing`: `{"model": "free", "settlement_protocol": "stripe-fiat"}`
  - `examples`: `["Generate a Stripe checkout link to pay with credit card"]`

#### 12. `run_swarm_research`
- **Title:** "Run Swarm Research Agency"
- **Docstring:** "Synthesize a composite research product across multiple sources, optionally buy upstream x402 intelligence, and catalog it for resale."
- **Annotations:** `readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=True`
- **Agent Card:**
  - `id`: `x402-swarm-research`
  - `role`: `investigator`
  - `domain`: `micropayments`
  - `pricing`: `{"model": "free"}`
  - `examples`: `["Run autonomous swarm research on Base L2 gas trends and list report"]`

#### 13. `settle_composite_sale`
- **Title:** "Settle Composite Sale"
- **Docstring:** "Verify and settle buyer payment for a listed swarm research product and credit earned revenue."
- **Annotations:** `readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=True`
- **Agent Card:**
  - `id`: `x402-settle-sale`
  - `role`: `settler`
  - `domain`: `commerce`
  - `pricing`: `{"model": "paid_per_call"}`
  - `examples`: `["Settle inbound payment for research artifact #402"]`

#### 14. `swarm_revenue_report`
- **Title:** "Swarm Revenue Intelligence Report"
- **Docstring:** "Query realized portfolio revenue, upstream spend, margins, LTV:CAC, and per-source profitability scores."
- **Annotations:** `readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False`
- **Agent Card:**
  - `id`: `x402-swarm-revenue`
  - `role`: `telemetry`
  - `domain`: `commerce`
  - `pricing`: `{"model": "free"}`
  - `examples`: `["Show total revenue and profit margins from swarm product sales"]`

#### 15. `get_base_pulse`
- **Title:** "Base Network Settlement Pulse"
- **Docstring:** "Live Base Network settlement conditions from real RPC: base fee, EIP-1559 trend, block utilization, estimated USD transfer cost, and settle-now vs wait verdict."
- **Annotations:** `readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True`
- **Agent Card:**
  - `id`: `base-network-pulse`
  - `role`: `oracle`
  - `domain`: `blockchain-gas-optimization`
  - `pricing`: `{"model": "free"}`
  - `examples`: `["Is Base network congested right now?", "What is the recommended gas fee for Base tx?"]`

#### 16. `get_os_metrics`
- **Title:** "Host OS Telemetry"
- **Docstring:** "Sample host OS telemetry: CPU load, memory utilization, swap, disk space, network IO, and process health verdict."
- **Annotations:** `readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False`
- **Agent Card:**
  - `id`: `host-os-telemetry`
  - `role`: `telemetry`
  - `domain`: `systems-ops`
  - `pricing`: `{"model": "free"}`
  - `examples`: `["Check server CPU and memory load", "Get health verdict for host instance"]`

#### 17. `list_us_cities`
- **Title:** "List US Compliance Network Cities"
- **Docstring:** "Free catalog of supported US city open-data jurisdictions (city codes, paid endpoint, sample endpoint, sample address, and sources label)."
- **Annotations:** `readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False`
- **Agent Card:**
  - `id`: `us-cities-catalog`
  - `role`: `indexer`
  - `domain`: `real-estate-compliance`
  - `pricing`: `{"model": "free"}`
  - `examples`: `["Which US cities are supported for rental compliance checks?"]`

#### 18. `get_us_city_property_sample`
- **Title:** "Get US City Compliance Sample"
- **Docstring:** "Free fixed-address property compliance sample for any supported city code (e.g. mn, sea, chi, nyc). Returns identical JSON schema to paid check without payment."
- **Annotations:** `readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True`
- **Agent Card:**
  - `id`: `us-city-compliance-sample`
  - `role`: `oracle`
  - `domain`: `real-estate-compliance`
  - `pricing`: `{"model": "free"}`
  - `examples`: `["Show me a sample property compliance report for Seattle (city=sea)"]`

#### 19. `check_us_city_property`
- **Title:** "Check US City Property Compliance (Paid)"
- **Docstring:** "Paid address-level rental license, building violation, and housing code compliance report for any supported US city. Settles $0.01 USDC on Base via x402."
- **Annotations:** `readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True`
- **Agent Card:**
  - `id`: `us-city-property-check`
  - `role`: `investigator`
  - `domain`: `real-estate-compliance`
  - `pricing`: `{"model": "paid_per_call", "price_usdc": "$0.01", "network": "eip155:8453", "settlement_protocol": "x402-v2"}`
  - `examples`: `["Check rental license and code violations for 1700 Penn Ave N in Minneapolis (city=mn)"]`

---

## 5. Verification & Audit Strategy

To prove compliance with the Smithery.ai 100/100 standard:
1. **Tool Annotations & Card Audit:** A programmatic test must iterate over `mcp._tool_manager._tools.values()` and verify that every tool possesses:
   - `annotations.title`
   - `annotations.readOnlyHint` (bool)
   - `annotations.destructiveHint` (bool)
   - `annotations.idempotentHint` (bool)
   - `annotations.openWorldHint` (bool)
   - `annotations.agent_card` dictionary with `id`, `name`, `role`, `domain`, `pricing`, `execution_profile`, and `examples`.
2. **Schema Description Coverage:** Check that every property in `t.input_schema["properties"]` has a non-empty `description`.
3. **`smithery.yaml` Schema Validation:** Validate that `smithery.yaml` contains `startCommand.type: "stdio"`, `startCommand.configSchema.properties`, and `commandFunction`.
4. **`package.json` Fields Validation:** Ensure `name`, `version`, `description`, `author`, `license`, `repository`, and `keywords` are non-empty.
5. **README Badge & Quickstart Audit:** Verify Smithery markdown badge and `npx @smithery/cli` install command are present.
