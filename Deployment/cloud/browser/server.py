import base64
import ipaddress
import json
import os
import socket
import time
import urllib.parse
import threading
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

from playwright.sync_api import sync_playwright

PORT = int(os.getenv("SAREMBOK_BROWSER_PORT", "9100"))
MAX_TEXT = max(1000, int(os.getenv("SAREMBOK_BROWSER_MAX_TEXT", "120000")))
NAVIGATION_TIMEOUT_MS = max(
    1000,
    int(os.getenv("SAREMBOK_BROWSER_NAVIGATION_TIMEOUT_MS", "15000")),
)
USER_AGENT = "SarembokBrowser/2.0 (+https://sarembok.com)"


def allowed_hosts() -> list[str]:
    raw = os.getenv("SAREMBOK_BROWSER_ALLOWED_HOSTS", "*")
    return [item.strip().lower() for item in raw.split(",") if item.strip()]


def host_allowed(host: str) -> bool:
    host = host.lower().rstrip(".")
    rules = allowed_hosts()
    if "*" in rules:
        return True
    for rule in rules:
        rule = rule.rstrip(".")
        if host == rule:
            return True
        if rule.startswith("*.") and host.endswith(rule[1:]):
            return True
    return False


def resolve_public_addresses(host: str) -> list[str]:
    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ValueError("dns_resolution_failed") from exc

    addresses = sorted({info[4][0] for info in infos})
    if not addresses:
        raise ValueError("dns_resolution_failed")

    for raw_address in addresses:
        address = ipaddress.ip_address(raw_address)
        if (
            address.is_private
            or address.is_loopback
            or address.is_link_local
            or address.is_multicast
            or address.is_reserved
            or address.is_unspecified
        ):
            raise PermissionError("private_or_reserved_network_target")

    return addresses


def validate_url(url: str) -> str:
    parsed = urllib.parse.urlparse(str(url).strip())
    if parsed.scheme not in {"http", "https"}:
        raise PermissionError("only_http_https_urls_are_supported")
    if not parsed.hostname:
        raise ValueError("hostname_required")

    host = parsed.hostname.lower().rstrip(".")
    if not host_allowed(host):
        raise PermissionError("origin_not_allowed")

    resolve_public_addresses(host)
    return urllib.parse.urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path or "/",
            "",
            parsed.query,
            "",
        )
    )


def clean_text(text: str) -> str:
    return " ".join(str(text or "").split())[:MAX_TEXT]


