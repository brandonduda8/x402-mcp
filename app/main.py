"""FastAPI application: HTTP transport, manifest, health, MCP SSE mount."""

from __future__ import annotations

import ipaddress
import logging
import time
from collections import defaultdict
from typing import Literal
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse

from app.commerce import quota_store
from app.config import settings
from app.dashboard import DASHBOARD_HTML
from app.ledger_io import read_ledger_rows
from app.manifest import build_mcp_manifest
from app.mcp_server import mcp
from app.ops_events import event_stream, format_sse

log = logging.getLogger(__name__)

app = FastAPI(
    title="x402 Micropayments MCP",
    description="MCP server for x402 HTTP micropayments with agent-commerce overlay",
    version="0.1.0",
)

def _cors_origins() -> list[str]:
    """Local Vite dev origins, plus any EXACT origins the operator opted into.

    Deliberately no origin regex: a pattern like https://.*.trycloudflare.com
    matches a tunnel anyone can register for free, and every endpoint here is
    unauthenticated, so that is equivalent to allowing all origins to read the
    ledger and wallet. Set CORS_EXTRA_ORIGINS to the one tunnel you are using.
    """
    origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ]
    extra = [o.strip().rstrip("/") for o in settings.cors_extra_origins.split(",")]
    origins.extend(o for o in extra if o)
    return origins


# TODO auth before public exposure — dashboard CORS for local Vite dev only.
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["PAYMENT-REQUIRED", "PAYMENT-RESPONSE", "PAYMENT-SIGNATURE"],
)

_LOOPBACK_HOSTS = ("127.0.0.1", "localhost", "0.0.0.0", "[::1]", "::1")


def _public_base_from_request(request: Request) -> str:
    """Public origin for seller resource URLs.

    The result is baked into the `resource` field of the signed 402 challenge
    and advertised to discovery catalogs, which index it once — so a spoofed
    Host header would otherwise let a caller choose what this server advertises.
    Forwarded headers are therefore only honoured when TRUST_FORWARDED_HOST is
    set, i.e. when the operator knows a proxy they control is in front.
    """
    if not settings.trust_forwarded_host:
        return settings.public_base_url.rstrip("/")

    xf_proto = request.headers.get("x-forwarded-proto")
    xf_host = request.headers.get("x-forwarded-host") or request.headers.get("host")
    if not xf_host:
        return settings.public_base_url.rstrip("/")

    host = xf_host.split(",")[0].strip()
    if host.startswith("["):  # bracketed IPv6, optionally with :port
        bare = host[: host.index("]") + 1] if "]" in host else host
    else:
        bare = host.rsplit(":", 1)[0]
    if bare.lower() in _LOOPBACK_HOSTS or host.lower() in _LOOPBACK_HOSTS:
        return settings.public_base_url.rstrip("/")

    scheme = (xf_proto or "https").split(",")[0].strip()
    return f"{scheme}://{host}".rstrip("/")


@app.exception_handler(Exception)
async def generic_handler(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_error",
            "message": str(exc),
            "upgrade_url": settings.upgrade_url,
        },
    )


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    return RedirectResponse(url="/dashboard", status_code=307)


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard() -> HTMLResponse:
    """Operator terminal: live health, quota meters, tool matrix, revenue paths."""
    return HTMLResponse(DASHBOARD_HTML)


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "service": "x402-micropayments-mcp",
        "x402_facilitator": settings.x402_facilitator_url,
        "wallet_configured": bool(settings.evm_private_key),
    }


@app.get("/.well-known/mcp")
async def well_known_mcp() -> dict:
    return build_mcp_manifest()


@app.get("/stats")
async def stats_snapshot() -> dict:
    """Mission-control quota snapshot (read-only)."""
    return quota_store.snapshot()


@app.get("/events")
async def tool_events() -> StreamingResponse:
    """SSE stream of MCP tool invocations."""

    async def generate():
        async for event in event_stream():
            yield format_sse(event)

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/ledger/{name}")
async def ledger_rows(name: Literal["spend", "revenue"]) -> list[dict]:
    """Agent-ops spend/revenue ledger (newest first, max 1000)."""
    return read_ledger_rows(name)


