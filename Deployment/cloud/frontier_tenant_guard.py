"""Tenant isolation helpers for the frontier RPC boundary."""
from __future__ import annotations

import hashlib
import json
from typing import Any


def scoped_session_id(subject: str, client_session_id: str) -> str:
    raw = str(client_session_id or "default").strip() or "default"
    fingerprint = hashlib.sha256(subject.encode("utf-8")).hexdigest()[:20]
    return f"srbk:{fingerprint}:{raw[:160]}"


def handle_user_rpc(runtime: Any, method: str, params: dict[str, Any], subject: str) -> tuple[bool, dict[str, Any] | None]:
    db = runtime.store.db

    if method == "StoreMemory":
        key = str(params.get("key", "")).strip(); value = str(params.get("value", "")).strip(); tier = str(params.get("tier", "WORKING")).strip().upper()
        if not key or not value: raise ValueError("key and value are required")
        import uuid
        memory_id = f"mem-{uuid.uuid4().hex[:10]}"; stamp = runtime.now()
        db.execute("INSERT INTO memories(memory_id,tier,key,value,agent_id,created_at) VALUES(?,?,?,?,?,?)",(memory_id,tier,key,value,subject,stamp)); db.commit()
        runtime.store.event(subject,"MEMORY_STORED",{"memoryId":memory_id,"tier":tier,"key":key})
        return True,{"memoryId":memory_id,"tier":tier,"key":key,"stored":True,"createdAt":stamp}

    if method in {"ListMemories","SearchMemories"}:
        query=str(params.get("query","")).strip() if method=="SearchMemories" else ""; tier=str(params.get("tier","")).strip().upper(); limit=min(100,max(1,int(params.get("limit",50))))
        sql="SELECT memory_id,tier,key,value,agent_id,created_at FROM memories WHERE agent_id=?"; args:[Any]=[subject]
        if query: sql += " AND (key LIKE ? OR value LIKE ?)"; args.extend([f"%{query}%",f"%{query}%"])
        if tier: sql += " AND tier=?"; args.append(tier)
        sql += " ORDER BY created_at DESC LIMIT ?"; args.append(limit)
        rows=db.execute(sql,args).fetchall(); memories=[{"memoryId":r[0],"tier":r[1],"key":r[2],"value":r[3],"agentId":r[4],"createdAt":r[5]} for r in rows]
        result={"memories":memories,"count":len(memories)}
        if method=="SearchMemories": result["query"]=query
        return True,result

    if method=="RecallMemory":
        key=str(params.get("key","")).strip()
        if not key: raise ValueError("key is required")
        row=db.execute("SELECT memory_id,tier,key,value,agent_id,created_at FROM memories WHERE key=? AND agent_id=? ORDER BY created_at DESC LIMIT 1",(key,subject)).fetchone()
        if not row:return True,{"found":False,"key":key,"value":None}
        return True,{"found":True,"memoryId":row[0],"tier":row[1],"key":row[2],"value":row[3],"agentId":row[4],"createdAt":row[5]}

    if method=="DeleteMemory":
        memory_id=str(params.get("memoryId","")).strip()
        if not memory_id:raise ValueError("memoryId is required")
        cur=db.execute("DELETE FROM memories WHERE memory_id=? AND agent_id=?",(memory_id,subject)); db.commit()
        if cur.rowcount: runtime.store.event(subject,"MEMORY_DELETED",{"memoryId":memory_id})
        return True,{"memoryId":memory_id,"deleted":bool(cur.rowcount)}

    if method=="SpatialVisualRecall":
        query=str(params.get("query","")).strip(); limit=min(50,max(1,int(params.get("limit",10))))
        sql="SELECT memory_id,key,value,created_at FROM memories WHERE tier='SPATIAL' AND agent_id=?"; args:[Any]=[subject]
        if query: sql += " AND (key LIKE ? OR value LIKE ?)"; args.extend([f"%{query}%",f"%{query}%"])
        sql += " ORDER BY created_at DESC LIMIT ?"; args.append(limit)
        rows=db.execute(sql,args).fetchall(); obs=[{"memoryId":r[0],"key":r[1],"observation":r[2],"createdAt":r[3]} for r in rows]
        return True,{"success":True,"query":query,"observations":obs,"count":len(obs)}

    if method=="ListUserChatSessions":
        rows=db.execute("SELECT session_id,user_id,title,created_at,updated_at FROM chat_sessions WHERE user_id=? ORDER BY updated_at DESC LIMIT 60",(subject,)).fetchall()
        return True,{"success":True,"sessions":[{"session_id":r[0],"user_id":r[1],"title":r[2],"created_at":r[3],"updated_at":r[4]} for r in rows]}

    if method=="SaveUserChatSession":
        raw_id=str(params.get("sessionId","")).strip()
        if not raw_id:return True,{"success":False,"error":"session_id_required"}
        session_id=scoped_session_id(subject,raw_id); title=str(params.get("title","Conversation")).strip(); messages=params.get("messages",[]); stamp=runtime.now()
        existing=db.execute("SELECT user_id,created_at FROM chat_sessions WHERE session_id=?",(session_id,)).fetchone()
        if existing and str(existing[0])!=subject:raise PermissionError("session_owner_mismatch")
        created_at=existing[1] if existing else stamp
        db.execute("INSERT INTO chat_sessions(session_id,user_id,title,messages_json,created_at,updated_at) VALUES(?,?,?,?,?,?) ON CONFLICT(session_id) DO UPDATE SET title=excluded.title,messages_json=excluded.messages_json,updated_at=excluded.updated_at",(session_id,subject,title,json.dumps(messages),created_at,stamp)); db.commit()
        return True,{"success":True,"sessionId":raw_id}

    if method=="DeleteUserChatSession":
        raw_id=str(params.get("sessionId","")).strip()
        if not raw_id:return True,{"success":False,"error":"session_id_required"}
        session_id=scoped_session_id(subject,raw_id); cur=db.execute("DELETE FROM chat_sessions WHERE session_id=? AND user_id=?",(session_id,subject)); db.commit()
        return True,{"success":True,"sessionId":raw_id,"deleted":bool(cur.rowcount)}

    return False,None
