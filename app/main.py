"""FastAPI application: HTTP transport, manifest, health, MCP SSE mount."""

from __future__ import annotations

import ipaddress
import time
from collections import defaultdict
from typing import Literal
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from app.commerce import quota_store
from app.config import settings
from app.ledger_io import read_ledger_rows
from app.manifest import build_mcp_manifest
from app.mcp_server import mcp
from app.ops_events import event_stream, format_sse

app = FastAPI(
    title="x402 Micropayments MCP",
    description="MCP server for x402 HTTP micropayments with agent-commerce overlay",
    version="0.1.0",
)

# TODO auth before public exposure — dashboard CORS for local Vite dev only.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


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


# Mount MCP Streamable HTTP / SSE transport when available.
try:
    mcp_app = mcp.streamable_http_app()
    app.mount("/mcp", mcp_app)
except AttributeError:
    try:
        app.mount("/mcp", mcp.sse_app())
    except AttributeError:
        pass