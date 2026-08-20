#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE=(docker compose -f "$ROOT_DIR/Deployment/cloud/compose.yaml" -f "$ROOT_DIR/Deployment/cloud/compose.production.yaml")
TEST_CONTAINER="sarembok-conversation-validation"

cleanup() {
    "${COMPOSE[@]}" rm -sf "$TEST_CONTAINER" >/dev/null 2>&1 || true
    docker rm -f "$TEST_CONTAINER" >/dev/null 2>&1 || true
}
trap cleanup EXIT

cd "$ROOT_DIR/Deployment/cloud"

if [[ ! -f /etc/sarembok/auth_token ]]; then
    echo "FAIL: /etc/sarembok/auth_token is missing" >&2
    exit 1
fi

export SAREMBOK_AUTH_TOKEN="$(sudo cat /etc/sarembok/auth_token)"
if [[ -z "$SAREMBOK_AUTH_TOKEN" ]]; then
    echo "FAIL: SAREMBOK_AUTH_TOKEN is empty" >&2
    exit 1
fi

echo "===== 1. UNIT TESTS ====="
PYTHONPATH=. python3 -m unittest -v test_conversation_runtime.py test_public_session.py

echo "===== 2. PRODUCTION IMAGE BUILD ====="
"${COMPOSE[@]}" build --no-cache sarembok-runtime

echo "===== 3. ISOLATED TEST RUNTIME ====="
"${COMPOSE[@]}" run -d \
    --no-deps \
    --name "$TEST_CONTAINER" \
    -e SAREMBOK_AUTH_TOKEN \
    -e SAREMBOK_MODEL_PROVIDER=test \
    sarembok-runtime \
    python /app/entrypoint.py >/dev/null

for _ in {1..30}; do
    if docker exec "$TEST_CONTAINER" python -c 'import socket; s=socket.create_connection(("127.0.0.1",9000),2); s.close()' >/dev/null 2>&1; then
        break
    fi
    sleep 1
done

sleep 1

echo "===== 4. PUBLIC BROWSER SESSION E2E ====="
docker exec -i "$TEST_CONTAINER" python - <<'PY'
import asyncio
import json
import urllib.request
import websockets

async def main():
    request = urllib.request.Request("http://127.0.0.1:9000/")
    with urllib.request.urlopen(request, timeout=5) as response:
        cookie = response.headers.get("Set-Cookie", "")
        assert "sarembok_session=" in cookie, cookie
        session_cookie = cookie.split(";", 1)[0]

    async with websockets.connect(
        "ws://127.0.0.1:9000",
        additional_headers={
            "Cookie": session_cookie,
            "Origin": "https://sarembok.com",
        },
    ) as ws:
        await ws.send(json.dumps({
            "jsonrpc": "2.0",
            "id": "public-runtime-info",
            "method": "RuntimeInfo",
            "params": {},
        }))
        response = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
        assert not response.get("error"), response
        assert (response.get("result") or {}).get("status") == "ONLINE", response

    print("Public session cookie: PASS")
    print("Trusted origin binding: PASS")
    print("Browser RPC without master token: PASS")

asyncio.run(main())
PY

echo "===== 5. CONVERSATION E2E ====="
docker exec -i -e SAREMBOK_AUTH_TOKEN="$SAREMBOK_AUTH_TOKEN" "$TEST_CONTAINER" python - <<'PY'
import asyncio
import json
import os
import websockets

AGENT = "conversation-validation-agent"
SESSION = "deterministic-validation"

async def rpc(ws, method, params, request_id):
    payload = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": method,
        "params": {
            **params,
            "authToken": os.environ["SAREMBOK_AUTH_TOKEN"],
        },
    }
    await ws.send(json.dumps(payload))
    return json.loads(await asyncio.wait_for(ws.recv(), timeout=30))

async def main():
    async with websockets.connect("ws://127.0.0.1:9000") as ws:
        provider = await rpc(ws, "ModelProviderInfo", {}, "provider")
        assert provider.get("result", {}).get("provider") == "test", provider
        assert provider.get("result", {}).get("configured") is True, provider

        created = await rpc(ws, "CreateAgent", {
            "agentId": AGENT,
            "displayName": "Conversation Validation Agent",
        }, "create-agent")
        assert not created.get("error"), created

        memory = await rpc(ws, "RememberMemory", {
            "agentId": AGENT,
            "content": "Sarembok conversation validation is being performed.",
            "memoryType": "validation",
            "importance": 1.0,
        }, "memory")
        assert not memory.get("error"), memory

        chat = await rpc(ws, "Chat", {
            "agentId": AGENT,
            "content": "Hello Sarembok. Confirm that the conversation runtime works.",
            "sessionId": SESSION,
            "historyLimit": 20,
            "memoryLimit": 10,
        }, "chat")
        assert not chat.get("error"), chat
        result = chat.get("result") or {}
        assert result.get("content"), result
        assert "conversation runtime works" in result["content"], result
        assert result.get("memoryCount", 0) >= 1, result

        history = await rpc(ws, "ListConversation", {
            "agentId": AGENT,
            "limit": 10,
        }, "history")
        assert not history.get("error"), history
        assert (history.get("result") or {}).get("count", 0) >= 2, history

        events = await rpc(ws, "GetEvents", {
            "agentId": AGENT,
            "eventType": "CHAT_COMPLETED",
            "limit": 10,
        }, "events")
        assert not events.get("error"), events
        assert (events.get("result") or {}).get("count", 0) >= 1, events

        print("========================================")
        print(" SAREMBOK CONVERSATION VALIDATION: PASS")
        print("========================================")
        print("Provider abstraction: PASS")
        print("Agent creation:       PASS")
        print("Memory persistence:   PASS")
        print("Chat execution:       PASS")
        print("Conversation history: PASS")
        print("Event emission:       PASS")
        print("External API quota:   NOT USED")
        print("========================================")

asyncio.run(main())
PY

echo "===== 6. TEST CONTAINER LOG ====="
docker logs --tail 60 "$TEST_CONTAINER"

echo "===== VALIDATION COMPLETE ====="
