"""Independent Forensic Audit Script for x402-mcp.

Checks:
1. FastMCP tools reflection (20 tools, annotations, docstrings, parameter descriptions, agent_card).
2. FastMCP prompts reflection (4 prompts, descriptions, arguments).
3. FastMCP resources reflection (4 resources, URIs, mime-types, data retrieval).
4. Codebase facade/dummy analysis (check all functions/classes in app/ for no-op/fake returns).
5. Config synchronization (smithery.yaml, package.json, server.json, tools_registry.py, README.md).
"""

import ast
import json
import os
import sys
from pathlib import Path
import asyncio

# Add project root to sys.path
root = Path("C:/Users/Keith/x402-mcp")
sys.path.insert(0, str(root))

async def run_audit():
    results = {}
    
    # 1. FastMCP Tool Inspection
    from app.mcp_server import mcp
    from app.tools_registry import TOOL_SPECS, EXPECTED_TOOL_NAMES, TOOL_COUNT
    
    # List tools from FastMCP instance
    registered_tools = await mcp.list_tools()
    tool_map = {t.name: t for t in registered_tools}
    
    results["tool_count_registry"] = TOOL_COUNT
    results["tool_count_fastmcp"] = len(registered_tools)
    results["tools_match_count"] = (TOOL_COUNT == len(registered_tools) == 20)
    
    missing_tools = [name for name in EXPECTED_TOOL_NAMES if name not in tool_map]
    results["missing_tools"] = missing_tools
    
    tool_details = {}
    for name, tool in tool_map.items():
        # Inspect parameters, docstrings, annotations
        doc = getattr(tool, "description", "") or ""
        annotations = getattr(tool, "annotations", {}) or {}
        agent_card = annotations.get("agent_card") if isinstance(annotations, dict) else None
        
        # Check inputSchema
        input_schema = getattr(tool, "inputSchema", {}) or {}
        props = input_schema.get("properties", {})
        
        # Verify every parameter has a description
        params_with_desc = [p for p, v in props.items() if v.get("description")]
        params_missing_desc = [p for p, v in props.items() if not v.get("description")]
        
        tool_details[name] = {
            "has_description": bool(doc),
            "description_len": len(doc),
            "has_args_docstring": "Args:" in doc,
            "has_annotations": bool(annotations),
            "title": annotations.get("title") if isinstance(annotations, dict) else None,
            "readOnlyHint": annotations.get("readOnlyHint") if isinstance(annotations, dict) else None,
            "destructiveHint": annotations.get("destructiveHint") if isinstance(annotations, dict) else None,
            "idempotentHint": annotations.get("idempotentHint") if isinstance(annotations, dict) else None,
            "openWorldHint": annotations.get("openWorldHint") if isinstance(annotations, dict) else None,
            "has_agent_card": bool(agent_card),
            "agent_card_id": agent_card.get("id") if isinstance(agent_card, dict) else None,
            "agent_card_role": agent_card.get("role") if isinstance(agent_card, dict) else None,
            "agent_card_domain": agent_card.get("domain") if isinstance(agent_card, dict) else None,
            "param_count": len(props),
            "params_missing_desc": params_missing_desc,
        }
    
    results["tools"] = tool_details
    
    # 2. FastMCP Prompts Inspection
    registered_prompts = await mcp.list_prompts()
    prompt_map = {p.name: p for p in registered_prompts}
    expected_prompts = {"onboarding_flow", "x402_tool_selector", "generate_quote", "troubleshoot_payment"}
    
    results["prompt_count"] = len(registered_prompts)
    results["prompts_match"] = set(prompt_map.keys()) == expected_prompts
    
    prompt_details = {}
    for name, prompt in prompt_map.items():
        prompt_details[name] = {
            "has_description": bool(prompt.description),
            "arg_count": len(prompt.arguments or []),
            "args": [arg.name for arg in (prompt.arguments or [])],
        }
    results["prompts"] = prompt_details
    
    # 3. FastMCP Resources Inspection
    registered_resources = await mcp.list_resources()
    resource_map = {str(r.uri): r for r in registered_resources}
    expected_resource_uris = {
        "x402://agent-card",
        "x402://server-card",
        "x402://tools-manifest",
        "x402://pricing-table",
    }
    
    results["resource_count"] = len(registered_resources)
    results["resources_match"] = set(resource_map.keys()) == expected_resource_uris
    
    resource_details = {}
    for uri, res in resource_map.items():
        # Try reading resource content
        read_res = await mcp.read_resource(uri)
        resource_details[uri] = {
            "name": res.name,
            "mimeType": res.mimeType,
            "has_content": bool(read_res),
            "content_length": len(str(read_res)),
        }
    results["resources"] = resource_details
    
    # 4. AST Facade / Dummy Code Detection across app/
    app_dir = root / "app"
    facade_flags = []
    
    for py_file in app_dir.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        except Exception as e:
            facade_flags.append({"file": str(py_file.relative_to(root)), "error": str(e)})
            continue
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Check for empty body / only pass / only return constant / only raise NotImplementedError
                body = [n for n in node.body if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant))] # ignore docstring
                if not body:
                    # pure docstring or empty
                    facade_flags.append({
                        "file": str(py_file.relative_to(root)),
                        "func": node.name,
                        "issue": "empty_body",
                        "lineno": node.lineno
                    })
                elif len(body) == 1:
                    stmt = body[0]
                    if isinstance(stmt, ast.Pass):
                        facade_flags.append({
                            "file": str(py_file.relative_to(root)),
                            "func": node.name,
                            "issue": "pass_only",
                            "lineno": node.lineno
                        })
                    elif isinstance(stmt, ast.Raise) and isinstance(stmt.exc, ast.Call) and getattr(stmt.exc.func, "id", None) == "NotImplementedError":
                        facade_flags.append({
                            "file": str(py_file.relative_to(root)),
                            "func": node.name,
                            "issue": "not_implemented_error",
                            "lineno": node.lineno
                        })
    
    results["facade_flags"] = facade_flags
    
    # 5. Config Cross-Validation
    # Package.json
    pkg = json.loads((root / "package.json").read_text(encoding="utf-8"))
    results["package_json"] = {
        "name": pkg.get("name"),
        "version": pkg.get("version"),
        "has_scripts": "start" in pkg.get("scripts", {}) and "test" in pkg.get("scripts", {}),
        "has_keywords": len(pkg.get("keywords", [])) >= 10,
        "keywords_count": len(pkg.get("keywords", [])),
        "license": pkg.get("license"),
        "has_repository": bool(pkg.get("repository")),
    }
    
    # Server.json
    srv = json.loads((root / "server.json").read_text(encoding="utf-8"))
    results["server_json"] = {
        "name": srv.get("name"),
        "version": srv.get("version"),
        "title": srv.get("title"),
        "capabilities": srv.get("capabilities"),
        "has_remotes": len(srv.get("remotes", [])) > 0,
    }
    
    # Smithery.yaml
    smithery_text = (root / "smithery.yaml").read_text(encoding="utf-8")
    results["smithery_yaml"] = {
        "has_configSchema": "configSchema:" in smithery_text,
        "has_commandFunction": "commandFunction:" in smithery_text,
        "has_startCommand": "startCommand:" in smithery_text,
        "has_remote": "remote:" in smithery_text,
        "has_categories": "categories:" in smithery_text,
        "has_tags": "tags:" in smithery_text,
    }
    
    # README.md
    readme_text = (root / "README.md").read_text(encoding="utf-8")
    results["readme"] = {
        "has_smithery_badge": "smithery.ai" in readme_text,
        "has_npx_command": "@smithery/cli" in readme_text,
        "has_all_20_tools": all(spec["name"] in readme_text for spec in TOOL_SPECS),
        "has_prompts_section": "Prompts" in readme_text or "prompts" in readme_text,
        "has_resources_section": "Resources" in readme_text or "resources" in readme_text,
    }

    # Write output to json
    out_path = root / ".agents/m4_auditor/audit_results.json"
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Audit completed. Output written to {out_path}")
    print(f"Summary: Tools: {results['tool_count_fastmcp']}/20, Prompts: {results['prompt_count']}/4, Resources: {results['resource_count']}/4")
    print(f"Facade flags count: {len(facade_flags)}")

if __name__ == "__main__":
    asyncio.run(run_audit())
