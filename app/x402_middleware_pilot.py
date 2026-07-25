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
section, so the pattern is available and tested for whatever the *next*
paid endpoint turns out to need — without touching any current route.

`GET /pilot/ping` is that endpoint: nominally priced, not cataloged, not a
product. It exists to be curled and settled against, not sold.
"""

from __future__ import annotations

from fastapi import APIRouter
from starlette.applications import Starlette

from app.config import settings

router = APIRouter()


@router.get("/pilot/ping")
async def pilot_ping() -> dict:
    """The protected handler. By the time this runs, the SDK middleware has
    already verified and settled payment — no challenge/verify/settle code
    here at all, which is the actual point of the pilot."""
    return {"ok": True, "pattern": "x402 SDK FastAPI middleware pilot"}


def register(app: Starlette) -> None:
    """Wire the pilot middleware onto `app`, additively.

    Only requests to `GET /pilot/ping` are gated — every other route takes
    one cheap regex-match-and-pass-through per request
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

    from app.x402_services import _resource_server

    server = _resource_server(settings.x402_default_network)

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
        )
    }

    app.include_router(router)
    app.add_middleware(PaymentMiddlewareASGI, routes=routes, server=server)
