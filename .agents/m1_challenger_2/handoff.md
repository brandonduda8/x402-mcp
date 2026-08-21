# Adversarial Challenge Handoff Report: get_agent_card & x402 Resources

**Agent**: `m1_challenger_2` (`teamwork_preview_challenger`)  
**Date**: 2026-08-21T15:20:00Z  
**Milestone**: Milestone 1 (MCP Tools, Agent ID Cards & Prompts/Resources)  
**Verdict**: **`APPROVE`**  

---

## 1. Observation

Direct empirical observations from executing adversarial tests on `get_agent_card` tool and `x402://` FastMCP resources:

1. **Tool Invocation & Envelope Integrity**:
   - `get_agent_card()` with no arguments returns a valid JSON string conforming to `ToolResponse` (`data`, `meta`), containing `card` (A2A Protocol v1.0), `server_card` (MCP Server Card with all 20 tools), `tools_count`, and quota tracking metadata (`quota_remaining: 499`, `calls_this_month: 1`, `agent_id`).
   - Valid `target_id` filtering was tested across 13 distinct targets including exact skill IDs (`x402-agent-card`, `us-cities-catalog`, `us-city-property-check`, `us-rental-diligence-pack`, `property-check-mn`, `property-check-sea`, `property-check-chi`), tag matching (`catalog`, `compliance`, `open-data`, `rental`), and full skill names (`A2A Agent Card & Capabilities Inspector`, `US City Open-Data Compliance Catalog`). All returned filtered skill objects under `data.skills` alongside `provider`, `securitySchemes`, and `serverInfo`.
   - Invalid and non-existent `target_id` inputs (`nonexistent_target_12345`, `get_market_depth`, `get_health`, `unknown_skill_foo_bar_baz`, `crypto_swap_v3`) gracefully fallback to the complete server agent card without raising exceptions.
   - Malicious and edge-case inputs (empty string `""`, whitespace `"   "`, special characters `!@#$%^&*()_+-=[]{}|;':",.<>?/`, unicode emoji `🔥🚀🤖💡💎⚡`, multilingual UTF-8 strings, 5,000 character strings, escape sequences `\n\t\r\v\f`, SQL injection payloads `' OR '1'='1`, XSS payloads `<script>alert('xss')</script>`, path traversal `../../../etc/passwd`, raw JSON payloads) execute cleanly without unhandled errors.

2. **Concurrency & Rate Limit Enforcement**:
   - 20 concurrent parallel invocations via `asyncio.gather` execute cleanly with isolated agent IDs and quota tracking.
   - Exhausting the rate limit (10 calls/min on free tier) returns a structured error envelope (`{"error": {"error": "rate_limit_exceeded", "message": "MCP rate limit exceeded (10/min on free tier).", ...}, "data": None, "meta": None}`) without crashing or throwing unhandled exceptions.

3. **FastMCP Resource Handlers**:
   - `x402://agent-card` returns valid JSON conforming to A2A Protocol v1.0 specification with `protocolVersion: "1.0"`, `capabilities: {streaming: False, pushNotifications: False, extendedAgentCard: False}`, 19 skills, and `x402` security scheme with `PAYMENT-SIGNATURE`.
   - `x402://server-card` returns valid JSON with `serverInfo`, `transport: streamable-http`, `authentication: x402/EIP-3009`, `capabilities: {tools: True, resources: True, prompts: True}`, and exactly 20 tools.
   - `x402://tools-manifest` returns canonical manifest JSON with all 20 registered tools, tier definitions, and protocol metadata.
   - `x402://pricing-table` returns structured pricing table including free tier quota/rate limit, Pro tier pricing, tool credits pack size/pricing, paid endpoints list, and payment rails.

4. **Test Suite Execution**:
   - Test suite `tests/test_adversarial_agent_card_m1_c2.py` (11 adversarial test cases) executed and passed 100%.
   - Combined test execution (`tests/test_mcp_tools.py tests/test_manifest.py tests/test_adversarial_agent_card_m1_c2.py`): **37 passed in 72.57s**.

---

## 2. Logic Chain

1. **Adversarial Input Resilience**:
   - `_build_card(resolved_agent_id)` in `app/mcp_server.py` checks `if target_id:` and filters `matching_skills = [s for s in card.get("skills", []) if s.get("id") == target_id or target_id in s.get("tags", []) or target_id == s.get("name")]`.
   - If `matching_skills` is non-empty, it returns the focused sub-manifest; if empty or `target_id` is non-matching, it returns the full card and server card. This design ensures that agent callers never receive unhandled 500 errors or malformed payloads regardless of query parameters.
2. **Quota & Rate Limiting Safety**:
   - `_execute_tool` resolves the calling agent ID and checks rate limits / quotas via `quota_store.consume_quota(resolved)`. If limit is exceeded, `QuotaExceededError` is caught and returned as a JSON error response before work is performed.
3. **Standards Conformance**:
   - The resources `x402://agent-card` and `x402://server-card` output valid JSON structures matching A2A Protocol v1.0 and MCP server card specifications, facilitating zero-friction automated agent discovery and Smithery.ai catalog indexing.

---

## 3. Caveats

- Testing was performed in a local hermetic environment with mocked/stubbed external RPCs where applicable.
- The A2A Agent Card lists 19 cataloged domain skills (general + city jurisdictions), whereas the MCP Server Card lists 20 MCP tools (including `get_agent_card`, payment utilities, swarm orchestrator, and telemetry). This distinction is intentional as A2A skills represent distinct product capabilities whereas MCP tools represent executable API primitives.

