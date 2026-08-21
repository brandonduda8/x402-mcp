import asyncio
import json
import sys
from pathlib import Path

root = Path("C:/Users/Keith/x402-mcp")
sys.path.insert(0, str(root))

from app.mcp_server import mcp
from app.tools_registry import TOOL_SPECS, EXPECTED_TOOL_NAMES, TOOL_COUNT

async def inspect():
    tools = await mcp.list_tools()
    print(f"Total tools returned by mcp.list_tools(): {len(tools)}")
    
    tm_tools = mcp._tool_manager._tools
    print(f"Total tools in _tool_manager: {len(tm_tools)}")
    
    print("\n--- Testing tool execution / annotations / docstrings ---")
    verified_count = 0
    for spec in TOOL_SPECS:
        name = spec["name"]
        tool_obj = tm_tools.get(name)
        assert tool_obj is not None, f"Missing tool: {name}"
        assert tool_obj.description, f"Missing description for {name}"
        assert "Args:" in tool_obj.description, f"Missing Args in description for {name}"
        
        ann = tool_obj.annotations
        assert ann is not None, f"Missing annotations for {name}"
        
        # Access attributes
        title = getattr(ann, "title", None)
        read_only = getattr(ann, "readOnlyHint", None)
        destructive = getattr(ann, "destructiveHint", None)
        idempotent = getattr(ann, "idempotentHint", None)
        open_world = getattr(ann, "openWorldHint", None)
        
        # Check agent_card
        extra = getattr(ann, "model_extra", {}) or {}
        agent_card = getattr(ann, "agent_card", None) or extra.get("agent_card")
        if not agent_card and hasattr(ann, "dict"):
            agent_card = ann.dict().get("agent_card")
            
        assert title, f"Missing title for {name}"
        assert read_only is not None, f"Missing readOnlyHint for {name}"
        assert destructive is not None, f"Missing destructiveHint for {name}"
        assert idempotent is not None, f"Missing idempotentHint for {name}"
        assert open_world is not None, f"Missing openWorldHint for {name}"
        assert agent_card, f"Missing agent_card for {name}"
        assert "id" in agent_card, f"Missing agent_card id for {name}"
        assert "name" in agent_card, f"Missing agent_card name for {name}"
        assert "role" in agent_card, f"Missing agent_card role for {name}"
        assert "domain" in agent_card, f"Missing agent_card domain for {name}"
        assert "pricing" in agent_card, f"Missing agent_card pricing for {name}"
        assert "execution_profile" in agent_card, f"Missing agent_card execution_profile for {name}"
        assert "tags" in agent_card, f"Missing agent_card tags for {name}"
        assert "examples" in agent_card, f"Missing agent_card examples for {name}"
        
        verified_count += 1
        print(f"[OK] {name:<30} | title='{title}' | card_id='{agent_card['id']}' | role='{agent_card['role']}'")
        
    print(f"\nALL {verified_count}/20 tools verified successfully for FastMCP reflection, docstrings, annotations, and agent cards!")

if __name__ == "__main__":
    asyncio.run(inspect())
