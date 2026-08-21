"""FastMCP tool, prompt, and resource registrations for x402 micropayments."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Annotated, Any
from urllib.parse import urlparse

from pydantic import Field
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from app.commerce import QuotaExceededError, quota_store
from app.config import settings
from app.models import (
    BuildSellerRequirementsInput,
    DiscoverServicesInput,
    GetPaymentRequirementsInput,
    PayAndFetchInput,
    ToolResponse,
    VerifyPaymentInput,
)
from app import stripe_payments, x402_services
from app.ops_events import emit_tool_event
from app.swarm import orchestrator as swarm_orchestrator


def _transport_security() -> TransportSecuritySettings:
    """Allow this deployment's own hostname through DNS-rebinding protection.

    FastMCP defaults to allowing localhost only, so on a public host every
    Streamable HTTP request is rejected with 421 "Invalid Host header" and the
    server is unreachable to any remote MCP client — which is most of the point
    of deploying it. The protection stays ON; the deployment's own host is added
    to the allowlist rather than the check being switched off.
    """
    allowed = ["127.0.0.1:*", "localhost:*", "[::1]:*"]
    origins = ["http://localhost:*", "http://127.0.0.1:*"]
    public = urlparse(settings.public_base_url).netloc
    if public and not public.startswith(("localhost", "127.0.0.1")):
        allowed.append(public)
        origins.append(f"https://{public}")
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=allowed,
        allowed_origins=origins,
    )


mcp = FastMCP(
    "x402-micropayments",
    instructions=(
        "Production MCP server for x402 HTTP micropayments on Base mainnet (EIP-3009 USDC). "
        "Capabilities include: (1) Buyer tools to discover paid services, probe HTTP 402 requirements, "
        "and pay-and-fetch protected resources; (2) Seller tools to build and verify PAYMENT-REQUIRED "
        "challenges with x402 Bazaar discovery metadata; (3) US City Open-Data Property Compliance Network "
        "(14 jurisdictions): list_us_cities → get_us_city_property_sample (free) → check_us_city_property ($0.01 USDC); "
        "(4) Base Network Pulse (EIP-1559 gas conditions & settlement verdict); (5) Host OS telemetry; "
        "(6) Agent ID cards (get_agent_card & x402://agent-card); (7) Prompts for onboarding, tool selection, "
        "quote generation, and payment troubleshooting. Every tool execution is quota-tracked and returns a ResponseMeta envelope."
    ),
    transport_security=_transport_security(),
)


async def _execute_tool(
    tool_name: str,
    agent_id: str | None,
    work: Callable[[str], Awaitable[dict[str, Any]]],
) -> str:
    """Preemptive quota enforcement, then execute work, then attach meta."""
    resolved = quota_store.resolve_agent_id(agent_id)
    try:
        snapshot = quota_store.consume_quota(resolved)
    except QuotaExceededError as exc:
        return json.dumps({"error": exc.detail, "data": None, "meta": None}, indent=2)

    data = await work(resolved)
    meta = quota_store.build_meta(snapshot)
    emit_tool_event(tool_name, resolved, meta.model_dump())
    payload = ToolResponse(data=data, meta=meta)
    return json.dumps(payload.model_dump(), indent=2)


async def _sync_result(data: dict[str, Any]) -> dict[str, Any]:
    return data


# ============================================================================
# 1. MCP Tools (20 Tools)
# ============================================================================


@mcp.tool(
    annotations={
        "title": "Discover x402 Services",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
        "agent_card": {
            "id": "x402-discover-services",
            "name": "x402 Bazaar Service Discovery",
            "role": "indexer",
            "domain": "micropayments",
            "version": "0.1.0",
            "pricing": {"model": "free"},
            "execution_profile": {
                "read_only": True,
                "destructive": False,
                "idempotent": True,
                "open_world": True,
            },
            "input_modes": ["application/json", "text/plain"],
            "output_modes": ["application/json"],
            "tags": ["discovery", "bazaar", "search", "services", "catalog", "x402", "free"],
            "examples": [
                "Find available paid APIs for real estate data",
                "Search for x402 services under 0.05 USDC",
            ],
        },
    }
)
async def discover_services(
    query: Annotated[
        str | None,
        Field(description="Optional search keyword to filter discovered x402 services by name or description"),
    ] = None,
    limit: Annotated[
        int,
        Field(description="Maximum number of discovered services to return (default: 20, range 1-100)"),
    ] = 20,
    max_price_usdc: Annotated[
        float | None,
        Field(description="Optional maximum price filter in USDC per service call"),
    ] = None,
    agent_id: Annotated[
        str | None,
        Field(description="Optional calling agent identifier for quota tracking and telemetry isolation"),
    ] = None,
) -> str:
    """Discover x402 Bazaar paid HTTP services via x402 HTTPFacilitatorClient.

    Queries active decentralized services accepting EIP-3009 micropayments across the ecosystem.

    Args:
        query: Optional search keyword to filter discovered x402 services.
        limit: Maximum number of discovered services to return (1-100).
        max_price_usdc: Optional maximum price filter in USDC.
        agent_id: Optional calling agent identifier for quota tracking and isolation.

    Returns:
        JSON string containing ToolResponse envelope with discovered services list in data and quota metadata in meta.
    """
    params = DiscoverServicesInput(
        query=query, limit=limit, max_price_usdc=max_price_usdc
    )
    return await _execute_tool(
        "discover_services", agent_id, lambda _: x402_services.discover_services(params)
    )


@mcp.tool(
    annotations={
        "title": "Probe HTTP 402 Payment Requirements",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
        "agent_card": {
            "id": "x402-probe-requirements",
            "name": "HTTP 402 Payment Probe",
            "role": "oracle",
            "domain": "micropayments",
            "version": "0.1.0",
            "pricing": {"model": "free"},
            "execution_profile": {
                "read_only": True,
                "destructive": False,
                "idempotent": True,
                "open_world": True,
            },
            "input_modes": ["application/json", "text/plain"],
            "output_modes": ["application/json"],
            "tags": ["probe", "402", "headers", "requirements", "x402", "free"],
            "examples": [
                "Probe https://x402-mcp.onrender.com/us/sea/property-check for payment terms",
                "Inspect the PAYMENT-REQUIRED challenge for a target URL before paying",
            ],
        },
    }
)
async def get_payment_requirements(
    url: Annotated[
        str,
        Field(description="Target HTTP URL to probe for HTTP 402 PAYMENT-REQUIRED terms and challenge headers"),
    ],
    method: Annotated[
        str,
        Field(description="HTTP method to use when probing the endpoint (default: GET)"),
    ] = "GET",
    headers: Annotated[
        dict[str, str] | None,
        Field(description="Optional dictionary of custom HTTP request headers to include in probe"),
    ] = None,
    agent_id: Annotated[
        str | None,
        Field(description="Optional calling agent identifier for quota tracking and telemetry isolation"),
    ] = None,
) -> str:
    """Probe a target URL for HTTP 402 PAYMENT-REQUIRED terms using x402HTTPClient SDK.

    Inspects the server's response headers to decode payTo address, asset, amount,
    network, and scheme without executing payment.

    Args:
        url: Target HTTP URL to probe for HTTP 402 terms.
        method: HTTP method to use for probe request (default: GET).
        headers: Optional dictionary of HTTP headers.
        agent_id: Optional calling agent identifier for quota tracking and isolation.

    Returns:
        JSON string containing ToolResponse envelope with decoded 402 payment requirements in data and quota metadata in meta.
    """
    params = GetPaymentRequirementsInput(
        url=url, method=method, headers=headers or {}
    )
    return await _execute_tool(
        "get_payment_requirements",
        agent_id,
        lambda _: x402_services.get_payment_requirements(params),
    )


@mcp.tool(
    annotations={
        "title": "Pay via x402 and Fetch Resource",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": False,
        "openWorldHint": True,
        "agent_card": {
            "id": "x402-pay-and-fetch",
            "name": "x402 Automatic Payment & Fetch Client",
            "role": "settler",
            "domain": "micropayments",
            "version": "0.1.0",
            "pricing": {
                "model": "paid_per_call",
                "settlement_protocol": "x402-v2",
            },
            "execution_profile": {
                "read_only": False,
                "destructive": True,
                "idempotent": False,
                "open_world": True,
            },
            "input_modes": ["application/json", "text/plain"],
            "output_modes": ["application/json"],
            "tags": ["pay", "fetch", "eip3009", "usdc", "settlement", "x402"],
            "examples": [
                "Pay 0.01 USDC and fetch the protected compliance report from https://x402-mcp.onrender.com/us/sea/property-check?address=123+Main+St",
                "Sign EIP-3009 payment authorization and retrieve paid API data",
            ],
        },
    }
)
async def pay_and_fetch(
    url: Annotated[
        str,
        Field(description="Protected HTTP URL requiring x402 payment authorization to fetch"),
    ],
    method: Annotated[
        str,
        Field(description="HTTP method to use for the request (default: GET)"),
    ] = "GET",
    headers: Annotated[
        dict[str, str] | None,
        Field(description="Optional custom HTTP headers to send with the payment request"),
    ] = None,
    body: Annotated[
        str | None,
        Field(description="Optional HTTP request body string for POST/PUT requests"),
    ] = None,
    preferred_network: Annotated[
        str | None,
        Field(description="Preferred CAIP-2 blockchain network identifier (e.g. 'eip155:8453')"),
    ] = None,
    max_price_usdc: Annotated[
        float | None,
        Field(description="Maximum price threshold in USDC the agent is willing to pay"),
    ] = None,
    agent_id: Annotated[
        str | None,
        Field(description="Optional calling agent identifier for quota tracking and telemetry isolation"),
    ] = None,
) -> str:
    """Sign an EIP-3009 payment authorization using EVM_PRIVATE_KEY, pay the HTTP 402 challenge, and fetch the protected resource.

    Settles USDC on Base mainnet or testnet via facilitator and returns the paid content.

    Args:
        url: Protected HTTP URL requiring x402 payment.
        method: HTTP method to use (default: GET).
        headers: Optional HTTP headers dictionary.
        body: Optional HTTP request body string.
        preferred_network: Preferred CAIP-2 blockchain network identifier.
        max_price_usdc: Maximum price limit in USDC.
        agent_id: Optional calling agent identifier for quota tracking and isolation.

    Returns:
        JSON string containing ToolResponse envelope with fetched data and settlement receipt in data and quota metadata in meta.
    """
    params = PayAndFetchInput(
        url=url,
        method=method,
        headers=headers or {},
        body=body,
        preferred_network=preferred_network,
        max_price_usdc=max_price_usdc,
    )
    return await _execute_tool(
        "pay_and_fetch", agent_id, lambda _: x402_services.pay_and_fetch(params)
    )


@mcp.tool(
    annotations={
        "title": "Build Seller Payment Requirements",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
        "agent_card": {
            "id": "x402-seller-requirements-builder",
            "name": "Seller Payment Requirements Builder",
            "role": "broker",
            "domain": "commerce",
            "version": "0.1.0",
            "pricing": {"model": "free"},
            "execution_profile": {
                "read_only": True,
                "destructive": False,
                "idempotent": True,
                "open_world": False,
            },
            "input_modes": ["application/json", "text/plain"],
            "output_modes": ["application/json"],
            "tags": ["seller", "402", "headers", "bazaar", "monetization", "commerce", "free"],
            "examples": [
                "Generate payment requirements to charge $0.05 USDC on Base for my API",
                "Build base64 PAYMENT-REQUIRED challenge header with Bazaar discovery metadata",
            ],
        },
    }
)
async def build_seller_requirements(
    network: Annotated[
        str,
        Field(description="CAIP-2 network identifier where seller receives funds (default: 'eip155:84532')"),
    ] = "eip155:84532",
    pay_to: Annotated[
        str | None,
        Field(description="Seller EVM wallet address to receive funds (defaults to X402_PAY_TO_ADDRESS)"),
    ] = None,
    price: Annotated[
        str,
        Field(description="Human-readable price string (e.g. '$0.01' or '0.01')"),
    ] = "$0.01",
    scheme: Annotated[
        str,
        Field(description="Payment scheme type (default: 'exact')"),
    ] = "exact",
    description: Annotated[
        str,
        Field(description="Human/model-readable description of the protected service or API"),
    ] = "Paid MCP-backed API access",
    resource_url: Annotated[
        str | None,
        Field(description="Canonical public URL of the resource to embed in Bazaar discovery extension"),
    ] = None,
    mime_type: Annotated[
        str | None,
        Field(description="MIME type of the resource response (default: 'application/json')"),
    ] = "application/json",
    discoverable: Annotated[
        bool | None,
        Field(description="Whether to mark the resource as public in the x402 Bazaar catalog"),
    ] = None,
    discovery_method: Annotated[
        str,
        Field(description="HTTP method for Bazaar invocation (default: 'GET')"),
    ] = "GET",
    discovery_input_example: Annotated[
        dict | None,
        Field(description="Example JSON input dictionary for Bazaar discovery metadata"),
    ] = None,
    discovery_output_example: Annotated[
        dict | None,
        Field(description="Example JSON output dictionary for Bazaar discovery metadata"),
    ] = None,
    agent_id: Annotated[
        str | None,
        Field(description="Optional calling agent identifier for quota tracking and telemetry isolation"),
    ] = None,
) -> str:
    """Build seller-side x402 payment requirements via x402ResourceServer.

    Pass resource_url (plus optional discovery_* fields) to embed the Bazaar
    discovery extension so a settled payment catalogs the endpoint.

    Args:
        network: CAIP-2 network identifier.
        pay_to: Seller EVM address to receive payments.
        price: Price string (e.g. '$0.01').
        scheme: Payment scheme (default: exact).
        description: Description of service being monetized.
        resource_url: Canonical resource URL for Bazaar discovery.
        mime_type: MIME type of response (default: application/json).
        discoverable: Whether endpoint is public in Bazaar.
        discovery_method: HTTP method (default: GET).
        discovery_input_example: Example request structure.
        discovery_output_example: Example response structure.
        agent_id: Optional calling agent identifier for quota tracking and isolation.

    Returns:
        JSON string containing ToolResponse envelope with base64 challenge and parsed requirements in data and quota metadata in meta.
    """
    params = BuildSellerRequirementsInput(
        network=network,
        pay_to=pay_to,
        price=price,
        scheme=scheme,
        description=description,
        resource_url=resource_url,
        mime_type=mime_type,
        discoverable=discoverable,
        discovery_method=discovery_method,
        discovery_input_example=discovery_input_example,
        discovery_output_example=discovery_output_example,
    )
    return await _execute_tool(
        "build_seller_requirements",
        agent_id,
        lambda _: _sync_result(x402_services.build_seller_requirements(params)),
    )


@mcp.tool(
    annotations={
        "title": "Verify Payment Payload",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
        "agent_card": {
            "id": "x402-verify-payment",
            "name": "Payment Payload Verifier",
            "role": "verifier",
            "domain": "micropayments",
            "version": "0.1.0",
            "pricing": {"model": "free"},
            "execution_profile": {
                "read_only": True,
                "destructive": False,
                "idempotent": True,
                "open_world": True,
            },
            "input_modes": ["application/json", "text/plain"],
            "output_modes": ["application/json"],
            "tags": ["verify", "settlement", "signature", "eip3009", "facilitator", "free"],
            "examples": [
                "Verify inbound EIP-3009 signature payload before serving data",
                "Validate buyer PAYMENT-SIGNATURE against PAYMENT-REQUIRED challenge",
            ],
        },
    }
)
async def verify_payment_payload(
    payment_signature: Annotated[
        str,
        Field(description="Base64-encoded or raw JSON string of buyer's PAYMENT-SIGNATURE header"),
    ],
    payment_required: Annotated[
        str,
        Field(description="Base64-encoded or raw JSON string of seller's PAYMENT-REQUIRED challenge header"),
    ],
    agent_id: Annotated[
        str | None,
        Field(description="Optional calling agent identifier for quota tracking and telemetry isolation"),
    ] = None,
) -> str:
    """Verify PAYMENT-SIGNATURE via x402ResourceServer + facilitator.

    Validates buyer's EIP-3009 cryptographic signature and checks settlement terms.

    Args:
        payment_signature: Buyer's PAYMENT-SIGNATURE payload.
        payment_required: Seller's PAYMENT-REQUIRED challenge payload.
        agent_id: Optional calling agent identifier for quota tracking and isolation.

    Returns:
        JSON string containing ToolResponse envelope with verification verdict in data and quota metadata in meta.
    """
    params = VerifyPaymentInput(
        payment_signature=payment_signature,
        payment_required=payment_required,
    )
    return await _execute_tool(
        "verify_payment_payload",
        agent_id,
        lambda _: x402_services.verify_payment_payload(params),
    )


@mcp.tool(
    annotations={
        "title": "Get Supported Networks & Headers",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
        "agent_card": {
            "id": "x402-supported-networks",
            "name": "Supported Networks & Protocol Oracle",
            "role": "oracle",
            "domain": "micropayments",
            "version": "0.1.0",
            "pricing": {"model": "free"},
            "execution_profile": {
                "read_only": True,
                "destructive": False,
                "idempotent": True,
                "open_world": False,
            },
            "input_modes": ["application/json", "text/plain"],
            "output_modes": ["application/json"],
            "tags": ["networks", "caip2", "chains", "facilitators", "headers", "free"],
            "examples": [
                "What blockchain networks and headers does this x402 server support?",
                "List supported CAIP-2 chain identifiers and active facilitators",
            ],
        },
    }
)
async def get_supported_networks(
    agent_id: Annotated[
        str | None,
        Field(description="Optional calling agent identifier for quota tracking and telemetry isolation"),
    ] = None,
) -> str:
    """List supported blockchain networks, facilitators, and protocol v2 header specifications.

    Args:
        agent_id: Optional calling agent identifier for quota tracking and isolation.

    Returns:
        JSON string containing ToolResponse envelope with supported CAIP-2 chains and header specs in data and quota metadata in meta.
    """
    return await _execute_tool(
        "get_supported_networks",
        agent_id,
        lambda _: _sync_result(x402_services.get_supported_networks().model_dump()),
    )


@mcp.tool(
    annotations={
        "title": "Get Pro Tier Upgrade Requirements",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
        "agent_card": {
            "id": "x402-pro-upgrade-requirements",
            "name": "Pro Tier Upgrade Broker",
            "role": "broker",
            "domain": "commerce",
            "version": "0.1.0",
            "pricing": {"model": "subscription_upgrade"},
            "execution_profile": {
                "read_only": True,
                "destructive": False,
                "idempotent": True,
                "open_world": False,
            },
            "input_modes": ["application/json", "text/plain"],
            "output_modes": ["application/json"],
            "tags": ["pro", "upgrade", "quota", "subscription", "pricing", "commerce"],
            "examples": [
                "How do I upgrade this agent to Pro tier via x402?",
                "Generate x402 payment requirements for Pro monthly subscription",
            ],
        },
    }
)
async def get_pro_upgrade_requirements(
    agent_id: Annotated[
        str | None,
        Field(description="Optional calling agent identifier for quota tracking and telemetry isolation"),
    ] = None,
) -> str:
    """Build x402 payment requirements to purchase Pro tier (revenue collection).

    Generates the payment challenge required to upgrade calling agent to Pro tier
    (50,000 calls/month, 120 calls/minute rate limit).

    Args:
        agent_id: Optional calling agent identifier for quota tracking and isolation.

    Returns:
        JSON string containing ToolResponse envelope with Pro upgrade challenge in data and quota metadata in meta.
    """
    return await _execute_tool(
        "get_pro_upgrade_requirements",
        agent_id,
        lambda resolved: _sync_result(
            x402_services.build_pro_upgrade_requirements(resolved)
        ),
    )


@mcp.tool(
    annotations={
        "title": "Activate Pro Tier",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": False,
        "openWorldHint": True,
        "agent_card": {
            "id": "x402-activate-pro",
            "name": "Pro Tier Activation Settler",
            "role": "settler",
            "domain": "commerce",
            "version": "0.1.0",
            "pricing": {"model": "subscription_upgrade"},
            "execution_profile": {
                "read_only": False,
                "destructive": True,
                "idempotent": False,
                "open_world": True,
            },
            "input_modes": ["application/json", "text/plain"],
            "output_modes": ["application/json"],
            "tags": ["pro", "activate", "settlement", "subscription", "commerce"],
            "examples": [
                "Activate Pro tier with signed x402 payment authorization",
                "Unlock 50k monthly calls quota with verified EIP-3009 payment",
            ],
        },
    }
)
async def activate_pro_tier(
    payment_signature: Annotated[
        str,
        Field(description="Buyer's signed PAYMENT-SIGNATURE payload authorizing Pro tier fee"),
    ],
    payment_required: Annotated[
        str,
        Field(description="Original PAYMENT-REQUIRED challenge generated by get_pro_upgrade_requirements"),
    ],
    agent_id: Annotated[
        str | None,
        Field(description="Optional calling agent identifier for quota tracking and telemetry isolation"),
    ] = None,
) -> str:
    """Verify pro-tier x402 payment and unlock Pro quota limits.

    Immediately upgrades the calling agent's monthly quota and per-minute rate limits.

    Args:
        payment_signature: Signed PAYMENT-SIGNATURE payload.
        payment_required: Pro upgrade PAYMENT-REQUIRED challenge.
        agent_id: Optional calling agent identifier for quota tracking and isolation.

    Returns:
        JSON string containing ToolResponse envelope with activation receipt and updated tier in data and quota metadata in meta.
    """
    return await _execute_tool(
        "activate_pro_tier",
        agent_id,
        lambda resolved: x402_services.activate_pro_tier(
            payment_signature, payment_required, resolved
        ),
    )


@mcp.tool(
    annotations={
        "title": "Get Tool Credits Requirements",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
        "agent_card": {
            "id": "x402-tool-credits-requirements",
            "name": "Tool Credits Pack Broker",
            "role": "broker",
            "domain": "commerce",
            "version": "0.1.0",
            "pricing": {"model": "credit_pack"},
            "execution_profile": {
                "read_only": True,
                "destructive": False,
                "idempotent": True,
                "open_world": False,
            },
            "input_modes": ["application/json", "text/plain"],
            "output_modes": ["application/json"],
            "tags": ["credits", "pack", "broker", "pricing", "commerce"],
            "examples": [
                "Buy 100 tool credits for this agent",
                "Get payment terms for purchasing a pack of 50 tool credits",
            ],
        },
    }
)
async def get_tool_credits_requirements(
    credits: Annotated[
        int | None,
        Field(description="Number of tool credits to purchase (default: configured pack size e.g. 100)"),
    ] = None,
    agent_id: Annotated[
        str | None,
        Field(description="Optional calling agent identifier for quota tracking and telemetry isolation"),
    ] = None,
) -> str:
    """Build x402 payment requirements to purchase per-use MCP tool credits.

    Args:
        credits: Optional number of credits to buy.
        agent_id: Optional calling agent identifier for quota tracking and isolation.

    Returns:
        JSON string containing ToolResponse envelope with credits purchase challenge in data and quota metadata in meta.
    """
    pack = credits or settings.tool_credit_pack_size

    return await _execute_tool(
        "get_tool_credits_requirements",
        agent_id,
        lambda resolved: _sync_result(
            x402_services.build_tool_credits_requirements(resolved, pack)
        ),
    )


@mcp.tool(
    annotations={
        "title": "Purchase Tool Credits",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": False,
        "openWorldHint": True,
        "agent_card": {
            "id": "x402-purchase-tool-credits",
            "name": "Tool Credits Settler",
            "role": "settler",
            "domain": "commerce",
            "version": "0.1.0",
            "pricing": {"model": "credit_pack"},
            "execution_profile": {
                "read_only": False,
                "destructive": True,
                "idempotent": False,
                "open_world": True,
            },
            "input_modes": ["application/json", "text/plain"],
            "output_modes": ["application/json"],
            "tags": ["credits", "settlement", "purchase", "commerce"],
            "examples": [
                "Settle x402 payment to add 50 tool credits",
                "Verify payment and credit per-use tool balance",
            ],
        },
    }
)
async def purchase_tool_credits(
    payment_signature: Annotated[
        str,
        Field(description="Buyer's signed PAYMENT-SIGNATURE payload authorizing tool credits fee"),
    ],
    payment_required: Annotated[
        str,
        Field(description="Original PAYMENT-REQUIRED challenge from get_tool_credits_requirements"),
    ],
    credits: Annotated[
        int | None,
        Field(description="Number of tool credits being purchased (default: configured pack size)"),
    ] = None,
    agent_id: Annotated[
        str | None,
        Field(description="Optional calling agent identifier for quota tracking and telemetry isolation"),
    ] = None,
) -> str:
    """Verify x402 payment and add per-use tool credits (per-call revenue path).

    Args:
        payment_signature: Signed PAYMENT-SIGNATURE payload.
        payment_required: Original challenge payload.
        credits: Optional number of credits purchased.
        agent_id: Optional calling agent identifier for quota tracking and isolation.

    Returns:
        JSON string containing ToolResponse envelope with credited balance in data and quota metadata in meta.
    """
    pack = credits or settings.tool_credit_pack_size

    return await _execute_tool(
        "purchase_tool_credits",
        agent_id,
        lambda resolved: x402_services.purchase_tool_credits(
            payment_signature, payment_required, resolved, pack
        ),
    )


@mcp.tool(
    annotations={
        "title": "Create Stripe Checkout Session",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
        "agent_card": {
            "id": "x402-stripe-checkout",
            "name": "Stripe Fiat Checkout Broker",
            "role": "checkout",
            "domain": "commerce",
            "version": "0.1.0",
            "pricing": {"model": "free", "settlement_protocol": "stripe-fiat"},
            "execution_profile": {
                "read_only": False,
                "destructive": False,
                "idempotent": True,
                "open_world": True,
            },
            "input_modes": ["application/json", "text/plain"],
            "output_modes": ["application/json"],
            "tags": ["stripe", "fiat", "credit-card", "checkout", "commerce"],
            "examples": [
                "Generate a Stripe checkout link to pay with credit card",
                "Create a fiat checkout session for Pro tier subscription",
            ],
        },
    }
)
async def create_stripe_checkout(
    purpose: Annotated[
        str,
        Field(description="Purpose of checkout session: 'pro_tier_upgrade' or 'tool_credits'"),
    ] = "pro_tier_upgrade",
    credits: Annotated[
        int | None,
        Field(description="Number of credits if purchasing tool credits pack"),
    ] = None,
    agent_id: Annotated[
        str | None,
        Field(description="Optional calling agent identifier for quota tracking and telemetry isolation"),
    ] = None,
) -> str:
    """Create Stripe Checkout Session for pro tier or tool credits (fiat rail).

    Enables fiat credit card / debit payments as an alternative to crypto micropayments.

    Args:
        purpose: Either 'pro_tier_upgrade' or 'tool_credits'.
        credits: Optional number of credits if purchasing tool credits.
        agent_id: Optional calling agent identifier for quota tracking and isolation.

    Returns:
        JSON string containing ToolResponse envelope with hosted Stripe checkout URL in data and quota metadata in meta.
    """
    if purpose not in ("pro_tier_upgrade", "tool_credits"):
        raise ValueError("purpose must be pro_tier_upgrade or tool_credits")

    return await _execute_tool(
        "create_stripe_checkout",
        agent_id,
        lambda resolved: _sync_result(
            stripe_payments.create_checkout_session(
                resolved,
                purpose,  # type: ignore[arg-type]
                credits=credits,
            )
        ),
    )


@mcp.tool(
    annotations={
        "title": "Run Swarm Research Agency",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
        "agent_card": {
            "id": "x402-swarm-research",
            "name": "Autonomous Swarm Research Agency",
            "role": "investigator",
            "domain": "micropayments",
            "version": "0.1.0",
            "pricing": {"model": "free"},
            "execution_profile": {
                "read_only": False,
                "destructive": False,
                "idempotent": False,
                "open_world": True,
            },
            "input_modes": ["application/json", "text/plain"],
            "output_modes": ["application/json"],
            "tags": ["swarm", "agency", "research", "composite", "intelligence"],
            "examples": [
                "Run autonomous swarm research on Base L2 gas trends and list report",
                "Synthesize composite intelligence report across multiple x402 data feeds",
            ],
        },
    }
)
async def run_swarm_research(
    topic: Annotated[
        str,
        Field(description="Research topic or intelligence domain for the swarm to investigate and synthesize"),
    ],
    max_price_usdc: Annotated[
        float | None,
        Field(description="Optional maximum budget in USDC to spend on upstream paid data feeds"),
    ] = None,
    agent_id: Annotated[
        str | None,
        Field(description="Optional calling agent identifier for quota tracking and telemetry isolation"),
    ] = None,
    allow_paid_inputs: Annotated[
        bool | None,
        Field(description="Whether to permit buying upstream paid data feeds (default: False)"),
    ] = None,
) -> str:
    """Run the swarm Agency: compose a research product and list it for resale.

    Spends nothing by default — the report is synthesized from free inputs, so
    unsold inventory costs nothing. Pass allow_paid_inputs=True to buy upstream
    x402 services first (buy → compose → list), which books a cost basis before
    knowing whether the composite will sell.

    Args:
        topic: Research topic to synthesize.
        max_price_usdc: Optional maximum spend cap in USDC.
        agent_id: Optional calling agent identifier for quota tracking and isolation.
        allow_paid_inputs: Optional flag to permit upstream paid data purchases.

    Returns:
        JSON string containing ToolResponse envelope with composed research listing in data and quota metadata in meta.
    """
    if not settings.swarm_enabled:
        return json.dumps(
            {
                "error": "SWARM_ENABLED is false; the buyer role is off on this "
                "deployment.",
                "data": None,
                "meta": None,
            },
            indent=2,
        )
    return await _execute_tool(
        "run_swarm_research",
        agent_id,
        lambda resolved: swarm_orchestrator.run_swarm_research(
            topic, resolved, max_price_usdc, allow_paid_inputs
        ),
    )


@mcp.tool(
    annotations={
        "title": "Settle Composite Sale",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": False,
        "openWorldHint": True,
        "agent_card": {
            "id": "x402-settle-sale",
            "name": "Composite Product Sale Settler",
            "role": "settler",
            "domain": "commerce",
            "version": "0.1.0",
            "pricing": {"model": "paid_per_call"},
            "execution_profile": {
                "read_only": False,
                "destructive": True,
                "idempotent": False,
                "open_world": True,
            },
            "input_modes": ["application/json", "text/plain"],
            "output_modes": ["application/json"],
            "tags": ["settle", "swarm", "sale", "revenue", "commerce"],
            "examples": [
                "Settle inbound payment for research artifact #402",
                "Verify buyer payment signature and unlock composite product report",
            ],
        },
    }
)
async def settle_composite_sale(
    product_id: Annotated[
        str,
        Field(description="Canonical product identifier of the listed research artifact"),
    ],
    payment_signature: Annotated[
        str,
        Field(description="Buyer's signed PAYMENT-SIGNATURE authorizing product purchase"),
    ],
    payment_required: Annotated[
        str,
        Field(description="Original PAYMENT-REQUIRED challenge for this composite product"),
    ],
    agent_id: Annotated[
        str | None,
        Field(description="Optional calling agent identifier for quota tracking and telemetry isolation"),
    ] = None,
) -> str:
    """Verify + settle a buyer's x402 payment for a listed composite product and record the realized revenue (sell side).

    Args:
        product_id: Product ID of the listed research item.
        payment_signature: Buyer's PAYMENT-SIGNATURE header value.
        payment_required: PAYMENT-REQUIRED challenge header value.
        agent_id: Optional calling agent identifier for quota tracking and isolation.

    Returns:
        JSON string containing ToolResponse envelope with full product report in data and quota metadata in meta.
    """
    return await _execute_tool(
        "settle_composite_sale",
        agent_id,
        lambda resolved: swarm_orchestrator.settle_composite_sale(
            product_id, payment_signature, payment_required, resolved
        ),
    )


@mcp.tool(
    annotations={
        "title": "Swarm Revenue Intelligence Report",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
        "agent_card": {
            "id": "x402-swarm-revenue",
            "name": "Swarm Revenue Intelligence Reporter",
            "role": "telemetry",
            "domain": "commerce",
            "version": "0.1.0",
            "pricing": {"model": "free"},
            "execution_profile": {
                "read_only": True,
                "destructive": False,
                "idempotent": True,
                "open_world": False,
            },
            "input_modes": ["application/json", "text/plain"],
            "output_modes": ["application/json"],
            "tags": ["revenue", "swarm", "margins", "ltv-cac", "telemetry", "free"],
            "examples": [
                "Show total revenue and profit margins from swarm product sales",
                "Inspect CAC:LTV ratios and per-source profitability scores",
            ],
        },
    }
)
async def swarm_revenue_report(
    agent_id: Annotated[
        str | None,
        Field(description="Optional calling agent identifier for quota tracking and telemetry isolation"),
    ] = None,
) -> str:
    """Portfolio revenue intelligence for the swarm: spend, revenue, LTV:CAC, margins, per-source profit scores.

    Args:
        agent_id: Optional calling agent identifier for quota tracking and isolation.

    Returns:
        JSON string containing ToolResponse envelope with swarm financial metrics in data and quota metadata in meta.
    """
    from app.swarm import sovereign

    return await _execute_tool(
        "swarm_revenue_report",
        agent_id,
        lambda _: _sync_result(sovereign.build_revenue_report()),
    )


@mcp.tool(
    annotations={
        "title": "Base Network Settlement Pulse",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
        "agent_card": {
            "id": "base-network-pulse",
            "name": "Base Network Settlement Pulse Oracle",
            "role": "oracle",
            "domain": "blockchain-gas-optimization",
            "version": "0.1.0",
            "pricing": {"model": "free"},
            "execution_profile": {
                "read_only": True,
                "destructive": False,
                "idempotent": True,
                "open_world": True,
            },
            "input_modes": ["application/json", "text/plain"],
            "output_modes": ["application/json"],
            "tags": ["base", "gas", "fees", "pulse", "eip1559", "oracle", "free"],
            "examples": [
                "Is Base network congested right now?",
                "What is the recommended gas fee and USD cost for Base transactions?",
            ],
        },
    }
)
async def get_base_pulse(
    depth: Annotated[
        int | None,
        Field(description="Number of recent Base blocks to analyze for gas trend and utilization (default: 12)"),
    ] = None,
    agent_id: Annotated[
        str | None,
        Field(description="Optional calling agent identifier for quota tracking and telemetry isolation"),
    ] = None,
) -> str:
    """Live Base Network Pulse: synthesized settlement-conditions intelligence.

    Computes base fee in gwei, EIP-1559 projection, block utilization %,
    estimated USD settlement cost, and settle-now/hold verdict from real Base RPC
    data and ETH spot price.

    Args:
        depth: Number of recent blocks to inspect (default: 12).
        agent_id: Optional calling agent identifier for quota tracking and isolation.

    Returns:
        JSON string containing ToolResponse envelope with Base gas conditions in data and quota metadata in meta.
    """
    from app import pulse

    return await _execute_tool(
        "get_base_pulse", agent_id, lambda _: pulse.get_pulse(depth)
    )


@mcp.tool(
    annotations={
        "title": "Host OS Telemetry",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
        "agent_card": {
            "id": "host-os-telemetry",
            "name": "Host Operating System Telemetry",
            "role": "telemetry",
            "domain": "systems-ops",
            "version": "0.1.0",
            "pricing": {"model": "free"},
            "execution_profile": {
                "read_only": True,
                "destructive": False,
                "idempotent": True,
                "open_world": False,
            },
            "input_modes": ["application/json", "text/plain"],
            "output_modes": ["application/json"],
            "tags": ["os", "telemetry", "cpu", "memory", "health", "system", "free"],
            "examples": [
                "Check server CPU and memory load",
                "Get health verdict and top memory processes for host instance",
            ],
        },
    }
)
async def get_os_metrics(
    include_processes: Annotated[
        bool,
        Field(description="Whether to include top memory-consuming processes table in telemetry output (default: False)"),
    ] = False,
    agent_id: Annotated[
        str | None,
        Field(description="Optional calling agent identifier for quota tracking and telemetry isolation"),
    ] = None,
) -> str:
    """Host OS telemetry: CPU, memory, swap, disk, network, and process signals.

    Samples live telemetry from the machine hosting the server and returns
    an ok/warn/critical health verdict.

    Args:
        include_processes: Whether to include top processes by memory.
        agent_id: Optional calling agent identifier for quota tracking and isolation.

    Returns:
        JSON string containing ToolResponse envelope with OS telemetry in data and quota metadata in meta.
    """
    from app import os_monitor

    return await _execute_tool(
        "get_os_metrics",
        agent_id,
        lambda _: _sync_result(
            os_monitor.get_os_metrics(include_processes=include_processes)
        ),
    )


@mcp.tool(
    annotations={
        "title": "List US Compliance Network Cities",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
        "agent_card": {
            "id": "us-cities-catalog",
            "name": "US City Open-Data Compliance Catalog",
            "role": "indexer",
            "domain": "real-estate-compliance",
            "version": "0.1.0",
            "pricing": {"model": "free"},
            "execution_profile": {
                "read_only": True,
                "destructive": False,
                "idempotent": True,
                "open_world": False,
            },
            "input_modes": ["application/json", "text/plain"],
            "output_modes": ["application/json"],
            "tags": ["catalog", "cities", "compliance", "real-estate", "open-data", "free"],
            "examples": [
                "Which US cities are supported for rental compliance checks?",
                "List all 14 supported US jurisdictions and sample endpoints",
            ],
        },
    }
)
async def list_us_cities(
    agent_id: Annotated[
        str | None,
        Field(description="Optional calling agent identifier for quota tracking and telemetry isolation"),
    ] = None,
) -> str:
    """US City Open-Data Compliance Network catalog (free).

    Lists supported city codes (mn, sea, nyc, chi, den, sf, lax, bos, phi,
    orl, nola, moco, gain, kc), paid_url, sample_url, sample_address, price ($0.01),
    and the MCP golden path: sample → paid check. Same product as GET /us/cities.

    Args:
        agent_id: Optional calling agent identifier for quota tracking and isolation.

    Returns:
        JSON string containing ToolResponse envelope with list of 14 supported cities in data and quota metadata in meta.
    """
    from app.city_compliance import mcp_tools as city_mcp

    return await _execute_tool(
        "list_us_cities", agent_id, lambda _: city_mcp.list_us_cities()
    )


@mcp.tool(
    annotations={
        "title": "Get US City Compliance Sample",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
        "agent_card": {
            "id": "us-city-compliance-sample",
            "name": "US City Property Compliance Sample",
            "role": "oracle",
            "domain": "real-estate-compliance",
            "version": "0.1.0",
            "pricing": {"model": "free"},
            "execution_profile": {
                "read_only": True,
                "destructive": False,
                "idempotent": True,
                "open_world": True,
            },
            "input_modes": ["application/json", "text/plain"],
            "output_modes": ["application/json"],
            "tags": ["sample", "property", "compliance", "free", "real-estate"],
            "examples": [
                "Show me a sample property compliance report for Seattle (city=sea)",
                "Inspect sample rental license and violations data for Minneapolis (city=mn)",
            ],
        },
    }
)
async def get_us_city_property_sample(
    city_code: Annotated[
        str,
        Field(description="2-4 letter city jurisdiction code (e.g. 'mn', 'sea', 'chi', 'nyc', 'den', 'sf', 'lax')"),
    ],
    agent_id: Annotated[
        str | None,
        Field(description="Optional calling agent identifier for quota tracking and telemetry isolation"),
    ] = None,
) -> str:
    """Free fixed-address property compliance sample for one US city.

    Returns the identical JSON schema to the paid check without requiring payment.
    Use before paying to validate city code, schema shape, and compliance fields.

    Args:
        city_code: Jurisdiction code (e.g. mn, sea, nyc, chi).
        agent_id: Optional calling agent identifier for quota tracking and isolation.

    Returns:
        JSON string containing ToolResponse envelope with sample compliance report in data and quota metadata in meta.
    """
    from app.city_compliance import mcp_tools as city_mcp

    return await _execute_tool(
        "get_us_city_property_sample",
        agent_id,
        lambda _: city_mcp.get_us_city_property_sample(city_code),
    )


@mcp.tool(
    annotations={
        "title": "Check US City Property Compliance (Paid)",
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
            "input_modes": ["application/json", "text/plain"],
            "output_modes": ["application/json"],
            "tags": ["property", "compliance", "housing", "violations", "x402", "usdc", "base"],
            "examples": [
                "Check rental license and code violations for 1700 Penn Ave N in Minneapolis (city=mn)",
                "Is 123 Main St in Seattle licensed for rental operations? (city=sea)",
            ],
        },
    }
)
async def check_us_city_property(
    city_code: Annotated[
        str,
        Field(description="2-4 letter city jurisdiction code (e.g. 'mn', 'sea', 'chi', 'nyc', 'den', 'sf', 'lax')"),
    ],
    address: Annotated[
        str,
        Field(description="Street address to inspect for rental licenses, code violations, and condemnations (1-120 characters)"),
    ],
    max_price_usdc: Annotated[
        float | None,
        Field(description="Maximum price willing to pay in USDC (default: 0.01)"),
    ] = None,
    preferred_network: Annotated[
        str | None,
        Field(description="Optional CAIP-2 payment network identifier (e.g. 'eip155:8453')"),
    ] = None,
    agent_id: Annotated[
        str | None,
        Field(description="Optional calling agent identifier for quota tracking and telemetry isolation"),
    ] = None,
) -> str:
    """Paid US city property compliance check via x402.

    Screens rental licenses, building code violations, and condemnation status
    across 14 US municipal open-data registries ($0.01 USDC on Base).
    Settles USDC automatically when EVM_PRIVATE_KEY is configured; otherwise
    returns a 402 payment probe and how-to-pay instructions without charging.

    Args:
        city_code: Jurisdiction code (e.g. mn, sea, chi, nyc).
        address: Street address string (1-120 characters).
        max_price_usdc: Optional maximum price in USDC.
        preferred_network: Optional CAIP-2 payment network.
        agent_id: Optional calling agent identifier for quota tracking and isolation.

    Returns:
        JSON string containing ToolResponse envelope with verified compliance report in data and quota metadata in meta.
    """
    from app.city_compliance import mcp_tools as city_mcp

    return await _execute_tool(
        "check_us_city_property",
        agent_id,
        lambda _: city_mcp.check_us_city_property(
            city_code,
            address,
            max_price_usdc=max_price_usdc,
            preferred_network=preferred_network,
        ),
    )


@mcp.tool(
    annotations={
        "title": "Get Agent ID Card & Capabilities",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
        "agent_card": {
            "id": "x402-agent-card",
            "name": "A2A Agent Card & Capabilities Inspector",
            "role": "identity",
            "domain": "agent-identity",
            "version": "0.1.0",
            "pricing": {"model": "free"},
            "execution_profile": {
                "read_only": True,
                "destructive": False,
                "idempotent": True,
                "open_world": False,
            },
            "input_modes": ["application/json", "text/plain"],
            "output_modes": ["application/json"],
            "tags": ["agent-card", "identity", "a2a", "mcp", "discovery", "capabilities", "free"],
            "examples": [
                "Get the full agent identity card and capability manifest for x402-mcp",
                "Inspect agent payment requirements, supported chains, and tool skills",
            ],
        },
    }
)
async def get_agent_card(
    target_id: Annotated[
        str | None,
        Field(description="Optional specific skill ID, tool name, or agent ID to inspect (defaults to full server agent card)"),
    ] = None,
    agent_id: Annotated[
        str | None,
        Field(description="Optional calling agent identifier for quota tracking and telemetry isolation"),
    ] = None,
) -> str:
    """Retrieve the full A2A Protocol v1.0 Agent ID Card and tool capability registry.

    Returns comprehensive agent metadata including identity, capabilities,
    supported payment networks (Base mainnet EIP-3009), pricing terms,
    and skill cards for all 20 MCP tools.

    Args:
        target_id: Optional specific skill ID, tool name, or agent ID to filter.
        agent_id: Optional calling agent identifier for quota tracking and isolation.

    Returns:
        JSON string containing ToolResponse envelope with full Agent ID Card in data and quota metadata in meta.
    """
    from app.agent_surface import agent_card, mcp_server_card

    def _build_card(resolved_agent_id: str) -> dict[str, Any]:
        card = agent_card()
        server_meta = mcp_server_card()
        if target_id:
            matching_skills = [
                s
                for s in card.get("skills", [])
                if s.get("id") == target_id
                or target_id in s.get("tags", [])
                or target_id == s.get("name")
            ]
            if matching_skills:
                return {
                    "agent_id": resolved_agent_id,
                    "target_id": target_id,
                    "skills": matching_skills,
                    "provider": card.get("provider"),
                    "securitySchemes": card.get("securitySchemes"),
                    "serverInfo": server_meta.get("serverInfo"),
                }
        return {
            "agent_id": resolved_agent_id,
            "card": card,
            "server_card": server_meta,
            "tools_count": len(card.get("skills", [])),
        }

    return await _execute_tool(
        "get_agent_card",
        agent_id,
        lambda resolved: _sync_result(_build_card(resolved)),
    )


# ============================================================================
# 2. MCP Prompts
# ============================================================================


@mcp.prompt()
def onboarding_flow(
    agent_name: Annotated[
        str,
        Field(description="Identifier or name of the onboarding AI agent"),
    ] = "agent",
) -> str:
    """Guided onboarding workflow for new AI agents connecting to x402-mcp.

    Args:
        agent_name: Identifier or name of the onboarding AI agent.

    Returns:
        Structured instructions for onboarding, discovering tools, probing 402 endpoints, and quota management.
    """
    return f"""# x402-mcp Agent Onboarding Guide

