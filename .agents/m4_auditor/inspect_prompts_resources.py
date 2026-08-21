import asyncio
import json
import sys
from pathlib import Path

root = Path("C:/Users/Keith/x402-mcp")
sys.path.insert(0, str(root))

from app.mcp_server import mcp

async def test_prompts_and_resources():
    # 1. Test Prompts
    prompts = await mcp.list_prompts()
    print(f"Total prompts registered: {len(prompts)}")
    expected_prompts = {
        "onboarding_flow": ["agent_name"],
        "x402_tool_selector": ["goal", "domain"],
        "generate_quote": ["service_name", "price_usdc", "network", "pay_to"],
        "troubleshoot_payment": ["error_code", "details"],
    }
    
    prompt_map = {p.name: p for p in prompts}
    for name, expected_args in expected_prompts.items():
        assert name in prompt_map, f"Missing prompt: {name}"
        p = prompt_map[name]
        assert p.description, f"Missing description for prompt: {name}"
        actual_args = [a.name for a in (p.arguments or [])]
        assert actual_args == expected_args, f"Args mismatch for {name}: expected {expected_args}, got {actual_args}"
        print(f"[OK] Prompt: {name:<25} | description='{p.description[:50]}...' | args={actual_args}")
        
    # Execute a prompt rendering to verify no runtime failures
    for name in expected_prompts:
        args = {k: "test_value" for k in expected_prompts[name]}
        prompt_fn = mcp._prompt_manager._prompts[name].fn
        res = await prompt_fn(**args) if asyncio.iscoroutinefunction(prompt_fn) else prompt_fn(**args)
        assert res, f"Prompt {name} returned empty result"
        print(f"     Render test for {name}: SUCCESS (length: {len(res)})")

    # 2. Test Resources
    resources = await mcp.list_resources()
    print(f"\nTotal resources registered: {len(resources)}")
    expected_resources = {
        "x402://agent-card": "A2A Protocol v1.0 Agent ID Card",
        "x402://server-card": "MCP Remote Server Card",
        "x402://tools-manifest": "MCP Well-Known Tool Manifest",
        "x402://pricing-table": "x402 Pricing & Service Table",
    }
    
    res_map = {str(r.uri): r for r in resources}
    for uri, desc in expected_resources.items():
        assert uri in res_map, f"Missing resource: {uri}"
        r = res_map[uri]
        assert r.description, f"Missing description for resource: {uri}"
        print(f"[OK] Resource: {uri:<25} | name='{r.name}' | desc='{r.description[:50]}...'")
        
        # Read content via read_resource
        content = await mcp.read_resource(uri)
        assert content, f"Resource {uri} returned empty content"
        # FastMCP read_resource returns list of contents or string/bytes or ResourceContent
        text_content = ""
        if isinstance(content, list):
            text_content = content[0].content if hasattr(content[0], "content") else str(content[0])
        elif hasattr(content, "content"):
            text_content = content.content
        else:
            text_content = str(content)
            
        data = json.loads(text_content)
        assert isinstance(data, (dict, list)), f"Resource {uri} content is not JSON"
        print(f"     Read & JSON validation for {uri}: SUCCESS (keys={list(data.keys())[:5] if isinstance(data, dict) else len(data)})")

    print("\nALL 4 prompts and ALL 4 resources verified successfully!")

if __name__ == "__main__":
    asyncio.run(test_prompts_and_resources())
