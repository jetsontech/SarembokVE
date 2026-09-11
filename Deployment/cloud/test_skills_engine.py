"""Unit tests for Sarembok VE Dynamic Skills Engine and MCP Gateway."""
from __future__ import annotations

import unittest
from pathlib import Path

from skills_engine import SkillsEngine, get_skills_engine
from mcp_gateway import MCPGateway, MCP_PROTOCOL_VERSION


class TestSkillsEngineAndMCP(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = get_skills_engine()
        self.mcp = MCPGateway()

    def test_skills_discovery(self) -> None:
        skills = self.engine.list_skills()
        self.assertGreaterEqual(len(skills), 5)
        names = {s.name for s in skills}
        self.assertIn("generate_image", names)
        self.assertIn("browser_navigate", names)
        self.assertIn("memory_recall", names)
        self.assertIn("media_streamer", names)
        self.assertIn("execute_code", names)

    def test_openai_tools_format(self) -> None:
        tools = self.engine.get_openai_tools()
        self.assertGreaterEqual(len(tools), 5)
        for t in tools:
            self.assertEqual(t["type"], "function")
            func = t["function"]
            self.assertIn("name", func)
            self.assertIn("description", func)
            self.assertIn("parameters", func)
            self.assertEqual(func["parameters"].get("type"), "object")

    def test_mcp_tools_format(self) -> None:
        tools = self.engine.get_mcp_tools()
        self.assertGreaterEqual(len(tools), 5)
        for t in tools:
            self.assertIn("name", t)
            self.assertIn("description", t)
            self.assertIn("inputSchema", t)

    def test_skill_execution(self) -> None:
        res = self.engine.execute_skill("generate_image", {"prompt": "neon city"})
        self.assertTrue(res["success"])
        self.assertEqual(res["skill"], "generate_image")

    def test_mcp_initialize(self) -> None:
        req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": MCP_PROTOCOL_VERSION},
        }
        res = self.mcp.handle_request(req)
        self.assertEqual(res["jsonrpc"], "2.0")
        self.assertEqual(res["id"], 1)
        self.assertEqual(res["result"]["protocolVersion"], MCP_PROTOCOL_VERSION)
        self.assertIn("tools", res["result"]["capabilities"])
        self.assertIn("resources", res["result"]["capabilities"])

    def test_mcp_tools_list(self) -> None:
        req = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
        }
        res = self.mcp.handle_request(req)
        self.assertEqual(res["id"], 2)
        tools = res["result"]["tools"]
        self.assertGreaterEqual(len(tools), 5)

    def test_mcp_tools_call(self) -> None:
        req = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "generate_image",
                "arguments": {"prompt": "cybernetic neural matrix"},
            },
        }
        res = self.mcp.handle_request(req)
        self.assertEqual(res["id"], 3)
        self.assertFalse(res["result"]["isError"])
        content = res["result"]["content"]
        self.assertTrue(len(content) >= 1)
        self.assertEqual(content[0]["type"], "text")

    def test_mcp_resources(self) -> None:
        req = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "resources/list",
        }
        res = self.mcp.handle_request(req)
        self.assertEqual(res["id"], 4)
        resources = res["result"]["resources"]
        uris = {r["uri"] for r in resources}
        self.assertIn("sarembok://cluster/workers", uris)
        self.assertIn("sarembok://memory/entries", uris)
        self.assertIn("sarembok://system/health", uris)


if __name__ == "__main__":
    unittest.main()