---

## 4. Conclusion

**Verdict: `APPROVE`**

The implementation of `get_agent_card` and the `x402://` resource handlers is robust, exception-safe, resilient to malicious/boundary inputs, and fully compliant with A2A Protocol v1.0 and MCP standards.

---

## 5. Verification Method

To independently reproduce the adversarial verification:

```bash
pytest tests/test_adversarial_agent_card_m1_c2.py -v
pytest tests/test_mcp_tools.py tests/test_manifest.py tests/test_adversarial_agent_card_m1_c2.py -v
```

### Verbatim Output:
```
============================= test session starts =============================
platform win32 -- Python 3.13.12, pytest-9.0.2, pluggy-1.6.0
collected 37 items

tests/test_mcp_tools.py::test_all_tools_registered PASSED                [  2%]
tests/test_mcp_tools.py::test_manifest_tools_match_registry PASSED       [  5%]
tests/test_mcp_tools.py::test_tool_annotations_and_agent_cards PASSED    [  8%]
tests/test_mcp_tools.py::test_tool_parameter_descriptions_complete PASSED [ 10%]
tests/test_mcp_tools.py::test_tool_docstrings_google_format PASSED       [ 13%]
tests/test_mcp_tools.py::test_mcp_prompts_registered PASSED              [ 16%]
tests/test_mcp_tools.py::test_mcp_resources_registered PASSED            [ 18%]
tests/test_mcp_tools.py::test_get_agent_card_tool_invocation PASSED      [ 21%]
tests/test_mcp_tools.py::test_get_supported_networks_tool_response_shape PASSED [ 24%]
tests/test_mcp_tools.py::test_rate_limit_through_mcp_wrapper PASSED      [ 27%]
tests/test_mcp_tools.py::test_quota_consumed_before_work_on_rate_limit PASSED [ 29%]
tests/test_mcp_tools.py::test_build_seller_requirements_missing_config PASSED [ 32%]
tests/test_mcp_tools.py::test_pay_and_fetch_missing_wallet PASSED        [ 35%]
tests/test_mcp_tools.py::test_get_payment_requirements_tool_invocable PASSED [ 37%]
tests/test_mcp_tools.py::test_pro_upgrade_agent_id_matches_meta PASSED   [ 40%]
tests/test_mcp_tools.py::test_tool_credits_requirements_agent_id_matches_meta PASSED [ 43%]
tests/test_mcp_tools.py::test_activate_pro_tier_through_mcp_wrapper PASSED [ 45%]
tests/test_mcp_tools.py::test_purchase_tool_credits_through_mcp_wrapper PASSED [ 48%]
tests/test_mcp_tools.py::test_create_stripe_checkout_through_mcp_wrapper PASSED [ 51%]
tests/test_manifest.py::test_health PASSED                               [ 54%]
tests/test_manifest.py::test_well_known_mcp PASSED                       [ 56%]
tests/test_manifest.py::test_quota_peek_no_consume PASSED                [ 59%]
tests/test_manifest.py::test_upgrade_endpoint PASSED                     [ 62%]
tests/test_manifest.py::test_manifest_payment_rails PASSED               [ 64%]
tests/test_manifest.py::test_agent_card_endpoint PASSED                  [ 67%]
tests/test_manifest.py::test_mcp_server_card_endpoint PASSED             [ 70%]
tests/test_adversarial_agent_card_m1_c2.py::TestGetAgentCardToolAdversarial::test_get_agent_card_no_arguments_default PASSED [ 72%]
tests/test_adversarial_agent_card_m1_c2.py::TestGetAgentCardToolAdversarial::test_get_agent_card_valid_target_ids PASSED [ 75%]
tests/test_adversarial_agent_card_m1_c2.py::TestGetAgentCardToolAdversarial::test_get_agent_card_invalid_and_nonexistent_targets PASSED [ 78%]
tests/test_adversarial_agent_card_m1_c2.py::TestGetAgentCardToolAdversarial::test_get_agent_card_adversarial_inputs PASSED [ 81%]
tests/test_adversarial_agent_card_m1_c2.py::TestGetAgentCardToolAdversarial::test_get_agent_card_concurrent_load PASSED [ 83%]
tests/test_adversarial_agent_card_m1_c2.py::TestGetAgentCardToolAdversarial::test_get_agent_card_rate_limit_and_quota_exhaustion PASSED [ 86%]
tests/test_adversarial_agent_card_m1_c2.py::TestFastMCPResourcesAdversarial::test_all_four_resource_uris_registered PASSED [ 89%]
tests/test_adversarial_agent_card_m1_c2.py::TestFastMCPResourcesAdversarial::test_agent_card_resource_standard_conformance PASSED [ 91%]
tests/test_adversarial_agent_card_m1_c2.py::TestFastMCPResourcesAdversarial::test_server_card_resource_standard_conformance PASSED [ 94%]
tests/test_adversarial_agent_card_m1_c2.py::TestFastMCPResourcesAdversarial::test_tools_manifest_resource_standard_conformance PASSED [ 97%]
tests/test_adversarial_agent_card_m1_c2.py::TestFastMCPResourcesAdversarial::test_pricing_table_resource_standard_conformance PASSED [100%]

======================== 37 passed in 72.57s (0:01:12) ========================
```