@app.get("/quota/{agent_id}")
async def quota_status(agent_id: str) -> dict:
    """Debug endpoint: inspect quota without consuming a call."""
    snapshot = quota_store.peek(agent_id)
    meta = quota_store.build_meta(snapshot)
    return {"meta": meta.model_dump()}


@app.get("/upgrade")
async def upgrade_info() -> dict:
    """Pro tier and per-use credits upgrade instructions (x402 payment paths)."""
    manifest = build_mcp_manifest()
    return {
        "upgrade_url": settings.upgrade_url,
        "tiers": manifest["tiers"],
        "tool_credits": {
            "pack_size": settings.tool_credit_pack_size,
            "pack_price": settings.tool_credit_pack_price,
            "payment_tool": "get_tool_credits_requirements",
            "purchase_tool": "purchase_tool_credits",
        },
        "payment_flow": [
            "1. Call get_pro_upgrade_requirements or get_tool_credits_requirements (MCP)",
            "2. Pay via x402 wallet using returned requirements",
            "3. Call activate_pro_tier or purchase_tool_credits with PAYMENT-SIGNATURE",
        ],
        "mcp_tools": {
            "pro_upgrade": ["get_pro_upgrade_requirements", "activate_pro_tier"],
            "tool_credits": ["get_tool_credits_requirements", "purchase_tool_credits"],
        },
        "manifest": "/.well-known/mcp",
    }


# ---------- /doctor ----------

@app.get("/doctor")
async def doctor_endpoint() -> dict:
    """Machine-readable health checks powering the setup wizard."""
    from app.doctor import run_checks

    report = await run_checks()
    return report.to_dict()


# ---------- /probe (SSRF-guarded, rate-limited 10/min per IP) ----------

_probe_windows: dict[str, list[float]] = defaultdict(list)


def _is_private_or_linklocal(hostname: str) -> bool:
    """Block private, loopback, and link-local IP ranges."""
    try:
        addr = ipaddress.ip_address(hostname)
        return addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved
    except ValueError:
        # Not a raw IP — check well-known private hostnames
        lower = hostname.lower()
        return lower in ("localhost", "0.0.0.0") or lower.endswith(".local")


def _probe_rate_check(client_ip: str) -> bool:
    """Returns True if under limit (10/min)."""
    now = time.time()
    window = _probe_windows[client_ip]
    cutoff = now - 60.0
    _probe_windows[client_ip] = [t for t in window if t > cutoff]
    if len(_probe_windows[client_ip]) >= 10:
        return False
    _probe_windows[client_ip].append(now)
    return True


@app.get("/probe")
async def probe_url(
    request: Request,
    url: str = Query(..., description="URL to probe for x402 payment requirements"),
    method: str = Query("GET", description="HTTP method"),
) -> dict:
    """Keyless 402 probe proxy — SSRF-guarded, 10/min per IP."""
    client_ip = request.client.host if request.client else "unknown"
    if not _probe_rate_check(client_ip):
        raise HTTPException(status_code=429, detail="Probe rate limit exceeded (10/min)")

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="Only http/https URLs allowed")

    hostname = parsed.hostname or ""
    if _is_private_or_linklocal(hostname):
        raise HTTPException(status_code=400, detail="Private/link-local addresses blocked")

    import httpx

    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.request(method.upper(), url)
            await resp.aread()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Upstream error: {exc}")

    result: dict = {
        "url": url,
        "method": method.upper(),
        "status_code": resp.status_code,
        "payment_required": resp.status_code == 402,
    }

    if resp.status_code == 402:
        pr_header = resp.headers.get("PAYMENT-REQUIRED")
        result["payment_required_header"] = pr_header

        # Try to decode the payment requirements
        decoded = None
        if pr_header:
            import base64
            import json

            try:
                decoded = json.loads(base64.b64decode(pr_header).decode("utf-8"))
            except Exception:
                decoded = None

        # Also try body
        body_data = None
        try:
            body_data = resp.json()
        except Exception:
            pass

        result["payment_required_decoded"] = decoded
        result["payment_required_body"] = body_data

    return result