class BrowserRuntime:
    def __init__(self) -> None:
        self.started_at = time.time()
        self.playwright = None
        self.browser = None

    def start(self) -> None:
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=True,
            args=[
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ],
        )

    def stop(self) -> None:
        with self.sessions_lock:
            sessions = list(self.sessions.values())
            self.sessions.clear()
        for item in sessions:
            try: item["context"].close()
            except Exception: pass
        if self.browser is not None:
            self.browser.close()
            self.browser = None
        if self.playwright is not None:
            self.playwright.stop()
            self.playwright = None

    def health(self) -> dict[str, Any]:
        browser_online = self.browser is not None
        return {
            "status": "ONLINE" if browser_online else "UNAVAILABLE",
            "service": "sarembok-browser",
            "engine": "chromium",
            "automation": "playwright",
            "capabilities": ["navigate", "render", "screenshot"],
            "uptimeSeconds": int(time.time() - self.started_at),
            "allowedHosts": allowed_hosts(),
            "browserProcess": "ONLINE" if browser_online else "OFFLINE",
        }

    def _create_context(self, width: int = 1280, height: int = 800):
        if self.browser is None:
            raise RuntimeError("browser_service_unavailable")

        context = self.browser.new_context(
            user_agent=USER_AGENT,
            viewport={"width": width, "height": height},
            java_script_enabled=True,
            service_workers="block",
        )

        def route_handler(route: Any) -> None:
            request_url = route.request.url
            try:
                validate_url(request_url)
            except Exception:
                route.abort()
                return
            route.continue_()

        context.route("**/*", route_handler)
        return context

    def _cleanup_sessions(self) -> None:
        cutoff = time.time() - self.session_ttl_seconds
        with self.sessions_lock:
            stale = [sid for sid, item in self.sessions.items() if float(item.get("last_used", 0)) < cutoff]
            for sid in stale:
                item = self.sessions.pop(sid, None)
                if item:
                    try: item["context"].close()
                    except Exception: pass

    def open_session(self, session_id: str = "") -> dict[str, Any]:
        self._cleanup_sessions()
        sid = str(session_id or "").strip() or f"browser-{uuid.uuid4().hex[:12]}"
        with self.sessions_lock:
            item = self.sessions.get(sid)
            if item:
                item["last_used"] = time.time()
                pages = list(item["context"].pages)
                return {"ok": True, "created": False, "sessionId": sid, "pageCount": len(pages), "activePage": int(item.get("active_page", 0)), "url": pages[int(item.get("active_page", 0))].url if pages else "about:blank"}
            context = self._create_context()
            context.new_page()
            self.sessions[sid] = {"context": context, "active_page": 0, "created_at": time.time(), "last_used": time.time()}
            return {"ok": True, "created": True, "sessionId": sid, "pageCount": 1, "activePage": 0, "url": "about:blank"}

    def close_session(self, session_id: str) -> dict[str, Any]:
        sid = str(session_id or "").strip()
        with self.sessions_lock: item = self.sessions.pop(sid, None)
        if item:
            try: item["context"].close()
            except Exception: pass
        return {"ok": True, "sessionId": sid, "closed": bool(item)}

    def _get_session(self, session_id: str) -> tuple[str, dict[str, Any]]:
        self._cleanup_sessions()
        sid = str(session_id or "").strip()
        if not sid: raise ValueError("session_id_required")
        with self.sessions_lock:
            item = self.sessions.get(sid)
            if not item: raise ValueError("browser_session_not_found")
            item["last_used"] = time.time()
            return sid, item
    @staticmethod
    def _target_locator(page: Any, request: dict[str, Any]):
        selector = str(request.get("selector") or "").strip()
        text = str(request.get("text") or "").strip()
        role = str(request.get("role") or "").strip()
        name = str(request.get("name") or "").strip()
        exact = bool(request.get("exact", True))
        if selector: return page.locator(selector)
        if role: return page.get_by_role(role, name=name or None, exact=exact)
        if text: return page.get_by_text(text, exact=exact)
        raise ValueError("selector_or_text_or_role_required")

    def inspect_session(self, session_id: str, include_text: bool = True) -> dict[str, Any]:
        sid, item = self._get_session(session_id)
        with self.sessions_lock:
            context = item["context"]
            pages = list(context.pages)
            if not pages:
                pages = [context.new_page()]
                item["active_page"] = 0
            idx = min(max(int(item.get("active_page", 0)), 0), len(pages) - 1)
            page = pages[idx]
            elements = page.locator("a,button,input,textarea,select,[role='button'],[role='link']").evaluate_all(
                "els => els.slice(0,120).map((e,i)=>({index:i,tag:e.tagName.toLowerCase(),type:e.getAttribute('type')||'',role:e.getAttribute('role')||'',text:(e.innerText||e.getAttribute('aria-label')||e.getAttribute('placeholder')||'').trim().slice(0,180),name:e.getAttribute('name')||'',id:e.id||'',placeholder:e.getAttribute('placeholder')||'',href:e.getAttribute('href')||'',disabled:!!e.disabled}))"
            )
            body = ""
            if include_text and page.url not in ("", "about:blank"):
                try: body = clean_text(page.locator("body").inner_text())
                except Exception: body = ""
            return {"ok":True,"sessionId":sid,"pageCount":len(pages),"activePage":idx,"url":page.url,"title":page.title() if page.url not in ("", "about:blank") else "","interactiveElements":elements,"text":body,"verified":True}

    def action(self, request: dict[str, Any]) -> dict[str, Any]:
        sid, item = self._get_session(str(request.get("sessionId") or ""))
        context = item["context"]
        action = str(request.get("action") or "").strip().lower()
        if request.get("pageIndex") is not None:
            idx = int(request.get("pageIndex")); pages=list(context.pages)
            if idx < 0 or idx >= len(pages): raise ValueError("page_index_out_of_range")
            item["active_page"] = idx
        pages=list(context.pages)
        if not pages: page=context.new_page(); item["active_page"]=0
        else: page=pages[min(max(int(item.get("active_page",0)),0),len(pages)-1)]
        destructive = bool(request.get("destructive") or request.get("confirmRequired"))
        if destructive and not bool(request.get("confirm")):
            return {"ok":False,"requiresConfirmation":True,"error":"explicit_confirmation_required_for_high_impact_action",**self.inspect_session(sid, include_text=False)}
        started=time.perf_counter()
        if action == "navigate":
            url=validate_url(str(request.get("url") or "")); resp=page.goto(url,wait_until="domcontentloaded",timeout=NAVIGATION_TIMEOUT_MS); result={"status":int(resp.status) if resp else None,"requestedUrl":url,"url":page.url}
        elif action == "new_tab":
            new_page=context.new_page(); url=str(request.get("url") or "").strip()
            if url: url=validate_url(url); resp=new_page.goto(url,wait_until="domcontentloaded",timeout=NAVIGATION_TIMEOUT_MS); result={"pageIndex":len(list(context.pages))-1,"status":int(resp.status) if resp else None,"requestedUrl":url,"url":new_page.url}
            else: result={"pageIndex":len(list(context.pages))-1,"url":new_page.url}
            item["active_page"]=result["pageIndex"]; page=new_page
        elif action in {"click","fill","type","select","hover","press"}:
            loc=self._target_locator(page,request).first; timeout=max(1000,min(15000,int(request.get("timeoutMs",NAVIGATION_TIMEOUT_MS))))
            if action=="click": loc.click(timeout=timeout)
            elif action=="fill": loc.fill(str(request.get("value") or ""),timeout=timeout)
            elif action=="type": loc.press_sequentially(str(request.get("value") or ""),delay=max(0,min(150,int(request.get("delayMs",0)))),timeout=timeout)
            elif action=="select":
                if request.get("value") is not None: loc.select_option(str(request.get("value")),timeout=timeout)
                elif request.get("label") is not None: loc.select_option(label=str(request.get("label")),timeout=timeout)
                else: raise ValueError("select_requires_value_or_label")
            elif action=="hover": loc.hover(timeout=timeout)
            else: loc.press(str(request.get("key") or "Enter"),timeout=timeout)
            result={"action":action,"targeted":True}
        elif action=="scroll": page.mouse.wheel(int(request.get("dx",0)),int(request.get("dy",700))); result={"action":"scroll"}
        elif action=="wait": ms=max(0,min(15000,int(request.get("ms",500)))); page.wait_for_timeout(ms); result={"action":"wait","ms":ms}
        elif action=="back": resp=page.go_back(wait_until="domcontentloaded",timeout=NAVIGATION_TIMEOUT_MS); result={"action":"back","url":page.url,"status":int(resp.status) if resp else None}
        elif action=="forward": resp=page.go_forward(wait_until="domcontentloaded",timeout=NAVIGATION_TIMEOUT_MS); result={"action":"forward","url":page.url,"status":int(resp.status) if resp else None}
        elif action=="extract": sel=str(request.get("selector") or "body"); result={"action":"extract","selector":sel,"text":clean_text(page.locator(sel).inner_text())}
        elif action=="screenshot":
            fmt="jpeg" if str(request.get("format","png")).lower() in {"jpg","jpeg"} else "png"; shot=page.screenshot(full_page=bool(request.get("fullPage",False)),type=fmt); result={"action":"screenshot","format":fmt,"image":f"data:image/{fmt};base64,{base64.b64encode(shot).decode('ascii')}"}
        elif action in {"inspect","state"}: return self.inspect_session(sid)
        elif action=="close": return self.close_session(sid)
        else: raise ValueError(f"unsupported_browser_action:{action}")
        return {"ok":True,"action":action,"result":result,"state":self.inspect_session(sid,include_text=bool(request.get("includeText",True))),"latencyMs":round((time.perf_counter()-started)*1000,2),"verified":True}
    def navigate(self, url: str) -> dict[str, Any]:
        target = validate_url(url)
        started = time.perf_counter()
        context = self._create_context()

        try:
            page = context.new_page()
            response = page.goto(
                target,
                wait_until="domcontentloaded",
                timeout=NAVIGATION_TIMEOUT_MS,
            )
            text = clean_text(page.locator("body").inner_text())

            return {
                "url": page.url,
                "requestedUrl": target,
                "title": page.title(),
                "status": int(response.status) if response is not None else None,
                "text": text,
                "textBytes": len(text.encode("utf-8")),
                "engine": "chromium",
                "automation": "playwright",
                "latencyMs": round((time.perf_counter() - started) * 1000, 2),
                "verified": True,
            }
        finally:
            context.close()

    def screenshot(
        self,
        url: str,
        full_page: bool = True,
        width: int = 1280,
        height: int = 800,
        image_format: str = "png",
    ) -> dict[str, Any]:
        target = validate_url(url)
        started = time.perf_counter()
        context = self._create_context(width=width, height=height)

        try:
            page = context.new_page()
            response = page.goto(
                target,
                wait_until="networkidle" if not full_page else "domcontentloaded",
                timeout=NAVIGATION_TIMEOUT_MS,
            )
            title = page.title()
            text = clean_text(page.locator("body").inner_text())

            fmt = "jpeg" if image_format.lower() in ("jpeg", "jpg") else "png"
            shot_bytes = page.screenshot(
                full_page=bool(full_page),
                type=fmt,
            )
            b64_img = base64.b64encode(shot_bytes).decode("ascii")
            data_uri = f"data:image/{fmt};base64,{b64_img}"

            return {
                "url": page.url,
                "requestedUrl": target,
                "title": title,
                "status": int(response.status) if response is not None else None,
                "screenshot": data_uri,
                "imageBytes": len(shot_bytes),
                "fullPage": full_page,
                "text": text,
                "engine": "chromium",
                "automation": "playwright",
                "latencyMs": round((time.perf_counter() - started) * 1000, 2),
                "verified": True,
            }
        finally:
            context.close()

    def render(
        self,
        url: str,
        width: int = 1280,
        height: int = 800,
    ) -> dict[str, Any]:
        target = validate_url(url)
        started = time.perf_counter()
        context = self._create_context(width=width, height=height)

        try:
            page = context.new_page()
            response = page.goto(
                target,
                wait_until="domcontentloaded",
                timeout=NAVIGATION_TIMEOUT_MS,
            )
            title = page.title()
            html_content = page.content()
            text = clean_text(page.locator("body").inner_text())

            return {
                "url": page.url,
                "requestedUrl": target,
                "title": title,
                "status": int(response.status) if response is not None else None,
                "html": html_content[:500000],
                "htmlBytes": len(html_content.encode("utf-8")),
                "text": text,
                "engine": "chromium",
                "automation": "playwright",
                "latencyMs": round((time.perf_counter() - started) * 1000, 2),
                "verified": True,
            }
        finally:
            context.close()


