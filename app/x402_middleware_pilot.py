"""Standalone pilot of the x402 SDK's own FastAPI payment middleware.

Every other paid route in this repo (Pulse, /base/tx-decision,
/mn/property-check) hand-rolls its own challenge/verify/settle path —
mostly because each needed something the generic middleware doesn't give
you for free (challenge caching through a flaky facilitator, demand
instrumentation that excludes self-traffic, a payer address captured
*before* settlement for the ledger). Rewriting those was evaluated and
declined: for this codebase, migrating trades ~40 lines of tested, working
code for a similar amount of hook glue, plus a real regression (payment
gated before request validation, since the SDK gates at the ASGI layer
before the route handler runs).

This module is the other half of that decision: prove the SDK's own
`x402.http.middleware.fastapi.PaymentMiddlewareASGI` actually works end to
end against this server's real facilitator config, as its own isolated
section, so the pattern is available for whatever paid endpoint turns out
to need it — without touching any current route.

`GET /pilot/ping` is the protocol proof: nominally priced, not cataloged,
not a product. `GET /base/finality-check` (app/finality_check.py) is the
first real one — the first paid product in this repo gated by the generic
middleware instead of a hand-rolled challenge/verify/settle path.

Known, accepted gap versus the hand-rolled products: there is no
post-settlement hook in the SDK, so unlike Pulse/tx-decision/mn-property-
check this route does NOT write a row to `ledger_writer.record_revenue` —
doing that from the pre-settlement payment payload would risk recording
revenue for a payment that later fails to settle, which is exactly the kind
of inflated-revenue bug the 2026-07-25 payer-classification work was
written to prevent, not reintroduce. Real settlement still happens
correctly (money still moves to X402_PAY_TO_ADDRESS via the same
facilitator); it just isn't mirrored into this repo's ledger or dashboard
yet. Base mainnet / the facilitator's own records are the source of truth
for this route's revenue until the SDK grows a settlement hook.
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from starlette.applications import Starlette

from app.config import settings

router = APIRouter()


@router.get("/pilot/ping")
async def pilot_ping() -> dict:
    """The protected handler. By the time this runs, the SDK middleware has
    already verified and settled payment — no challenge/verify/settle code
    here at all, which is the actual point of the pilot."""
    return {"ok": True, "pattern": "x402 SDK FastAPI middleware pilot"}


@router.get("/base/finality-check")
async def base_finality_check(
    tx: str = Query(
        ...,
        pattern=r"^0x[0-9a-fA-F]{64}$",
        description="Base mainnet transaction hash to check",
    ),
) -> dict:
    """The protected handler for the real product. FastAPI's own query
    validation runs here, inside `call_next` — a malformed `tx` produces a
    422 the middleware sees as a handler failure and does not settle for
    (see `PaymentMiddlewareASGI`'s `response.status_code >= 400` check), so
    the "validate before charge" property is preserved despite payment
    gating happening at the ASGI layer."""
    from app.finality_check import check_finality

    return await check_finality(tx)


def register(app: Starlette) -> None:
    """Wire the pilot middleware onto `app`, additively.

    Only requests to the two routes below are gated — every other route
    takes one cheap regex-match-and-pass-through per request
    (`x402HTTPResourceServer.requires_payment`) and is otherwise untouched.
    A no-op (with a log line) if X402_PAY_TO_ADDRESS isn't configured, same
    posture as the seller-only public deployment for every other product.
    """
    if not settings.x402_pay_to_address:
        import logging

        logging.getLogger(__name__).info(
            "x402_middleware_pilot: X402_PAY_TO_ADDRESS unset, not registering"
        )
        return

    from x402.http.middleware import PaymentMiddlewareASGI
    from x402.http.types import PaymentOption, RouteConfig

    from app import finality_check
    from app.x402_services import _build_discovery_extension, _resource_server

    server = _resource_server(settings.x402_default_network)

    finality_extensions = None
    if settings.bazaar_discoverable:
        finality_extensions = _build_discovery_extension(
            "GET",
            finality_check.DISCOVERY_INPUT_EXAMPLE,
            finality_check.DISCOVERY_OUTPUT_EXAMPLE,
        )

    tags = [t.strip()[:32] for t in settings.bazaar_service_tags.split(",") if t.strip()][:5]

    routes = {
        "GET /pilot/ping": RouteConfig(
            accepts=PaymentOption(
                scheme="exact",
                pay_to=settings.x402_pay_to_address,
                price=settings.middleware_pilot_price,
                network=settings.x402_default_network,
            ),
            description=(
                "x402 SDK middleware pilot endpoint — not a catalog product, "
                "exists to prove the generic FastAPI payment middleware "
                "against this server's real facilitator config."
            ),
            mime_type="application/json",
        ),
        "GET /base/finality-check": RouteConfig(
            accepts=PaymentOption(
                scheme="exact",
                pay_to=settings.x402_pay_to_address,
                price=settings.finality_check_price,
                network=settings.x402_default_network,
            ),
            resource=finality_check.resource_url(),
            description=finality_check.RESOURCE_DESCRIPTION,
            mime_type="application/json",
            service_name=settings.bazaar_service_name.strip()[:32] or None,
            tags=tags or None,
            extensions=finality_extensions,
        ),
    }

    app.include_router(router)
    app.add_middleware(PaymentMiddlewareASGI, routes=routes, server=server)