# ---------- /wallet (read-only, no key material) ----------

@app.get("/wallet")
async def wallet_info() -> dict:
    """Public wallet addresses and RPC balance reads. No private key material."""
    from app.doctor import get_wallet_info

    return await get_wallet_info()


# ---------- POST /seller/requirements (gated) ----------

@app.post("/seller/requirements")
async def seller_requirements_endpoint(body: dict) -> dict:
    """Keyless wrapper on build_seller_requirements. Gated behind DASHBOARD_ACTIONS=true."""
    if not settings.dashboard_actions:
        raise HTTPException(
            status_code=403,
            detail="Dashboard actions disabled. Set DASHBOARD_ACTIONS=true to enable.",
        )

    from app.models import BuildSellerRequirementsInput
    from app import x402_services

    params = BuildSellerRequirementsInput(
        network=body.get("network", "eip155:84532"),
        pay_to=body.get("pay_to"),
        price=body.get("price", "$0.01"),
        scheme=body.get("scheme", "exact"),
        description=body.get("description", "Paid API access"),
    )
    return x402_services.build_seller_requirements(params)


# ---------- Step 2 seller demo: paid resource at /demo/paid ----------

@app.get("/demo/paid")
async def demo_paid_resource(request: Request) -> JSONResponse:
    """Seller demo — returns 402 without payment; paid body after verify+settle.

    Self-test (vault pays itself on Base Sepolia):
      pay_and_fetch url=http://127.0.0.1:8402/demo/paid preferred_network=eip155:84532
    """
    from x402.http.constants import (
        PAYMENT_REQUIRED_HEADER,
        PAYMENT_RESPONSE_HEADER,
        PAYMENT_SIGNATURE_HEADER,
        X_PAYMENT_HEADER,
    )
    from x402.http.utils import encode_payment_response_header

    from app import challenge_cache, x402_services
    from app.ledger_io import append_ledger_row
    from app.ops_events import emit_tool_event

    resource_url = f"{_public_base_from_request(request)}/demo/paid"
    description = "x402 seller demo — paid JSON secret on Base Sepolia"

    # Every input baked into the header goes into the fingerprint. Miss one and
    # a changed challenge deploys cleanly while buyers keep seeing the old one.
    cache_key = challenge_cache.fingerprint(
        resource_url=resource_url,
        description=description,
        price=settings.x402_default_price,
        network=settings.x402_default_network,
        pay_to=settings.x402_pay_to_address,
        scheme="exact",
        include_bazaar=True,
    )

    try:
        built = await challenge_cache.get_or_build(
            cache_key,
            lambda: x402_services.build_payment_required_for_resource(
                resource_url=resource_url,
                description=description,
                price=settings.x402_default_price,
                network=settings.x402_default_network,
            ),
            ttl_seconds=settings.challenge_cache_ttl_seconds,
        )
    except Exception:
        # Cold start with the facilitator down. A retryable 503 is honest;
        # a 500 gets this endpoint recorded as non-compliant by every indexer.
        log.warning("demo/paid: cannot build challenge", exc_info=True)
        return JSONResponse(
            status_code=503,
            headers={"Retry-After": "30"},
            content={"error": "challenge_unavailable", "detail": "retry shortly"},
        )

    payment_sig = (
        request.headers.get(PAYMENT_SIGNATURE_HEADER)
        or request.headers.get(X_PAYMENT_HEADER)
        or request.headers.get("payment-signature")
    )

    if not payment_sig:
        # 402 Payment Required — client should pay and retry with PAYMENT-SIGNATURE
        return JSONResponse(
            status_code=402,
            content={
                **built["payment_required"],
                "note": "Pay with x402 exact scheme, then retry with PAYMENT-SIGNATURE header.",
                "seller_pay_to": built["pay_to"],
                "price": built["price"],
                "network": built["network"],
            },
            headers={
                PAYMENT_REQUIRED_HEADER: built["payment_required_header"],
                "Access-Control-Expose-Headers": PAYMENT_REQUIRED_HEADER,
            },
        )

    # Buyer presented payment — verify + settle (revenue path)
    result = await x402_services.verify_and_settle_from_headers(
        payment_signature=payment_sig,
        payment_required_header=built["payment_required_header"],
    )

    if not result.get("is_valid"):
        return JSONResponse(
            status_code=402,
            content={
                **built["payment_required"],
                "error": "Payment verification failed",
                "invalid_reason": result.get("invalid_reason"),
            },
            headers={PAYMENT_REQUIRED_HEADER: built["payment_required_header"]},
        )

    settlement = result.get("settlement") or {}
    paid_ok = result.get("payment_settled") is True

    if paid_ok:
        append_ledger_row(
            "revenue",
            {
                "kind": "seller_demo",
                "resource": resource_url,
                "pay_to": built["pay_to"],
                "network": built["network"],
                "price": built["price"],
                "tx": settlement.get("transaction"),
                "payer": settlement.get("payer"),
                "settlement": settlement,
            },
        )
        emit_tool_event(
            "demo_paid",
            "seller",
            {"tx": settlement.get("transaction"), "price": built["price"]},
        )

    headers: dict[str, str] = {}
    if paid_ok and settlement:
        try:
            from x402.schemas import SettleResponse

            settle_model = SettleResponse.model_validate(settlement)
            headers[PAYMENT_RESPONSE_HEADER] = encode_payment_response_header(settle_model)
            headers["Access-Control-Expose-Headers"] = PAYMENT_RESPONSE_HEADER
        except Exception:
            pass

    return JSONResponse(
        status_code=200 if paid_ok else 402,
        content={
            "ok": paid_ok,
            "message": "Payment settled — seller demo payload unlocked"
            if paid_ok
            else "Verified but settlement failed",
            "secret": "x402-seller-demo-ok" if paid_ok else None,
            "seller_pay_to": built["pay_to"],
            "price": built["price"],
            "network": built["network"],
            "payment_settled": paid_ok,
            "settlement": settlement,
            "settlement_error": result.get("settlement_error"),
        },
        headers=headers,
    )


