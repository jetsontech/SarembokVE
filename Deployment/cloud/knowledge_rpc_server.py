"""Production JSON-RPC entrypoint with streaming dialogue bridge."""
from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import time
import sys

import websockets

from provider_router import reset_stream_callback, set_stream_callback

CLOUD_SERVER_PATH = "/app/server.py"
spec = importlib.util.spec_from_file_location("sarembok_cloud_server", CLOUD_SERVER_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Unable to load cloud server: {CLOUD_SERVER_PATH}")
cloud_server = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = cloud_server
spec.loader.exec_module(cloud_server)

sys.path.insert(0, "/app/Runtime")
from sarembok_knowledge_api import KnowledgeRuntimeAPI
from sarembok_knowledge_runtime import PersistentKnowledgeRuntime

knowledge_runtime = PersistentKnowledgeRuntime(cloud_server.DB_PATH)
knowledge_api = KnowledgeRuntimeAPI(knowledge_runtime)
_original_dispatch = cloud_server.dispatch
_original_process_http_request = cloud_server.process_http_request


def dispatch(method: str, params: dict) -> dict:
    if method in KnowledgeRuntimeAPI.METHODS:
        return knowledge_api.dispatch(method, params)
    return _original_dispatch(method, params)


cloud_server.dispatch = dispatch
CHAT_METHODS = {"SarembokChat", "AriaChat", "Chat", "AriaDialogue", "SarembokDialogue"}


async def handler(websocket) -> None:
    peer = getattr(websocket, "remote_address", None)
    cloud_server.LOG.info("connection_open peer=%s", peer)
    try:
        async for raw in websocket:
            request = None
            token_ctx = None
            try:
                if isinstance(raw, str) and len(raw.encode("utf-8")) > cloud_server.MAX_REQUEST_BYTES:
                    raise ValueError("request_too_large")
                request = json.loads(raw)
                method, params = cloud_server.validate_request(request)
                stream_requested = bool(params.get("stream")) and method in CHAT_METHODS
                first_delta_at = [None]
                started_at = time.perf_counter()
                if stream_requested:
                    loop = asyncio.get_running_loop()
                    request_id = request.get("id")
                    def emit_delta(text: str) -> None:
                        if first_delta_at[0] is None:
                            first_delta_at[0] = time.perf_counter()
                        event = {"jsonrpc": "2.0", "method": "SarembokChat.delta", "params": {"id": request_id, "text": text}}
                        future = asyncio.run_coroutine_threadsafe(websocket.send(json.dumps(event, separators=(",", ":"))), loop)
                        future.result(timeout=10)
                    token_ctx = set_stream_callback(emit_delta)
                async with cloud_server.get_db_lock():
                    result = await asyncio.to_thread(dispatch, method, params)
                if token_ctx is not None:
                    reset_stream_callback(token_ctx)
                    token_ctx = None
                    if isinstance(result, dict):
                        metadata = result.get("metadata")
                        if isinstance(metadata, dict):
                            metadata["streamed"] = True
                            metadata["ttft_ms"] = round((first_delta_at[0] - started_at) * 1000, 1) if first_delta_at[0] is not None else None
                response = {"jsonrpc": "2.0", "id": request.get("id"), "result": result}
                cloud_server.LOG.info("rpc_success method=%s request_id=%s streamed=%s", method, request.get("id"), stream_requested)
            except cloud_server.PermissionError as exc:
                response = {"jsonrpc": "2.0", "id": request.get("id") if isinstance(request, dict) else None, "error": {"code": -32001, "message": str(exc)}}
                cloud_server.LOG.warning("rpc_auth_failed peer=%s", peer)
            except Exception as exc:
                if token_ctx is not None:
                    try: reset_stream_callback(token_ctx)
                    except Exception: pass
                response = {"jsonrpc": "2.0", "id": request.get("id") if isinstance(request, dict) else None, "error": {"code": -32000, "message": str(exc)}}
                cloud_server.LOG.warning("rpc_error peer=%s error=%s", peer, exc)
            await websocket.send(json.dumps(response, separators=(",", ":")))
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        cloud_server.LOG.info("connection_close peer=%s", peer)


cloud_server.handler = handler


async def process_http_request(connection, request):
    path = getattr(request, "path", None) or getattr(connection, "path", "/")
    if path not in ("/", "/index.html"):
        return await _original_process_http_request(connection, request)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(base_dir, "frontend", "index.html"),
        os.path.join(base_dir, "..", "frontend", "index.html"),
        os.path.join(base_dir, "..", "..", "frontend", "index.html"),
        os.path.abspath(os.path.join(os.getcwd(), "frontend", "index.html")),
        "/app/frontend/index.html",
        "frontend/index.html",
    ]
    html_str = None
    for cand in candidates:
        if os.path.exists(cand):
            try:
                with open(cand, "r", encoding="utf-8") as f: html_str = f.read()
                break
            except Exception as exc: cloud_server.LOG.error("Failed to read frontend index.html: %s", exc)
    if not html_str:
        html_str = "<!DOCTYPE html><html><body><h1>Sarembok VE Cloud Runtime</h1><p>Status: ONLINE</p></body></html>\n"
    streaming_script = r'''<script id="sarembok-streaming-v1">
(()=>{
  const esc=s=>String(s??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#039;');
  const waitOpen=ws=>new Promise((resolve,reject)=>{if(ws.readyState===WebSocket.OPEN)return resolve();const ok=()=>{cleanup();resolve()};const bad=()=>{cleanup();reject(new Error('WebSocket connection failed'))};const cleanup=()=>{ws.removeEventListener('open',ok);ws.removeEventListener('error',bad);ws.removeEventListener('close',bad)};ws.addEventListener('open',ok);ws.addEventListener('error',bad);ws.addEventListener('close',bad)});
  window.sendDirective=async function(){
    const input=document.getElementById('directive-input'), history=document.getElementById('dialogue-history'); if(!input||!history)return;
    const txt=input.value.trim(); if(!txt)return; input.value='';
    const user=document.createElement('div'); user.className='srbk-message user'; user.innerHTML='<div class="srbk-bubble"><div class="srbk-meta"><strong>YOU</strong></div><div class="srbk-content">'+esc(txt)+'</div></div><div class="srbk-avatar user-avatar">YOU</div>'; history.appendChild(user);
    const ai=document.createElement('div'); ai.className='srbk-message ai'; ai.innerHTML='<div class="srbk-avatar">ARIA</div><div class="srbk-bubble"><div class="srbk-meta"><strong>ARIA</strong><span>STREAMING</span></div><div class="srbk-content"><span class="srbk-thinking"><i></i><i></i><i></i></span></div><div class="srbk-status">Generating</div></div>'; history.appendChild(ai); history.scrollTop=history.scrollHeight;
    const content=ai.querySelector('.srbk-content'), status=ai.querySelector('.srbk-status'); let text=''; const id='stream-'+Date.now()+'-'+Math.random().toString(16).slice(2); let settled=false;
    try{
      const session=await fetch('/session',{cache:'no-store'}).then(r=>{if(!r.ok)throw new Error('Unable to establish browser session');return r.json()});
      if(!session.sessionToken)throw new Error('Browser session token missing');
      const proto=location.protocol==='https:'?'wss:':'ws:'; const socket=new WebSocket(proto+'//'+location.host+'/ws'); await waitOpen(socket);
      const done=new Promise((resolve,reject)=>{
        socket.addEventListener('message',e=>{try{const d=JSON.parse(e.data); if(d.method==='SarembokChat.delta'&&d.params&&d.params.id===id){text+=String(d.params.text||'');content.textContent=text;history.scrollTop=history.scrollHeight;return} if(d.id===id){settled=true;if(d.error)reject(new Error(d.error.message||'Runtime error'));else resolve(d.result)}}catch(err){reject(err)}});
        socket.addEventListener('error',()=>reject(new Error('Streaming connection error')));
        socket.addEventListener('close',()=>{if(!settled)reject(new Error('Streaming connection closed'))});
      });
      socket.send(JSON.stringify({jsonrpc:'2.0',id,method:'SarembokChat',params:{sessionToken:session.sessionToken,prompt:txt,stream:true}}));
      const result=await Promise.race([done,new Promise((_,reject)=>setTimeout(()=>reject(new Error('Runtime request timeout')),45000))]);
      const reply=result&&result.response?result.response:text; content.textContent=reply||'Directive executed.'; status.textContent='Complete'; socket.close();
    }catch(err){content.textContent=text||('Unable to complete directive: '+String(err.message||err)); status.textContent='Error'; status.classList.add('srbk-error')}
  };
})();
</script>'''
    html_str = html_str.replace("</body>", streaming_script + "</body>", 1)
    if hasattr(connection, "respond"):
        resp = connection.respond(200, html_str)
        try: del resp.headers["Content-Type"]
        except Exception: pass
        resp.headers["Content-Type"] = "text/html; charset=utf-8"
        resp.headers["Cache-Control"] = "no-cache"
        return resp
    return (200, [("Content-Type", "text/html; charset=utf-8")], html_str.encode("utf-8"))


cloud_server.process_http_request = process_http_request

if __name__ == "__main__":
    asyncio.run(cloud_server.main())
