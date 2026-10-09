import subprocess
import time
import json
import urllib.request
import asyncio
import os
import sys

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PORT = 9333
PROFILE_DIR = os.path.join(os.environ.get("TEMP", "C:\\Temp"), "chrome_cdp_test")

async def run_test():
    import websockets

    # 1. Start Chrome
    cmd = [
        CHROME_PATH,
        "--headless=new",
        f"--remote-debugging-port={PORT}",
        f"--user-data-dir={PROFILE_DIR}",
        "--disable-gpu",
        "--no-first-run",
        "--no-default-browser-check",
        "https://sarembok.com/"
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"Started Chrome (PID {proc.pid}) on port {PORT}...")

    # Wait for Chrome to be ready
    ws_url = None
    for _ in range(30):
        time.sleep(0.5)
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json") as resp:
                data = json.loads(resp.read().decode())
                for target in data:
                    if target.get("type") == "page" and "webSocketDebuggerUrl" in target:
                        ws_url = target["webSocketDebuggerUrl"]
                        break
                if ws_url:
                    break
        except Exception:
            pass

    if not ws_url:
        print("ERROR: Could not get WebSocket debugger URL from Chrome.")
        proc.terminate()
        return

    print(f"Connecting to CDP: {ws_url}")
    async with websockets.connect(ws_url) as ws:
        msg_id = 0

        async def send_cmd(method, params=None):
            nonlocal msg_id
            msg_id += 1
            payload = {"id": msg_id, "method": method, "params": params or {}}
            await ws.send(json.dumps(payload))
            return msg_id

        # Enable logging and runtime
        await send_cmd("Runtime.enable")
        await send_cmd("Page.enable")
        await send_cmd("Console.enable")

        console_logs = []
        js_exceptions = []

        pending_responses = {}

        # Background listener task
        async def listener():
            try:
                while True:
                    raw = await ws.recv()
                    data = json.loads(raw)
                    msg_resp_id = data.get("id")
                    if msg_resp_id in pending_responses:
                        pending_responses[msg_resp_id].set_result(data)

                    method = data.get("method")
                    params = data.get("params", {})
                    if method == "Console.messageAdded":
                        msg = params.get("message", {})
                        console_logs.append(f"[{msg.get('level')}] {msg.get('text')}")
                    elif method == "Runtime.consoleAPICalled":
                        c_type = params.get("type")
                        args = [str(a.get("value") or a.get("description") or "") for a in params.get("args", [])]
                        console_logs.append(f"[{c_type}] {' '.join(args)}")
                    elif method == "Runtime.exceptionThrown":
                        details = params.get("exceptionDetails", {})
                        exc = details.get("exception", {})
                        text = details.get("text", "") + " " + str(exc.get("description") or exc.get("value") or "")
                        js_exceptions.append(text)
            except asyncio.CancelledError:
                pass
            except Exception as e:
                pass

        listen_task = asyncio.create_task(listener())

        # Wait 4 seconds for page load and initial scripts to run
        print("Waiting for page load and initialization...")
        await asyncio.sleep(4)

        async def eval_js(expr):
            loop = asyncio.get_running_loop()
            fut = loop.create_future()
            req_id = await send_cmd("Runtime.evaluate", {"expression": expr, "returnByValue": True, "awaitPromise": True})
            pending_responses[req_id] = fut
            try:
                resp = await asyncio.wait_for(fut, timeout=10.0)
                val = resp.get("result", {}).get("result", {}).get("value")
                return val
            except Exception as e:
                return f"EVAL_TIMEOUT_OR_ERROR: {e}"
            finally:
                pending_responses.pop(req_id, None)

        print("\n--- INITIAL PAGE STATUS ---")
        title_id = await send_cmd("Runtime.evaluate", {"expression": "document.title", "returnByValue": True})
        
        # Test tab switching and view visibility
        tabs_to_test = ["workspace", "deck", "research", "settings", "dialogue"]
        for tab in tabs_to_test:
            res = await eval_js(f"""
            (() => {{
                if (typeof switchTab !== 'function') return 'switchTab not defined';
                switchTab('{tab}');
                const panel = document.getElementById('view-{tab}');
                const isVis = panel && (panel.classList.contains('active') || panel.style.display !== 'none');
                return {{ tab: '{tab}', panelFound: !!panel, isVisible: isVis }};
            }})()
            """)
            print(f"Tab switch result for {tab}: {res}")
            await asyncio.sleep(0.5)

        # Test settings loading
        print("Testing loadSystemSettings()...")
        settings_res = await eval_js("""
        (() => {
            if (typeof loadSystemSettings !== 'function') return 'loadSystemSettings not defined';
            loadSystemSettings();
            return 'loadSystemSettings invoked successfully';
        })()
        """)
        print(f"loadSystemSettings result: {settings_res}")
        await asyncio.sleep(1)

        # Switch back to dialogue for chat testing
        await eval_js("switchTab('dialogue')")
        await asyncio.sleep(0.5)

        # Test chat directive submission
        print("Testing chat directive submission...")
        chat_eval = await eval_js("""
        (async () => {
            const input = document.getElementById('directive-input');
            if (!input) return { status: 'DIRECTIVE_INPUT_NOT_FOUND' };
            input.value = 'Status test. Confirm system operational in 5 words.';
            input.dispatchEvent(new Event('input', { bubbles: true }));
            if (typeof sendDirective !== 'function') return { status: 'SEND_DIRECTIVE_MISSING' };
            
            try {
                sendDirective(false);
                return { status: 'INVOKED', textSent: input.value };
            } catch (err) {
                return { status: 'ERROR', error: String(err) };
            }
        })()
        """)
        print(f"Chat submission status: {chat_eval}")

        # Wait for AI streaming response in dialogue feed
        print("Waiting 12 seconds for chat stream response...")
        for i in range(12):
            await asyncio.sleep(1)
            feed_status = await eval_js("""
            (() => {
                const bubbles = Array.from(document.querySelectorAll('.srbk-bubble'));
                const texts = bubbles.map(b => {
                    const sender = b.querySelector('.srbk-bubble-sender')?.textContent.trim() || '';
                    const content = b.querySelector('.srbk-content')?.textContent.trim() || '';
                    return sender + ': ' + content;
                }).filter(Boolean);
                return { bubbleCount: bubbles.length, messages: texts };
            })()
            """)
            safe_status = str(feed_status).encode('ascii', errors='replace').decode('ascii')
            print(f"  [T+{i+1}s] {safe_status}")

        # Let any async responses finish
        await asyncio.sleep(2)

        listen_task.cancel()

        print("\n=== BROWSER TEST REPORT ===")
        print(f"Total Console logs: {len(console_logs)}")
        print(f"Total JS Exceptions thrown: {len(js_exceptions)}")

        if js_exceptions:
            print("\n[!] RUNTIME JAVASCRIPT EXCEPTIONS:")
            for exc in js_exceptions:
                print(f"  [-] {exc}")
        else:
            print("\n[OK] ZERO RUNTIME JAVASCRIPT EXCEPTIONS DETECTED!")

        print("\n[+] CONSOLE LOGS:")
        for log in console_logs:
            # sanitize for windows console
            safe_log = log.encode("ascii", errors="replace").decode("ascii")
            print(f"  {safe_log}")

    proc.terminate()
    try:
        proc.wait(timeout=2)
    except Exception:
        proc.kill()
    print("\nBrowser test complete.")

if __name__ == "__main__":
    asyncio.run(run_test())
