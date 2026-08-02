"""`/openapi.json` is the document x402scan reads FIRST — it has to sell.

Before app/openapi_spec.py existed, FastAPI's generated spec told the largest
x402 explorer that this storefront had 33 routes and nothing for sale
(`L2_NO_PAID_ROUTES` from their own `@agentcash/discovery` auditor), and
published the operator surface while it was at it. These tests pin both halves:
every product is declared payable, and nothing operational is declared at all.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import agent_surface, openapi_spec
from app.config import settings
from app.main import app

client = TestClient(app)


@pytest.fixture
def spec() -> dict:
    return client.get("/openapi.json").json()


def test_every_paid_product_is_declared_payable(spec: dict) -> None:
    """The regression: a paid route the crawler cannot tell is paid."""
    paid = openapi_spec.paid_paths()
    assert paid, "no paid products resolved — the spec would advertise a free API"

    for path, amount in paid.items():
        operation = spec["paths"][path]["get"]
        info = operation["x-payment-info"]
        assert info["protocols"] == [{"x402": {}}]
        assert info["price"] == {"mode": "fixed", "currency": "USD", "amount": amount}
        assert "402" in operation["responses"]


def test_prices_are_decimal_usd_not_atomic_units(spec: dict) -> None:
    """Atomic units where dollars belong is on x402scan's published list of
    common registration failures ($0.01 is "0.01" here, "10000" on the wire)."""
    for path in openapi_spec.paid_paths():
        amount = spec["paths"][path]["get"]["x-payment-info"]["price"]["amount"]
        assert float(amount) < 100, f"{path} looks like atomic units: {amount}"
        assert not amount.startswith("$")


def test_the_paid_set_matches_the_other_discovery_documents(spec: dict) -> None:
    """One source of truth: adding a product to agent_surface must reach here."""
    from_surface = {
        openapi_spec._path_of(r["url"])
        for r in agent_surface.paid_resources()
        if r["price"] != "free"
    }
    declared = {p for p, o in spec["paths"].items() if "x-payment-info" in o.get("get", {})}
    assert from_surface <= declared, f"undeclared paid resources: {from_surface - declared}"


def test_the_operator_surface_is_not_published(spec: dict) -> None:
    leaked = [p for p in openapi_spec.OPERATOR_PATHS if p in spec["paths"]]
    assert not leaked, f"operator routes exposed in the public spec: {leaked}"


def test_a_new_route_is_private_by_default(spec: dict) -> None:
    """The allowlist has to fail closed — an unlisted route stays unlisted."""
    from fastapi.openapi.utils import get_openapi

    generated = set(
        get_openapi(title=app.title, version=app.version, routes=app.routes)["paths"]
    )
    published = set(spec["paths"])
    # Only the concrete purchase URL is published without being generated.
    assert published - generated <= {
        f"/swarm/products/{settings.pinned_pulse_product_id}/purchase"
    }
    assert len(generated - published) > 15, "the spec published its whole inventory"


def test_free_routes_say_public_on_purpose(spec: dict) -> None:
    """`security: []` is the marker their auditor asks for; silence reads as an
    oversight and earns an AUTH_MODE_MISSING warning per route."""
    for path in openapi_spec.PUBLIC_FREE_PATHS:
        for operation in spec["paths"][path].values():
            assert operation.get("security") == [], f"{path} has no explicit auth mode"


def test_agents_get_the_payment_flow_without_reading_our_docs(spec: dict) -> None:
    guidance = spec["info"]["x-guidance"]
    assert "PAYMENT-REQUIRED" in guidance and "PAYMENT-SIGNATURE" in guidance
    assert "/llms.txt" in guidance
    assert spec["info"]["contact"]["url"]
    assert spec["servers"][0]["url"] == settings.public_base_url.rstrip("/")


def test_the_cataloged_purchase_url_is_concrete_not_templated(spec: dict) -> None:
    """A crawler cannot probe `{product_id}`; only a real URL is registerable."""
    assert "/swarm/products/{product_id}/purchase" not in spec["paths"]
    if settings.pinned_pulse_product_id:
        concrete = f"/swarm/products/{settings.pinned_pulse_product_id}/purchase"
        assert concrete in spec["paths"]
        assert "product_id" not in str(spec["paths"][concrete]["get"].get("parameters", []))


def test_no_pinned_product_means_no_advertised_purchase_url(monkeypatch) -> None:
    """Advertising a listing that may not exist earns "expected 402, got 404"."""
    monkeypatch.setattr(settings, "pinned_pulse_product_id", "")
    assert not [p for p in openapi_spec.paid_paths() if p.endswith("/purchase")]


@pytest.mark.parametrize(
    ("price", "expected"),
    [("$0.01", "0.01"), ("0.05", "0.05"), ("free", None), ("", None), ("$x", None)],
)
def test_price_parsing(price: str, expected: str | None) -> None:
    assert openapi_spec._price_amount(price) == expected


def test_the_spec_follows_a_reprice_without_a_redeploy(monkeypatch, spec: dict) -> None:
    """Not cached on purpose — a stale spec quotes a price we no longer charge."""
    before = spec["paths"]["/base/tx-decision"]["get"]["x-payment-info"]["price"]["amount"]
    monkeypatch.setattr(settings, "tx_decision_price", "$0.99")
    after = client.get("/openapi.json").json()["paths"]["/base/tx-decision"]["get"][
        "x-payment-info"
    ]["price"]["amount"]
    assert before != after == "0.99"