@app.get("/demo/paid/info")
async def demo_paid_info(request: Request) -> dict:
    """Free metadata for the seller demo resource (no payment)."""
    base = _public_base_from_request(request)
    return {
        "resource": f"{base}/demo/paid",
        "price": settings.x402_default_price,
        "network": settings.x402_default_network,
        "pay_to": settings.x402_pay_to_address,
        "public_base_url_config": settings.public_base_url,
        "flow": [
            "1. GET /demo/paid → 402 + PAYMENT-REQUIRED",
            "2. Buyer pays (pay_and_fetch or wallet)",
            "3. GET /demo/paid with PAYMENT-SIGNATURE → 200 + secret + settle",
        ],
        "self_test": {
            "url": f"{base}/demo/paid",
            "tool": "pay_and_fetch",
            "preferred_network": settings.x402_default_network,
        },
        "bazaar": {
            "merchant_discovery": (
                "https://api.cdp.coinbase.com/platform/v2/x402/discovery/merchant"
                f"?payTo={settings.x402_pay_to_address or ''}"
            ),
            "note": "CDP indexes after settle through CDP facilitator; catalog lag ~10m",
        },
    }


@app.get("/ops/status")
async def ops_status() -> dict:
    """Compact stack status for restart scripts and dashboards."""
    from app.doctor import run_checks

    report = await run_checks()
    return {
        "service": "x402-micropayments-mcp",
        "public_base_url": settings.public_base_url,
        "pay_to": settings.x402_pay_to_address,
        "network": settings.x402_default_network,
        "facilitator": settings.x402_facilitator_url,
        "wallet_configured": bool(settings.evm_private_key),
        "doctor_ok": report.all_passed,
        "checks": [
            {
                "id": c.id,
                "passed": c.passed,
                "detail": c.detail,
            }
            for c in report.checks
        ],
    }


# Mount MCP Streamable HTTP / SSE transport when available.
try:
    mcp_app = mcp.streamable_http_app()
    app.mount("/mcp", mcp_app)
except AttributeError:
    try:
        app.mount("/mcp", mcp.sse_app())
    except AttributeError:
        pass