Welcome, {agent_name}! You are connected to the `x402-mcp` autonomous commerce server.

## Recommended Golden Path:
1. **Identity & Discovery**:
   - Call `get_agent_card()` to inspect server capabilities, payment terms, and available tools.
   - Resource `x402://agent-card` provides the complete A2A Protocol v1.0 Agent Card.
2. **Explore US City Compliance**:
   - Call `list_us_cities()` to see 14 supported municipal jurisdictions.
   - Call `get_us_city_property_sample(city_code="mn")` to test data schema for free before paying.
   - When ready, call `check_us_city_property(city_code="mn", address="1700 Penn Ave N")` ($0.01 USDC on Base).
3. **Check Network Settlement Conditions**:
   - Call `get_base_pulse()` to check Base EIP-1559 base fee, congestion, and settle-now vs hold verdict.
4. **Quota & Subscription**:
   - Free tier includes 500 calls/month and 10 calls/minute.
   - Every tool returns a `meta` envelope with remaining quota.
   - Upgrade to Pro (50k calls/mo) with `get_pro_upgrade_requirements()` or Stripe checkout via `create_stripe_checkout()`.
"""


@mcp.prompt()
def x402_tool_selector(
    goal: Annotated[
        str,
        Field(description="Goal or task to accomplish (e.g. 'compliance', 'gas_check', 'pay_api', 'monetize', 'telemetry')"),
    ] = "compliance",
    domain: Annotated[
        str | None,
        Field(description="Optional domain filter (e.g. 'real-estate', 'blockchain', 'commerce', 'ops')"),
    ] = None,
) -> str:
    """Decision tree and tool selection guide for AI agents and LLM routers.

    Args:
        goal: The operational goal or task to accomplish.
        domain: Optional domain filter.

    Returns:
        Structured tool recommendation with required parameters and execution safety profiles.
    """
    return f"""# x402 Tool Selector Guide

