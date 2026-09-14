#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
URL = "https://sarembok.com/"
OUT = ROOT / ".frontend_acceptance.html"


def fetch(url: str) -> str:
    req = Request(url, headers={"User-Agent": "SarembokVE-Acceptance/2026.09"})
    with urlopen(req, timeout=20) as r:
        body = r.read().decode("utf-8", "replace")
        if r.status != 200:
            raise RuntimeError(f"HTTP {r.status} from {url}")
        return body


def run(name: str, ok: bool, detail: str = "") -> None:
    print(f"{name}: {'PASS' if ok else 'FAIL'}{(' — ' + detail) if detail else ''}")
    if not ok:
        failures.append(name)


failures: list[str] = []

print("===== SAREMBOKVE LIVE FRONTEND ACCEPTANCE =====")
print(f"Target: {URL}")
html = fetch(URL)
OUT.write_text(html, encoding="utf-8")

# Product identity / cleanup.
run("HTTP 200", True)
legacy_identifiers = [
    "activeAstraFrame", "astraVisionMode", "astraScreenStream",
    "captureAstraCameraFrame", "toggleAstraScreenShare", "setAstraActiveFrame",
    "clearAstraFrame", "toggleAstraVisionMode",
    "activeVisionVisionFrame", "toggleVisionVisionMode",
    "captureVisionVisionFrame", "toggleVisionVisionScreenShare",
]
run("legacy vision identifiers absent", not any(x in html for x in legacy_identifiers))

standalone_aria = []
for n, line in enumerate(html.splitlines(), 1):
    low = line.lower()
    if "aria" in low and not re.search(r"aria-[a-z-]+", low):
        standalone_aria.append(n)
run("obsolete voice/product token absent", not standalone_aria, str(standalone_aria[:10]))

run("speech pronunciation normalizer present", "normalizeSarembokSpeech" in html and "Sarembok V E" in html)
run("video layout V2 present", "SAREMBOK_VIDEO_LAYOUT_V2_20260914" in html)
run("table recovery present", "SAREMBOK_COLLAPSED_TABLE_RECOVERY_20260914" in html)
run("chat-session RPCs present", all(x in html for x in ("SaveUserChatSession", "ListUserChatSessions", "DeleteUserChatSession")))
run("text selection enabled", "user-select:text" in html)

# Video layout assertions.
css_requirements = [
    ".srbk-video-card {",
    "max-width: 100%;",
    "min-width: 0;",
    ".srbk-video-player-wrap {",
    "aspect-ratio: 16 / 9;",
    ".srbk-video-iframe {",
    "width: 100%;",
    "height: 100%;",
]
run("video sizing rules present", all(x in html for x in css_requirements))

# Inline onclick function integrity: every JS function directly invoked by an
# HTML onclick handler must exist as a function declaration in this document.
onclick = re.findall(r'onclick=["\']([^"\']+)["\']', html, flags=re.I)
handlers = set()
for expr in onclick:
    for fn in re.findall(r'\b([A-Za-z_$][\w$]*)\s*\(', expr):
        if fn not in {"if", "setTimeout", "setInterval"}:
            handlers.add(fn)
declared = set(re.findall(r'\bfunction\s+([A-Za-z_$][\w$]*)\s*\(', html))
missing_handlers = sorted(h for h in handlers if h not in declared and h not in {
    "open", "focus", "blur", "submit", "click", "play", "stop", "remove", "setAttribute"
})
run("inline handler integrity", not missing_handlers, ", ".join(missing_handlers[:20]))

# Required interaction anchors.
required_anchors = {
    "dialogue input": 'id="directive-input"',
    "execute button": 'id="execute-button"',
    "simple mode": 'onclick="setUiMode(\'simple\')"',
    "cockpit mode": 'onclick="setUiMode(\'cockpit\')"',
    "history drawer": 'id="hud-history-drawer-btn"',
    "features": 'id="hud-features-btn"',
    "new chat": 'id="hud-new-chat-btn"',
    "export": 'id="hud-export-btn"',
    "live 2-way": 'id="hud-live-2way-btn"',
    "fabric": 'id="hud-fabric-btn"',
}
for name, token in required_anchors.items():
    run(f"{name} anchor", token in html)

# Execute button must reach sendDirective(false), not merely exist visually.
execute_area = html[html.find('id="execute-button"') - 1500: html.find('id="execute-button"') + 2000]
run("execute routes to sendDirective", "sendDirective" in execute_area)

# Preserve known deployment repair markers.
for token in (
    "SAREMBOK_PRODUCT_CONSISTENCY_V2_20260914",
    "SAREMBOK_RESPONSE_FORMATTING_20260914",
    "SAREMBOK_IDENTITY_PRONUNCIATION_REPAIR_20260914",
):
    run(f"marker {token}", token in html)

print("\n===== OPTIONAL HEADLESS BROWSER =====")
print("This stage uses Docker so the VPS does not need Node.js installed.")
print("Run: docker run --rm -i --ipc=host mcr.microsoft.com/playwright:v1.55.0-noble node -e '...'")
print("The static acceptance above is authoritative for source integrity; browser interaction still requires a real Chromium run.")

OUT.unlink(missing_ok=True)

if failures:
    print("\nACCEPTANCE RESULT: FAIL")
    print("Failed checks:", ", ".join(failures))
    sys.exit(1)

print("\nACCEPTANCE RESULT: PASS")
