#!/usr/bin/env python3
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
URL = "https://sarembok.com/"
BROWSER_TEST = ROOT / "Deployment/cloud/frontend_browser_acceptance_20260914.mjs"
STATIC_OUT = ROOT / ".frontend_acceptance.html"


def fetch(url: str) -> str:
    req = Request(url, headers={"User-Agent": "SarembokVE-Acceptance/2026.09"})
    with urlopen(req, timeout=20) as r:
        body = r.read().decode("utf-8", "replace")
        if r.status != 200:
            raise RuntimeError(f"HTTP {r.status} from {url}")
        return body


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"{name}: {'PASS' if ok else 'FAIL'}{(' — ' + detail) if detail else ''}")
    if not ok:
        failures.append(name)


failures: list[str] = []
print("===== SAREMBOKVE STATIC FRONTEND ACCEPTANCE =====")
print(f"Target: {URL}")
html = fetch(URL)
STATIC_OUT.write_text(html, encoding="utf-8")

legacy_symbols = [
    "activeAstraFrame", "astraVisionMode", "astraScreenStream",
    "captureAstraCameraFrame", "toggleAstraScreenShare", "setAstraActiveFrame",
    "clearAstraFrame", "toggleAstraVisionMode", "activeVisionVisionFrame",
    "toggleVisionVisionMode", "captureVisionVisionFrame", "toggleVisionVisionScreenShare",
]
check("HTTP 200", True)
check("legacy vision identifiers absent", not any(x in html for x in legacy_symbols))

# Ignore standard accessibility tokens such as aria-label; reject bare legacy product/voice token.
aria_stripped = re.sub(r"\baria-[a-z-]+\b", "", html, flags=re.I)
check("obsolete Aria token absent", not re.search(r"\baria\b", aria_stripped, re.I))
check("SarembokVE speech normalization present", "normalizeSarembokSpeech" in html and "Sarembok V E" in html)
check("video layout V2 present", "SAREMBOK_VIDEO_LAYOUT_V2_20260914" in html)
check("table recovery present", "SAREMBOK_COLLAPSED_TABLE_RECOVERY_20260914" in html)
check("session RPCs present", all(x in html for x in ("SaveUserChatSession", "ListUserChatSessions", "DeleteUserChatSession")))
check("selection enabled", "user-select:text" in html)

# Ensure media sizing rules are not merely marker text.
css_requirements = [
    ".srbk-video-card {", "max-width: 100%;", "min-width: 0;",
    ".srbk-video-player-wrap {", "aspect-ratio: 16 / 9;",
    ".srbk-video-iframe {", "width: 100%;", "height: 100%;",
]
check("video sizing rules present", all(x in html for x in css_requirements))

# Inline onclick integrity. Ignore property methods such as classList.add();
# only identify bare callable names that are candidates for global handlers.
onclick = re.findall(r'onclick=["\']([^"\']+)["\']', html, flags=re.I)
handlers = set()
for expr in onclick:
    for fn in re.findall(r'(?<![.\w$])([A-Za-z_$][\w$]*)\s*\(', expr):
        if fn not in {"if", "setTimeout", "setInterval", "alert", "confirm", "prompt"}:
            handlers.add(fn)
declared = set(re.findall(r'\bfunction\s+([A-Za-z_$][\w$]*)\s*\(', html))
missing = sorted(h for h in handlers if h not in declared)
check("inline handler integrity", not missing, ", ".join(missing[:20]))

required_ids = [
    "directive-input", "execute-button", "mode-btn-simple", "mode-btn-cockpit",
    "hud-history-drawer-btn", "hud-features-btn", "hud-new-chat-btn",
    "hud-export-btn", "hud-live-2way-btn", "hud-fabric-btn",
]
for element_id in required_ids:
    check(f"DOM anchor #{element_id}", f'id="{element_id}"' in html)

# Execute control must actually call sendDirective.
exec_pos = html.find('id="execute-button"')
exec_area = html[max(0, exec_pos - 1800):exec_pos + 2200] if exec_pos >= 0 else ""
check("execute control routes to sendDirective", "sendDirective" in exec_area)

for token in (
    "SAREMBOK_PRODUCT_CONSISTENCY_V2_20260914",
    "SAREMBOK_RESPONSE_FORMATTING_20260914",
    "SAREMBOK_IDENTITY_PRONUNCIATION_REPAIR_20260914",
):
    check(f"marker {token}", token in html)

STATIC_OUT.unlink(missing_ok=True)

if failures:
    print("\nSTATIC ACCEPTANCE: FAIL")
    print("Failed checks:", ", ".join(failures))
    sys.exit(1)

print("\nSTATIC ACCEPTANCE: PASS")
print("\n===== REAL CHROMIUM ACCEPTANCE =====")
print("Launching Playwright inside Docker; Node.js is not required on the VPS host.")

cmd = [
    "docker", "run", "--rm", "--ipc=host",
    "-v", f"{ROOT}:/work", "-w", "/work",
    "mcr.microsoft.com/playwright:latest",
    "node", str(BROWSER_TEST.relative_to(ROOT)), URL,
]
print("$", " ".join(cmd))
result = subprocess.run(cmd, cwd=ROOT, text=True)
sys.exit(result.returncode)
