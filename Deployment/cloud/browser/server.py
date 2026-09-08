import base64
import ipaddress
import json
import os
import socket
import time
import urllib.parse
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
