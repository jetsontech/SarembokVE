"""Unit tests for Sarembok MCP Client Manager and Global Tools Integration."""
from mcp_client import MCPClientManager, ExternalMcpServer
from skills_engine import SkillsEngine


def test_mcp_client_manager_load(tmp_path):
    config_file = tmp_path / "mcp_servers.json"
    mgr = MCPClientManager(config_path=config_file)
    assert config_file.exists()
    assert len(mgr.servers) > 0
    assert "sqlite" not in mgr.servers
    assert "memory-hub" in mgr.servers


def test_non_mcp_sqlite_shell_is_rejected(tmp_path):
    config_file = tmp_path / "mcp_servers.json"
    config_file.write_text(
        '{"mcpServers":{"sqlite":{"transport":"stdio","command":"python","args":["-m","sqlite3"]}}}',
        encoding="utf-8",
    )
    mgr = MCPClientManager(config_path=config_file)
    assert "sqlite" not in mgr.servers


def test_mcp_client_register_and_status(tmp_path):
    config_file = tmp_path / "mcp_servers.json"
    mgr = MCPClientManager(config_path=config_file)
    status = mgr.register_server(
        name="test-server",
        transport="http",
        url="https://api.example.com/mcp",
    )
    assert status["name"] == "test-server"
    assert status["transport"] == "http"
    assert "test-server" in mgr.servers


def test_skills_engine_external_mcp_tools(tmp_path):
    from mcp_client import set_mcp_client_manager
    config_file = tmp_path / "mcp_servers.json"
    mgr = MCPClientManager(config_path=config_file)
    srv = ExternalMcpServer(name="sqlite", transport="stdio", command="python")
    srv.tools = [{
        "name": "query_database",
        "description": "Query a database",
        "inputSchema": {
            "type": "object",
            "properties": {"sql": {"type": "string"}},
            "required": ["sql"],
        },
    }]
    mgr.servers["sqlite"] = srv
    set_mcp_client_manager(mgr)
    try:
        engine = SkillsEngine(skills_dir=tmp_path / "skills")
        tools = engine.get_openai_tools()
        mcp_names = [t["function"]["name"] for t in tools if t["function"]["name"].startswith("mcp_")]
        assert "mcp_sqlite_query_database" in mcp_names
    finally:
        set_mcp_client_manager(None)
