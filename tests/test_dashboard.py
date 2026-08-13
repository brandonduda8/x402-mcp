"""Dashboard route — served HTML wires to real API endpoints."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

BASE_APP_ID_META = 'name="base:app_id" content="944ef4db-601d-4b22-b612-cbf733d6bd31"'


def test_root_serves_ownership_meta_and_points_at_dashboard() -> None:
    """`/` must expose Base ownership meta for scrapers (not a bare 307)."""
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert BASE_APP_ID_META in response.text
    assert 'content="0; url=/dashboard"' in response.text or 'href="/dashboard"' in response.text


def test_dashboard_serves_html() -> None:
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert BASE_APP_ID_META in response.text


def test_dashboard_polls_real_endpoints() -> None:
    """The UI must consume live API routes, not hardcoded data."""
    html = client.get("/dashboard").text
    for endpoint in (
        "/health",
        "/quota/",
        "/.well-known/mcp",
        "/upgrade",
        "/swarm/products",
        "/swarm/revenue",
        "/ledger/revenue",
    ):
        assert endpoint in html


def test_dashboard_endpoints_it_polls_are_live() -> None:
    assert client.get("/health").status_code == 200
    assert client.get("/quota/dashboard-agent").status_code == 200
    assert client.get("/.well-known/mcp").status_code == 200
    assert client.get("/upgrade").status_code == 200
    assert client.get("/swarm/products").status_code == 200
    assert client.get("/swarm/revenue").status_code == 200
    assert client.get("/ledger/revenue").status_code == 200


def test_upgrade_field_names_match_the_api() -> None:
    """The tool-credits panel rendered "undefined → undefined" in production
    because it read tc.payment_tool / tc.purchase_tool while /upgrade returns
    x402_payment_tool / x402_purchase_tool. Pin the names to the live payload
    so a rename on either side fails here instead of silently on the page."""
    payload = client.get("/upgrade").json()["tool_credits"]
    html = client.get("/dashboard").text
    for field in ("pack_size", "pack_price", "x402_payment_tool", "x402_purchase_tool"):
        assert field in payload, f"/upgrade no longer returns {field}"
        assert f"tc.{field}" in html, f"dashboard does not read tc.{field}"
    assert "tc.payment_tool" not in html
    assert "tc.purchase_tool}" not in html


def test_registered_agents_panel_is_rendered() -> None:
    """The quota panel's agent picker needs its ids and the /stats poller."""
    html = client.get("/dashboard").text
    assert 'id="agent-select"' in html
    assert 'id="q-registered"' in html
    assert "loadRegisteredAgents" in html
    assert "/stats" in html


def test_storefront_panel_is_rendered() -> None:
    """The commerce panel needs the element ids its poller writes into."""
    html = client.get("/dashboard").text
    for element_id in (
        "s-revenue",
        "s-external",
        "s-spend",
        "s-listed",
        "store-body",
        "sales-body",
    ):
        assert f'id="{element_id}"' in html


def test_storefront_poll_is_throttled_and_visibility_gated() -> None:
    """Those endpoints hit Redis, which is metered — polling must stay cheap.

    Guards two easy regressions: dropping pollStore to the 5s cadence the
    health poller uses, and losing the hidden-tab check that stops a
    backgrounded tab from spending the command budget all day.
    """
    html = client.get("/dashboard").text
    assert "setInterval(pollStore, 30000)" in html
    assert "if (document.hidden) return;" in html


def test_named_grid_areas_cover_every_section() -> None:
    """Every <section id="p-..."> must have a matching #p-... grid-area rule.

    Regression guard: p-store previously had no grid-area at all and fell
    into implicit grid placement instead of its own row.
    """
    html = client.get("/dashboard").text
    import re

    section_ids = re.findall(r'<section id="(p-[a-z]+)"', html)
    assert section_ids, "expected at least one dashboard section"
    for section_id in section_ids:
        assert f"#{section_id}{{grid-area:" in html, f"{section_id} has no grid-area rule"


def test_distribution_panel_is_rendered() -> None:
    """The outreach panel needs the element ids its poller writes into."""
    html = client.get("/dashboard").text
    for element_id in ("dist-count", "dist-body"):
        assert f'id="{element_id}"' in html


def test_distribution_poll_is_throttled_and_visibility_gated() -> None:
    """GitHub's API is rate-limited per IP — keep this slower than health/quota
    and skip it on a hidden tab, same rule as pollStore."""
    html = client.get("/dashboard").text
    assert "setInterval(loadDistribution, 60000)" in html
    assert "async function loadDistribution(){\n  if (document.hidden) return;" in html


def test_distribution_never_renders_fetched_text_as_html() -> None:
    """Outreach threads live on repos we don't control — their titles/comment
    bodies must never reach innerHTML, only our own hardcoded labels and
    structured (state/count/date) fields via textContent."""
    html = client.get("/dashboard").text
    assert "pr.title" not in html
    assert "pr.body" not in html
    assert "a.textContent = r.label" in html
