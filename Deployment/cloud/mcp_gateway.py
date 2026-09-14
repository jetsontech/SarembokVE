"""Sarembok Model Context Protocol (MCP) Gateway.

Provides the MCP JSON-RPC surface while enforcing a critical Sarembok rule:
MCP resources report observed runtime state and never fabricate infrastructure.
"""
from __future__ import annotations
import json
import logging
from typing import Any, Callable

try:
    from skills_engine import get_skills_engine
except ImportError:
    try:
        from Deployment.cloud.skills_engine import get_skills_engine
    except ImportError:
        from .skills_engine import get_skills_engine

logger = logging.getLogger("sarembok.mcp_gateway")
MCP_PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name":"sarembok-mcp-gateway","version":"2.1.0"}


class MCPGateway:
    def __init__(self, db_store: Any = None) -> None:
        self.skills_engine=get_skills_engine(); self.store=db_store
        self._custom_tool_handlers:dict[str,Callable[[dict[str,Any]],Any]]={}

    def register_tool_handler(self,tool_name:str,handler:Callable[[dict[str,Any]],Any])->None:
        self._custom_tool_handlers[tool_name]=handler

    def handle_request(self,payload:dict[str,Any]|str)->dict[str,Any]|None:
        if isinstance(payload,str):
            try:data=json.loads(payload)
            except json.JSONDecodeError as exc:return {"jsonrpc":"2.0","id":None,"error":{"code":-32700,"message":f"Parse error: {exc}"}}
        else:data=payload
        req_id=data.get("id"); method=data.get("method"); params=data.get("params") or {}
        if not req_id and method=="notifications/initialized": return None
        if not method:return {"jsonrpc":"2.0","id":req_id,"error":{"code":-32600,"message":"Invalid Request: missing method"}}
        try:return {"jsonrpc":"2.0","id":req_id,"result":self._dispatch_method(method,params)}
        except Exception as exc:
            logger.error("Error handling MCP method %s: %s",method,exc)
            return {"jsonrpc":"2.0","id":req_id,"error":{"code":-32603,"message":str(exc)}}

    def _dispatch_method(self,method:str,params:dict[str,Any])->dict[str,Any]:
        if method=="initialize":
            return {"protocolVersion":MCP_PROTOCOL_VERSION,"capabilities":{"tools":{"listChanged":False},"resources":{"subscribe":False,"listChanged":False},"prompts":{"listChanged":False}},"serverInfo":SERVER_INFO}
        if method=="ping": return {}
        if method=="tools/list": return {"tools":self.skills_engine.get_mcp_tools()}
        if method=="tools/call":
            name=params.get("name",""); args=params.get("arguments") or {}
            if name in self._custom_tool_handlers: out=self._custom_tool_handlers[name](args)
            else:
                result=self.skills_engine.execute_skill(name,args)
                if not result.get("success"):
                    return {"content":[{"type":"text","text":result.get("error","Skill execution failed")}],"isError":True}
                out=result.get("output","")
            return {"content":[{"type":"text","text":out if isinstance(out,str) else json.dumps(out,indent=2)}],"isError":False}
        if method=="resources/list":
            return {"resources":[
                {"uri":"sarembok://cluster/workers","name":"Compute Cluster Workers","description":"Observed status of registered compute workers.","mimeType":"application/json"},
                {"uri":"sarembok://memory/entries","name":"Persistent SQLite Memory","description":"Stored memory entries visible to the current MCP boundary.","mimeType":"application/json"},
                {"uri":"sarembok://system/health","name":"Runtime System Health","description":"Observed runtime and provider state.","mimeType":"application/json"},
            ]}
        if method=="resources/read":
            uri=params.get("uri","")
            if uri=="sarembok://cluster/workers":
                workers=[]
                if self.store and hasattr(self.store,"db"):
                    rows=self.store.db.execute("SELECT worker_id,status,last_heartbeat,gpu_model,vram_mb FROM workers").fetchall()
                    workers=[{"id":r[0],"status":str(r[1]).upper(),"lastHeartbeat":r[2],"gpuModel":r[3],"vramMb":r[4]} for r in rows]
                online=sum(1 for w in workers if w["status"]=="ONLINE")
                gpu=sum(1 for w in workers if w["status"]=="ONLINE" and w.get("gpuModel"))
                return {"contents":[{"uri":uri,"mimeType":"application/json","text":json.dumps({"registered":len(workers),"online":online,"onlineGpuNodes":gpu,"workers":workers},indent=2)}]}
            if uri=="sarembok://memory/entries":
                rows=[]
                if self.store and hasattr(self.store,"db"):
                    rows=self.store.db.execute("SELECT key,value,tier,created_at FROM memories ORDER BY created_at DESC LIMIT 20").fetchall()
                data=[{"key":r[0],"value":r[1],"tier":r[2],"createdAt":r[3]} for r in rows]
                return {"contents":[{"uri":uri,"mimeType":"application/json","text":json.dumps(data,indent=2)}]}
            if uri=="sarembok://system/health":
                providers=[]
                try:
                    from provider_router import ProviderRouter
                    providers=[{"name":p.name,"model":p.model,"kind":p.kind} for p in ProviderRouter().configured()]
                except Exception: pass
                return {"contents":[{"uri":uri,"mimeType":"application/json","text":json.dumps({"service":"sarembok-ve-cloud-runtime","status":"ONLINE","mcp":"enabled","configuredProviders":providers},indent=2)}]}
            raise ValueError(f"Resource not found: {uri}")
        raise ValueError(f"Unsupported MCP method: {method}")

_GLOBAL_MCP_GATEWAY:MCPGateway|None=None

def get_mcp_gateway(store:Any=None)->MCPGateway:
    global _GLOBAL_MCP_GATEWAY
    if _GLOBAL_MCP_GATEWAY is None:_GLOBAL_MCP_GATEWAY=MCPGateway(db_store=store)
    return _GLOBAL_MCP_GATEWAY
