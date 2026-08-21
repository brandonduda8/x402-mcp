"""Manifest and HTTP endpoint tests."""

from fastapi.testclient import TestClient

from app.main import app
from app.tools_registry import EXPECTED_TOOL_NAMES, TOOL_COUNT


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "x402-micropayments-mcp"
    assert isinstance(body["wallet_configured"], bool)
    assert isinstance(body["pay_to_configured"], bool)


def test_well_known_mcp() -> None:
    response = client.get("/.well-known/mcp")
    assert response.status_code == 200
    manifest = response.json()

    assert manifest["name"] == "x402-micropayments"
    assert manifest["protocol"] == "mcp"
    assert manifest["capabilities"]["tools"] is True
    assert manifest["capabilities"]["resources"] is True
    assert manifest["capabilities"]["prompts"] is True
    assert "free" in manifest["tiers"]
    assert manifest["tiers"]["free"]["monthly_quota"] == 500
    assert manifest["tiers"]["free"]["rate_limit_per_minute"] == 10
    assert manifest["upgrade_url"]
    assert len(manifest["tools"]) == TOOL_COUNT
    tool_names = {t["name"] for t in manifest["tools"]}
    assert tool_names == EXPECTED_TOOL_NAMES
    assert manifest["tiers"]["pro"]["payment_tools"]
    assert manifest["x402"]["protocol_version"] == "v2"
    assert "PAYMENT-REQUIRED" in manifest["x402"]["headers"]["payment_required"]


def test_quota_peek_no_consume() -> None:
    agent = "peek-agent-unique"
    first = client.get(f"/quota/{agent}").json()
    second = client.get(f"/quota/{agent}").json()
    assert first["meta"]["calls_this_month"] == second["meta"]["calls_this_month"]


def test_upgrade_endpoint() -> None:
    response = client.get("/upgrade")
    assert response.status_code == 200
    body = response.json()
    assert body["upgrade_url"]
    assert "pro" in body["tiers"]
    assert body["stripe"]["checkout_endpoint"] == "/stripe/checkout"
    assert body["x402_coinbase"]["status"] == "alternate_future_rail"
    assert "create_stripe_checkout" in body["mcp_tools"]["stripe"]
    assert "get_tool_credits_requirements" in body["mcp_tools"]["tool_credits_x402"]
    assert body["tool_credits"]["pack_size"] == 100
    assert body["manifest"] == "/.well-known/mcp"


def test_manifest_payment_rails() -> None:
    manifest = client.get("/.well-known/mcp").json()
    assert manifest["payment_rails"]["stripe"]["primary"] is True
    assert manifest["payment_rails"]["x402_coinbase"]["primary"] is False
    assert manifest["endpoints"]["stripe_webhook"] == "/stripe/webhook"


def test_agent_card_endpoint() -> None:
    response = client.get("/.well-known/agent-card.json")
    assert response.status_code == 200
    card = response.json()
    assert "skills" in card
    assert any(s["id"] == "x402-agent-card" for s in card["skills"])
    assert card["protocolVersion"] == "1.0"


def test_mcp_server_card_endpoint() -> None:
    response = client.get("/.well-known/mcp/server-card.json")
    assert response.status_code == 200
    server_card = response.json()
    assert server_card["serverInfo"]["name"] == "io.github.kwizzlesurp10-ctrl/x402-mcp"
    assert server_card["capabilities"]["tools"] is True
    assert server_card["capabilities"]["resources"] is True
    assert server_card["capabilities"]["prompts"] is True
    assert len(server_card["tools"]) == TOOL_COUNT