Target Goal: {goal} (Domain: {domain or 'all'})

## Decision Matrix:
- **Real Estate / Rental Compliance**:
  - Catalog: `list_us_cities` (free, read-only)
  - Testing: `get_us_city_property_sample` (free fixed address sample)
  - Paid Verification: `check_us_city_property` ($0.01 USDC on Base)
- **Base Blockchain & Gas Optimization**:
  - Network Pulse: `get_base_pulse` (live RPC fees, congestion, verdict)
  - Supported Chains: `get_supported_networks`
- **Buyer & Payments**:
  - Probe URL: `get_payment_requirements` (inspect 402 challenge)
  - Pay & Fetch: `pay_and_fetch` (sign EIP-3009 & fetch data)
  - Discover APIs: `discover_services` (search x402 Bazaar)
- **Seller & Monetization**:
  - Requirements Builder: `build_seller_requirements` (build PAYMENT-REQUIRED challenge)
  - Verify Payment: `verify_payment_payload` (facilitator signature check)
- **Swarm Research Agency**:
  - Research Synthesis: `run_swarm_research`
  - Settle Sale: `settle_composite_sale`
  - Revenue Reporting: `swarm_revenue_report`
- **Host Telemetry**:
  - Telemetry: `get_os_metrics` (CPU, memory, disk, network, health)
