"""Validation test suite for server.json, package.json, and smithery.yaml.

Ensures that all metadata manifests stay valid, discoverable, and synchronized
across MCP Registry, NPM, and Smithery.ai specifications.
"""

from __future__ import annotations

import json
import pathlib
import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
SERVER_JSON_PATH = ROOT / "server.json"
PACKAGE_JSON_PATH = ROOT / "package.json"
SMITHERY_YAML_PATH = ROOT / "smithery.yaml"

SERVER_DOC = json.loads(SERVER_JSON_PATH.read_text(encoding="utf-8"))
PACKAGE_DOC = json.loads(PACKAGE_JSON_PATH.read_text(encoding="utf-8"))
SMITHERY_DOC = yaml.safe_load(SMITHERY_YAML_PATH.read_text(encoding="utf-8"))


# --- server.json tests ---

def test_server_json_required_fields_present() -> None:
    for field in ("$schema", "name", "version", "description", "repository", "remotes", "websiteUrl"):
        assert field in SERVER_DOC, f"Missing required field: {field}"


def test_server_json_description_fits_the_registry_limit() -> None:
    assert 1 <= len(SERVER_DOC["description"]) <= 100


def test_server_json_namespace_matches_the_github_owner() -> None:
    """io.github.<owner>/<name> is only publishable by that GitHub account."""
    assert SERVER_DOC["name"].startswith("io.github.kwizzlesurp10-ctrl/")


def test_server_json_the_remote_points_at_the_mounted_transport() -> None:
    remote = SERVER_DOC["remotes"][0]
    assert remote["type"] == "streamable-http"
    # FastMCP mounts at /mcp and serves its own /mcp beneath it.
    assert remote["url"].endswith("/mcp/mcp")


@pytest.mark.skipif(
    not pathlib.Path(".git").exists(), reason="version check needs the repo"
)
def test_server_json_version_is_semver() -> None:
    parts = SERVER_DOC["version"].split(".")
    assert len(parts) == 3 and all(p.isdigit() for p in parts)


def test_server_json_capabilities() -> None:
    caps = SERVER_DOC.get("capabilities", {})
    assert caps.get("tools") is True
    assert caps.get("resources") is True
    assert caps.get("prompts") is True


# --- package.json tests ---

def test_package_json_metadata_fields() -> None:
    assert PACKAGE_DOC["name"] == "x402-mcp"
    assert PACKAGE_DOC["version"] == "0.1.0"
    assert PACKAGE_DOC["author"] == "kwizzlesurp10"
    assert PACKAGE_DOC["license"] == "MIT"
    assert "crypto" in PACKAGE_DOC["description"].lower()
    assert "agent" in PACKAGE_DOC["description"].lower()


def test_package_json_keywords() -> None:
    keywords = set(PACKAGE_DOC.get("keywords", []))
    required = {"mcp", "x402", "crypto", "ai-agents", "agent-cards", "compliance", "base", "blockchain", "fastmcp"}
    assert required.issubset(keywords), f"Missing required keywords: {required - keywords}"


def test_package_json_repository_and_links() -> None:
    repo = PACKAGE_DOC.get("repository", {})
    assert repo.get("type") == "git"
    assert "kwizzlesurp10-ctrl/x402-mcp" in repo.get("url", "")
    assert "kwizzlesurp10-ctrl/x402-mcp" in PACKAGE_DOC.get("homepage", "")
    assert "kwizzlesurp10-ctrl/x402-mcp/issues" in PACKAGE_DOC.get("bugs", {}).get("url", "")


def test_package_json_scripts() -> None:
    scripts = PACKAGE_DOC.get("scripts", {})
    assert "start" in scripts
    assert "test" in scripts
    assert "build" in scripts


# --- smithery.yaml tests ---

def test_smithery_yaml_root_metadata() -> None:
    assert SMITHERY_DOC["name"] == "kwizzlesurp10/x402-mcp"
    assert SMITHERY_DOC["displayName"] == "x402 Micropayments & Agent ID Cards MCP"
    assert SMITHERY_DOC["version"] == "0.1.0"
    assert len(SMITHERY_DOC["description"]) > 20
    assert SMITHERY_DOC["license"] == "MIT"
    assert SMITHERY_DOC["homepage"] == "https://x402-mcp.onrender.com"
    assert "kwizzlesurp10-ctrl/x402-mcp" in SMITHERY_DOC["repository"]
    assert "favicon.ico" in SMITHERY_DOC["iconUrl"]


def test_smithery_yaml_categories_and_tags() -> None:
    categories = SMITHERY_DOC.get("categories", [])
    assert isinstance(categories, list) and len(categories) >= 3
    assert "payments" in categories or "crypto" in categories

    tags = SMITHERY_DOC.get("tags", [])
    assert isinstance(tags, list) and len(tags) >= 5
    assert "x402" in tags and "mcp" in tags and "agent-cards" in tags


def test_smithery_yaml_remote_and_start_command() -> None:
    remote = SMITHERY_DOC.get("remote", {})
    assert remote.get("transport") == "streamable-http"
    assert remote.get("url", "").endswith("/mcp/mcp")
    assert remote.get("capabilities", {}).get("tools") is True
    assert remote.get("capabilities", {}).get("resources") is True
    assert remote.get("capabilities", {}).get("prompts") is True

    start = SMITHERY_DOC.get("startCommand", {})
    assert start.get("type") == "stdio"
    assert start.get("command") == "python"
    assert "run_stdio.py" in start.get("args", [])


def test_smithery_yaml_config_schema() -> None:
    schema = SMITHERY_DOC.get("configSchema", {})
    assert schema.get("type") == "object"
    props = schema.get("properties", {})
    assert isinstance(props, dict)

    expected_props = (
        "X402_PAY_TO_ADDRESS",
        "EVM_PRIVATE_KEY",
        "X402_FACILITATOR_URL",
        "X402_NETWORK",
        "DEFAULT_AGENT_ID",
        "DYNAMIC_QUOTA_MODE",
        "COINMARKETCAP_API_KEY",
        "CDP_API_KEY_ID",
        "CDP_API_KEY_SECRET",
        "STRIPE_SECRET_KEY",
        "BASE_RPC_URL",
    )
    for prop in expected_props:
        assert prop in props, f"Missing property in configSchema: {prop}"
        assert props[prop].get("type") == "string", f"Property {prop} must have type string"
        assert len(props[prop].get("description", "")) > 5, f"Property {prop} must have a description"


def test_smithery_yaml_command_function_and_example() -> None:
    cmd_fn = SMITHERY_DOC.get("commandFunction")
    assert isinstance(cmd_fn, str)
    assert "run_stdio.py" in cmd_fn
    assert "X402_PAY_TO_ADDRESS" in cmd_fn
    assert "EVM_PRIVATE_KEY" in cmd_fn

    example = SMITHERY_DOC.get("exampleConfig")
    assert isinstance(example, dict)
    assert "X402_PAY_TO_ADDRESS" in example
    assert "X402_FACILITATOR_URL" in example


# --- Cross-file sync tests ---

def test_cross_file_metadata_synchronization() -> None:
    assert SERVER_DOC["version"] == PACKAGE_DOC["version"] == str(SMITHERY_DOC["version"]) == "0.1.0"
    assert SERVER_DOC["license"] == PACKAGE_DOC["license"] == SMITHERY_DOC["license"] == "MIT"
    assert SERVER_DOC["repository"]["url"] == SMITHERY_DOC["repository"]
    assert PACKAGE_DOC["repository"]["url"].startswith(SERVER_DOC["repository"]["url"])