BROWSER = BrowserRuntime()


class Handler(BaseHTTPRequestHandler):
    server_version = "SarembokBrowser/2.0"

    def _send(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send(200, BROWSER.health())
            return
        self._send(404, {"error": "not_found"})

    def do_POST(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 65536:
                raise ValueError("invalid_request_size")

            raw = self.rfile.read(length)
            request = json.loads(raw.decode("utf-8"))
            url = str(request.get("url") or "")

            if self.path == "/navigate":
                result = BROWSER.navigate(url)
                self._send(200, {"ok": True, **result})
            elif self.path in ("/screenshot", "/capture"):
                full_page = bool(request.get("full_page", True))
                width = int(request.get("width", 1280))
                height = int(request.get("height", 800))
                fmt = str(request.get("format", "png"))
                result = BROWSER.screenshot(
                    url,
                    full_page=full_page,
                    width=width,
                    height=height,
                    image_format=fmt,
                )
                self._send(200, {"ok": True, **result})
            elif self.path == "/render":
                width = int(request.get("width", 1280))
                height = int(request.get("height", 800))
                result = BROWSER.render(url, width=width, height=height)
                self._send(200, {"ok": True, **result})
            else:
                self._send(404, {"error": "not_found"})

        except PermissionError as exc:
            self._send(403, {"ok": False, "error": str(exc)})
        except Exception as exc:
            self._send(502, {"ok": False, "error": type(exc).__name__, "detail": str(exc)})

    def log_message(self, format: str, *args: Any) -> None:
        return


def main() -> None:
    BROWSER.start()
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    try:
        server.serve_forever()
    finally:
        server.server_close()
        BROWSER.stop()


if __name__ == "__main__":
    main()