- **Agent Identity**:
  - Agent Card: `get_agent_card`
"""


@mcp.prompt()
def generate_quote(
    service_name: Annotated[
        str,
        Field(description="Name or title of the service to monetize"),
    ] = "My Custom Data API",
    price_usdc: Annotated[
        str,
        Field(description="Price in USDC per call (e.g. '$0.05')"),
    ] = "$0.05",
    network: Annotated[
        str,
        Field(description="CAIP-2 network identifier (default: eip155:8453 for Base mainnet)"),
    ] = "eip155:8453",
    pay_to: Annotated[
        str | None,
        Field(description="Recipient EVM wallet address (0x...)"),
    ] = None,
) -> str:
    """Generate x402 payment requirements and pricing quote for monetizing an API endpoint.

    Args:
        service_name: Name of the service to monetize.
        price_usdc: Price per call in USDC.
        network: CAIP-2 network identifier.
        pay_to: Recipient wallet address.

    Returns:
        Step-by-step instructions and code snippet to build seller PAYMENT-REQUIRED challenge.
    """
    pay_line = f"- `pay_to`: '{pay_to}'" if pay_to else "- `pay_to`: (uses configured X402_PAY_TO_ADDRESS)"
    return f"""# Generate x402 Seller Quote

To monetize '{service_name}' at {price_usdc} on {network}:

