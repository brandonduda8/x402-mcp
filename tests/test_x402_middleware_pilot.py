"""Pilot of the x402 SDK's own FastAPI payment middleware (app/x402_middleware_pilot.py).

Purely additive — these tests pin that it works end to end AND that it does
not disturb any existing route.
"""

from __future__ import annotations

import base64
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import x402_middleware_pilot
from app.config import settings
from app.main import app

client = TestClient(app)


def test_unpaid_ping_returns_402_with_payment_required_header() -> None:
    response = client.get("/pilot/ping")
    assert response.status_code == 402
    assert "payment-required" in response.headers


def test_payment_required_header_matches_configured_price_and_pay_to() -> None:
    response = client.get("/pilot/ping")
    decoded = json.loads(base64.b64decode(response.headers["payment-required"]))
    accept = decoded["accepts"][0]
    assert accept["scheme"] == "exact"
    assert accept["network"] == settings.x402_default_network
    assert accept["payTo"].lower() == settings.x402_pay_to_address.lower()
    # $0.001 -> 1000 atomic units of 6-decimal USDC.
    assert accept["amount"] == "1000"


def test_existing_routes_are_unaffected() -> None:
    assert client.get("/health").status_code == 200
    assert client.get("/.well-known/mcp").status_code == 200


def test_mn_property_check_still_uses_its_own_hand_rolled_path() -> None:
    """Guards the "own section, don't touch current code" boundary: the
    generic middleware must not intercept a route it wasn't given."""
    response = client.get("/mn/property-check", params={"address": "1 Test St"})
    assert response.status_code in (402, 503)
    if response.status_code == 402:
        # Still the hand-rolled challenge shape, not the generic middleware's.
        assert response.json()["error"] == "payment_required"


def test_register_is_a_noop_without_pay_to_address(monkeypatch) -> None:
    monkeypatch.setattr(settings, "x402_pay_to_address", None)
    pilot_app = FastAPI()
    x402_middleware_pilot.register(pilot_app)
    pilot_client = TestClient(pilot_app)
    # No route was ever included, so it's a plain 404 -- not a 402, and not a crash.
    assert pilot_client.get("/pilot/ping").status_code == 404


@pytest.mark.parametrize("agent_id", ["dashboard-agent"])
def test_quota_route_untouched(agent_id: str) -> None:
    """Spot-check a second unrelated route family stays reachable."""
    assert client.get(f"/quota/{agent_id}").status_code == 200
