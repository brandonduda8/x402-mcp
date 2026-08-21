## 2026-08-21T15:05:15Z

You are m1_worker (teamwork_preview_worker).
Your working directory is C:/Users/Keith/x402-mcp/.agents/m1_worker.
The project root is C:/Users/Keith/x402-mcp.

MANDATORY: Read ORIGINAL_REQUEST.md at C:/Users/Keith/x402-mcp/.agents/ORIGINAL_REQUEST.md.
MANDATORY: Read PROJECT.md at C:/Users/Keith/x402-mcp/PROJECT.md.
MANDATORY: Read survey reports at:
- C:/Users/Keith/x402-mcp/.agents/survey_explorer_1/report.md
- C:/Users/Keith/x402-mcp/.agents/survey_explorer_2/report.md
- C:/Users/Keith/x402-mcp/.agents/survey_spec_miner_3/report.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Mission: Implement Milestone 1 (MCP Tools, Agent ID Cards & Prompts/Resources).

Scope & File Ownership:
You have exclusive write ownership of:
- C:/Users/Keith/x402-mcp/app/mcp_server.py
- C:/Users/Keith/x402-mcp/app/tools_registry.py
- C:/Users/Keith/x402-mcp/app/manifest.py
- C:/Users/Keith/x402-mcp/app/agent_surface.py
- C:/Users/Keith/x402-mcp/tests/test_mcp_tools.py
- C:/Users/Keith/x402-mcp/tests/test_manifest.py

Detailed Requirements:
1. Tool Parameter Docstrings:
   Update all tool functions in `app/mcp_server.py` so each docstring contains comprehensive `Args:` and `Returns:` descriptions following Google/Sphinx style, enabling FastMCP to generate complete JSON schema property descriptions for all inputs and outputs.
2. FastMCP Tool Annotations:
   Decorate all tools in `app/mcp_server.py` with `@mcp.tool(annotations={...})` including `title`, `readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`, and `agent_card` metadata matching the specifications in the survey reports.
3. Agent ID Card Tool & Resource:
   - Add `get_agent_card` tool to `app/tools_registry.py` and `app/mcp_server.py`. Update `TOOL_COUNT = 20` and `EXPECTED_TOOL_NAMES`.
   - Ensure `get_agent_card` returns the full Agent ID card for `x402-mcp` (or specified agent/tool ID) with capabilities, payment requirements, supported chains, and contact details.
   - Register MCP resource `x402://agent-card` (and additional resources `x402://server-card`, `x402://tools-manifest`, `x402://pricing-table`) using `@mcp.resource(...)`.
4. MCP Prompts:
   Register FastMCP prompts using `@mcp.prompt(...)` for common agent workflows:
   - `onboarding_flow`
   - `x402_tool_selector`
   - `generate_quote`
   - `troubleshoot_payment`
5. Test Synchronization:
   Update `tests/test_mcp_tools.py` and `tests/test_manifest.py` to test the new `get_agent_card` tool, annotations, prompts, and resources. Run pytest to verify all modified test files pass.

Handoff Deliverables:
- Write a complete handoff report to `C:/Users/Keith/x402-mcp/.agents/m1_worker/handoff.md` following the Handoff Protocol (Observation, Logic Chain, Caveats, Conclusion, Verification Method with command outputs).
- Send a message to parent summarizing your completed work.
