# Milestone 1 Review Handoff Report: FastMCP Compatibility, Schema Integrity, Prompts & Resources

**Reviewer**: `m1_reviewer_2` (`teamwork_preview_reviewer`)  
**Roles**: `reviewer`, `critic`  
**Date**: 2026-08-21T15:16:45Z  
**Verdict**: **APPROVE**  

---

## 1. Observation

Direct code and test observations from the repository:

1. **FastMCP Prompts Inspection (`app/mcp_server.py:1516-1688`)**:
   - `onboarding_flow`: Registered via `@mcp.prompt()`, parameterized with `agent_name: Annotated[str, Field(description="...")] = "agent"`. Emits complete markdown guidance covering agent identity (`get_agent_card`, `x402://agent-card`), city property compliance flow (`list_us_cities` -> `get_us_city_property_sample` -> `check_us_city_property`), Base pulse checks (`get_base_pulse`), and quota/subscription management.
   - `x402_tool_selector`: Registered via `@mcp.prompt()`, parameterized with `goal: str = "compliance"` and `domain: str | None = None`. Provides a comprehensive routing matrix across 8 functional agent domains.
   - `generate_quote`: Registered via `@mcp.prompt()`, parameterized with `service_name`, `price_usdc`, `network`, and `pay_to`. Emits actionable steps to construct HTTP 402 seller challenges.
   - `troubleshoot_payment`: Registered via `@mcp.prompt()`, parameterized with `error_code` and `details`. Emits recovery steps for `rate_limit_exceeded`, `payment_invalid`, `502_facilitator`, and missing private key errors.

2. **FastMCP Resources Inspection (`app/mcp_server.py:1695-1746`)**:
   - `x402://agent-card`: Registered via `@mcp.resource("x402://agent-card")`, returns formatted JSON of `agent_card()` including A2A v1.0 skills, provider, and security schemes.
   - `x402://server-card`: Registered via `@mcp.resource("x402://server-card")`, returns formatted JSON of `mcp_server_card()` with `serverInfo`, `capabilities: {"tools": True, "resources": True, "prompts": True}`, and all 20 tools.
   - `x402://tools-manifest`: Registered via `@mcp.resource("x402://tools-manifest")`, returns formatted JSON of `build_mcp_manifest()`.
   - `x402://pricing-table`: Registered via `@mcp.resource("x402://pricing-table")`, returns formatted JSON with live pricing from `settings`, `paid_resources()`, and `build_payment_rails()`.

3. **`get_agent_card` Implementation & Error Handling (`app/mcp_server.py:1422-1509`)**:
   - Annotated with `ToolAnnotations` (`title`, `readOnlyHint: True`, `destructiveHint: False`, `idempotentHint: True`, `openWorldHint: False`) and complete `agent_card` schema (`id: "x402-agent-card"`, `role: "identity"`, `domain: "agent-identity"`, `pricing: {"model": "free"}`).
   - Docstrings contain detailed descriptions, `Args:`, and `Returns:`.
   - Wrapped via `_execute_tool`: enforces quota checks preemptively, catches `QuotaExceededError` returning `{error: ..., data: None, meta: None}`, resolves `agent_id`, and emits telemetry events.
   - Supports `target_id` filtering across skill ID, tags, or skill name, falling back safely to the full server card when unfiltered or unmatched.

4. **Single Source of Truth Consistency**:
   - `app/tools_registry.py`: `TOOL_COUNT = 20`, `EXPECTED_TOOL_NAMES` contains all 20 registered tools including `get_agent_card`.
   - `app/manifest.py`: Dynamically generates tool entries from `TOOL_SPECS`, capabilities report `tools: True`, `resources: True`, `prompts: True`.
   - `app/agent_surface.py`: `agent_card()["skills"]` contains `x402-agent-card`.

5. **Test Suite Verification**:
   - Executed: `pytest tests/test_mcp_tools.py tests/test_manifest.py tests/test_assessor.py tests/test_mcp_stdio.py -v`
   - Result: `37 passed in 93.84s`.

