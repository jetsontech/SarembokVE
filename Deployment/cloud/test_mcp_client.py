"""Unit tests for Sarembok MCP Client Manager and Global Tools Integration."""
import pytest
from mcp_client import MCPClientManager, ExternalMcpServer
from skills_engine import SkillsEngine


def test_mcp_client_manager_load(tmp_path):
    config_file = tmp_path / "mcp_servers.json"
    mgr = MCPClientManager(config_path=config_file)
    
    assert config_file.exists()
    assert len(mgr.servers) > 0
    assert "sqlite" in mgr.servers


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
    # Manually add a mock external tool
    srv = mgr.servers["sqlite"]
    srv.tools = [{
        "name": "query_database",
        "description": "Execute a SQL query against local database",
        "inputSchema": {
            "type": "object",
            "properties": {"sql": {"type": "string"}},
            "required": ["sql"],
        }
    }]
    set_mcp_client_manager(mgr)
    try:
        engine = SkillsEngine(skills_dir=tmp_path / "skills")
        tools = engine.get_openai_tools()
        
        # Check if tools contain mcp_sqlite_query_database
        mcp_names = [t["function"]["name"] for t in tools if t["function"]["name"].startswith("mcp_")]
        assert len(mcp_names) >= 1
        assert "mcp_sqlite_query_database" in mcp_names
    finally:
        set_mcp_client_manager(None)

