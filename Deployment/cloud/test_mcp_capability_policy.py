from __future__ import annotations

from mcp_capability_policy import McpCapabilityPolicy, classify_tool
from mcp_client import ExternalMcpServer, MCPClientManager, set_mcp_client_manager
from skills_engine import SkillsEngine


def test_classify_read_only_tool():
    tool = {
        "name": "search_repositories",
        "description": "Search repositories",
        "annotations": {"readOnlyHint": True, "destructiveHint": False},
    }
    assert classify_tool(tool) == "read"


def test_classify_mutating_tool():
    tool = {"name": "delete_repository", "description": "Delete a repository"}
    assert classify_tool(tool) == "write"


def test_policy_blocks_write_without_approval():
    policy = McpCapabilityPolicy()
    decision = policy.authorize(
        "github",
        {"name": "delete_repository", "description": "Delete a repository"},
        {},
        {},
    )
    assert decision.allowed is False
    assert decision.risk == "write"
    assert decision.audit_id


def test_policy_allows_write_with_explicit_approval():
    policy = McpCapabilityPolicy()
    decision = policy.authorize(
        "github",
        {"name": "create_issue", "description": "Create an issue"},
        {"title": "test"},
        {"mcp_approval": "approved", "caller": "integration-test"},
    )
    assert decision.allowed is True


def test_skills_engine_blocks_external_mutation(tmp_path):
    config = tmp_path / "mcp_servers.json"
    mgr = MCPClientManager(config_path=config)
    mgr.servers = {
        "github": ExternalMcpServer(
            name="github",
            transport="stdio",
            command="python",
            tools=[
                {
                    "name": "delete_repository",
                    "description": "Delete a repository",
                    "inputSchema": {"type": "object", "properties": {}},
                }
            ],
        )
    }
    set_mcp_client_manager(mgr)
    try:
        engine = SkillsEngine(skills_dir=tmp_path / "skills")
        result = engine.execute_skill("mcp_github_delete_repository", {})
        assert result["success"] is False
        assert result["policy"]["allowed"] is False
        assert result["policy"]["risk"] == "write"
    finally:
        set_mcp_client_manager(None)


def test_skills_engine_allows_external_read_and_calls_manager(tmp_path, monkeypatch):
    config = tmp_path / "mcp_servers.json"
    mgr = MCPClientManager(config_path=config)
    mgr.servers = {
        "github": ExternalMcpServer(
            name="github",
            transport="stdio",
            command="python",
            tools=[
                {
                    "name": "search_repositories",
                    "description": "Search repositories",
                    "inputSchema": {"type": "object", "properties": {}},
                }
            ],
        )
    }
    called = {}

    def fake_call(server, tool, arguments):
        called.update(server=server, tool=tool, arguments=arguments)
        return {"repositories": []}

    monkeypatch.setattr(mgr, "call_external_tool", fake_call)
    set_mcp_client_manager(mgr)
    try:
        engine = SkillsEngine(skills_dir=tmp_path / "skills")
        result = engine.execute_skill(
            "mcp_github_search_repositories",
            {"q": "Sarembok"},
            {"caller": "integration-test"},
        )
        assert result["success"] is True
        assert result["policy"]["allowed"] is True
        assert called == {
            "server": "github",
            "tool": "search_repositories",
            "arguments": {"q": "Sarembok"},
        }
    finally:
        set_mcp_client_manager(None)