---

## 2. Logic Chain

1. **Schema & Protocol Integrity**:
   - FastMCP extracts tool parameter descriptions from Pydantic `Field(description="...")` annotations on function signatures and parses Google-style docstrings. All 20 tools satisfy both requirements, ensuring clients receiving tool definitions have complete machine-readable documentation for every parameter.
2. **Prompts and Resources Operational Readiness**:
   - Testing confirms all 4 prompts and 4 resources are registered in the FastMCP internal registries (`_prompt_manager` and `_resource_manager`), return valid JSON / markdown content without runtime exceptions, and are discoverable via MCP protocol transports.
3. **Adversarial & Edge-Case Evaluation**:
   - Challenged `get_agent_card` with non-existent `target_id`: gracefully falls back to returning the full server card, preserving usability for exploratory agents.
   - Challenged rate-limiting & quota exhaustion on stdio and HTTP transports: quota is checked preemptively before invoking expensive downstream handlers, preventing unauthorized resource consumption.
   - Checked for integrity violations: Zero hardcoded mock outputs in production modules, zero facade implementations, zero bypasses of core logic.

---

## 3. Caveats

- `README.md`, `smithery.yaml`, `package.json`, and `server.json` synchronization belongs to Milestones 2 and 3 as defined in `PROJECT.md`.
- Stdio transport tests require spawning real python subprocesses (`run_stdio.py`), which is verified and passes hermetically.

---

## 4. Conclusion

**Verdict: APPROVE**

The implementation of Milestone 1 in `app/mcp_server.py`, `app/tools_registry.py`, `app/agent_surface.py`, and `app/manifest.py` strictly satisfies all requirements and acceptance criteria:
- Complete behavioral annotations and Agent ID cards across all 20 MCP tools.
- 4 FastMCP prompts and 4 FastMCP resources are fully registered, operational, and tested.
- `get_agent_card` provides robust Agent-to-Agent discovery with quota tracking and error handling.
- All 37 targeted and regression tests pass with 100% success rate.

---

## 5. Verification Method

To independently reproduce the verification:

```bash
pytest tests/test_mcp_tools.py tests/test_manifest.py tests/test_assessor.py tests/test_mcp_stdio.py -v
```

### Verbatim Test Execution Output:

```
============================= test session starts =============================
platform win32 -- Python 3.13.12, pytest-9.0.2, pluggy-1.6.0 -- C:\Users\Keith\AppData\Local\Programs\Python\Python313\python.exe
cachedir: .pytest_cache
rootdir: C:\Users\Keith\x402-mcp
configfile: pyproject.toml
plugins: anyio-4.12.1, langsmith-0.7.6, asyncio-1.3.0
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 37 items

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
tests/test_assessor.py::test_assessment_shape_and_ordering PASSED        [ 72%]
tests/test_assessor.py::test_weights_sum_to_one PASSED                   [ 75%]
tests/test_assessor.py::test_growth_functions_are_human_gated PASSED     [ 78%]
tests/test_assessor.py::test_signals_are_real PASSED                     [ 81%]
tests/test_assessor.py::test_feedback_loop_marks_completed_charters PASSED [ 83%]
tests/test_assessor.py::test_product_focus_realignment PASSED            [ 86%]
tests/test_mcp_stdio.py::test_stdio_get_supported_networks PASSED        [ 89%]
tests/test_mcp_stdio.py::test_stdio_get_payment_requirements PASSED      [ 91%]
tests/test_mcp_stdio.py::test_stdio_get_pro_upgrade_requirements PASSED  [ 94%]
tests/test_mcp_stdio.py::test_stdio_get_tool_credits_requirements PASSED [ 97%]
tests/test_mcp_stdio.py::test_stdio_quota_exceeded_includes_upgrade_tools PASSED [100%]

======================== 37 passed in 93.84s (0:01:33) ========================
```