1. Call the `build_seller_requirements` tool with:
   - `price`: "{price_usdc}"
   - `network`: "{network}"
   - `description`: "{service_name}"
   {pay_line}
   - `discoverable`: True

2. Embed the returned `payment_required` base64 header in HTTP 402 responses.
3. When buyers submit `PAYMENT-SIGNATURE`, verify via `verify_payment_payload`.
"""


@mcp.prompt()
def troubleshoot_payment(
    error_code: Annotated[
        str,
        Field(description="Error code or symptom (e.g. 'payment_invalid', 'rate_limit_exceeded', '502_facilitator', 'missing_wallet')"),
    ] = "payment_invalid",
    details: Annotated[
        str | None,
        Field(description="Optional verbatim error message or context"),
    ] = None,
) -> str:
    """Troubleshooting and error-recovery protocol for x402 payment and quota issues.

    Args:
        error_code: Error code or symptom.
        details: Optional additional error details.

    Returns:
        Diagnostic analysis and concrete recovery steps for the specified failure.
    """
    return f"""# Troubleshooting x402 Payment & Quota Errors

Reported Error: `{error_code}`
Details: {details or 'None provided'}

## Remediation Playbook:
- **`rate_limit_exceeded` / `quota_exceeded`**:
  - The agent has exceeded free tier limits (500 calls/mo, 10/min).
  - Remedy: Call `get_pro_upgrade_requirements` or `create_stripe_checkout` to upgrade, or purchase `purchase_tool_credits`.
- **`payment_invalid` / `signature_expired`**:
  - Signatures expire after 300 seconds or when bound to a stale challenge.
  - Remedy: Re-probe the URL with `get_payment_requirements` to get a fresh `PAYMENT-REQUIRED` header, sign with `EVM_PRIVATE_KEY`, and retry.
- **`502_facilitator` / CDP timeout**:
  - Transient facilitator failure. No funds moved.
  - Remedy: Safe to retry the exact same payment request after 2-3 seconds.
- **`EVM_PRIVATE_KEY missing`**:
  - Buyer execution requires a private key for on-chain signing.
  - Remedy: Configure `EVM_PRIVATE_KEY` in environment or use seller-only / probe tools.
"""


# ============================================================================
# 3. MCP Resources
# ============================================================================


@mcp.resource("x402://agent-card")
def get_agent_card_resource() -> str:
    """Full A2A Protocol v1.0 Agent ID Card and capability descriptor."""
    from app.agent_surface import agent_card

    return json.dumps(agent_card(), indent=2)


@mcp.resource("x402://server-card")
def get_server_card_resource() -> str:
    """Remote MCP Server Card for Smithery.ai, Glama.ai, and client indexing."""
    from app.agent_surface import mcp_server_card

    return json.dumps(mcp_server_card(), indent=2)


@mcp.resource("x402://tools-manifest")
def get_tools_manifest_resource() -> str:
    """Canonical MCP well-known manifest with tool specifications, quotas, and endpoints."""
    from app.manifest import build_mcp_manifest

    return json.dumps(build_mcp_manifest(), indent=2)


@mcp.resource("x402://pricing-table")
def get_pricing_table_resource() -> str:
    """Machine-readable pricing table for x402 micropayments, subscriptions, and credits."""
    from app.agent_surface import paid_resources
    from app.payment_rails import build_payment_rails

    return json.dumps(
        {
            "free_tier": {
                "monthly_quota": settings.free_tier_monthly_quota,
                "rate_limit_per_minute": settings.free_tier_rate_limit_per_min,
                "price": "$0.00",
            },
            "pro_tier": {
                "monthly_quota": settings.pro_tier_monthly_quota,
                "rate_limit_per_minute": settings.pro_tier_rate_limit_per_min,
                "price_usd": "$29.00",
                "price_x402": settings.pro_tier_price,
            },
            "tool_credits": {
                "pack_size": settings.tool_credit_pack_size,
                "price_x402": settings.tool_credit_pack_price,
            },
            "paid_endpoints": paid_resources(),
            "payment_rails": build_payment_rails(),
        },
        indent=2,
    )