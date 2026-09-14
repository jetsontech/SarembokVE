from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "frontend/index.html"
MARKER = "SAREMBOK_IDENTITY_PRONUNCIATION_REPAIR_20260914"

def run(*args, check=True):
    print("$", " ".join(args))
    return subprocess.run(args, cwd=ROOT, check=check, text=True)

def fail(message):
    print("PATCH FAILED:", message, file=sys.stderr)
    raise SystemExit(1)

run("git", "status", "--short")
status = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, text=True, capture_output=True, check=True).stdout.strip()
if status:
    fail("working tree is not clean; refusing to modify unrelated work")

s = PATH.read_text(encoding="utf-8")
original = s

# Rename only the actual vision subsystem identifiers. Do not globally replace
# the word 'Astra', because compound names such as AstraVision would otherwise
# become VisionVision.
identifier_replacements = [
    ("activeAstraFrame", "activeVisionFrame"),
    ("astraVisionMode", "visionMode"),
    ("astraScreenStream", "visionScreenStream"),
    ("captureAstraCameraFrame", "captureVisionCameraFrame"),
    ("toggleAstraScreenShare", "toggleVisionScreenShare"),
    ("setAstraActiveFrame", "setVisionActiveFrame"),
    ("clearAstraFrame", "clearVisionFrame"),
    ("toggleAstraVisionMode", "toggleVisionMode"),
    ("astra-frame-preview-bar", "vision-frame-preview-bar"),
    ("astra-frame-thumb", "vision-frame-thumb"),
    ("astra-frame-label", "vision-frame-label"),
    ("astra-vision-toggle-btn", "vision-toggle-btn"),
]
for old, new in identifier_replacements:
    s = s.replace(old, new)

# Visible legacy product terminology: preserve semantics, remove obsolete brand.
visible_replacements = [
    ("Astra Vision Eye (Camera &amp; Screen)", "Live Vision (Camera &amp; Screen)"),
    ("Astra Vision Eye", "Live Vision"),
    ("Astra Camera Eye", "Camera Vision"),
    ("Astra Screen Eye", "Screen Vision"),
    ("Astra perception frame", "Vision perception frame"),
    ("Toggle Astra Multimodal Eye", "Toggle live multimodal vision"),
    ("Astra Multimodal Eye", "Live Multimodal Vision"),
    ("ASTRA MULTIMODAL VISION", "LIVE MULTIMODAL VISION"),
    ("ASTRA MULTIMODAL EYE", "LIVE MULTIMODAL VISION"),
    ("ASTRA EYE VIEWPORT ATTACHED", "LIVE VISION VIEWPORT ATTACHED"),
    ("ASTRA EYE: OFF", "VISION: OFF"),
    ("ASTRA EYE: ON", "VISION: ON"),
    ("ASTRA EYE OFF", "VISION OFF"),
    ("ASTRA MULTIMODAL EYE ACTIVE", "LIVE MULTIMODAL VISION ACTIVE"),
    ("ASTRA SCREEN EYE ACTIVE", "LIVE SCREEN VISION ACTIVE"),
    ("ASTRA SCREEN SHARE STOPPED", "SCREEN SHARE STOPPED"),
    ("ASTRA CAMERA VIEWPORT CAPTURED", "CAMERA VIEWPORT CAPTURED"),
    ("Astra camera &amp; screen perception", "live camera &amp; screen perception"),
    ("Astra camera & screen perception", "live camera & screen perception"),
]
for old, new in visible_replacements:
    s = s.replace(old, new)

# Remove the browser voice named 'aria' from selection heuristics. Do not touch
# accessibility attributes such as aria-label or aria-hidden.
s = s.replace('"jenny", "aria", "samantha", "victoria", "ava"',
              '"jenny", "samantha", "victoria", "ava"')
s = s.replace(
    'return (n.includes("aria") || n.includes("ava") || n.includes("victoria")) && getVoiceFidelityScore(v) > 0;',
    'return (n.includes("ava") || n.includes("victoria")) && getVoiceFidelityScore(v) > 0;'
)
s = s.replace(
    'const vegaPriority = ["jenny", "shimmer", "aria", "google us english", "natural", "neural", "samantha", "ava"];',
    'const vegaPriority = ["jenny", "shimmer", "google us english", "natural", "neural", "samantha", "ava"];'
)

# Browser TTS: on-screen branding remains SarembokVE; speech becomes
# 'Sarembok V E'.
pronunciation = '''
        // SAREMBOK_PRODUCT_PRONUNCIATION_20260914
        function normalizeSarembokSpeech(text) {
            return String(text || "")
                .replace(/\\bSarembok\\s*VE\\b/gi, "Sarembok V E")
                .replace(/\\bSarembokVE\\b/gi, "Sarembok V E");
        }
'''
if "SAREMBOK_PRODUCT_PRONUNCIATION_20260914" not in s:
    anchor = '        function speakText(btnOrText) {'
    if anchor not in s:
        fail("speakText anchor not found")
    s = s.replace(anchor, pronunciation + "\n" + anchor, 1)

old = '            const utterance = new SpeechSynthesisUtterance(clean);'
new = '            const utterance = new SpeechSynthesisUtterance(normalizeSarembokSpeech(clean));'
if old in s:
    s = s.replace(old, new, 1)
elif new not in s:
    fail("SpeechSynthesisUtterance anchor not found")

if MARKER not in s:
    style = '<style>\n'
    if style not in s:
        fail("style tag not found")
    s = s.replace(style, style + f"        /* {MARKER} */\n", 1)

if s == original:
    fail("frontend unchanged")

# Structural integrity checks before writing/committing.
required = [
    "captureVisionCameraFrame",
    "toggleVisionScreenShare",
    "setVisionActiveFrame",
    "clearVisionFrame",
    "toggleVisionMode",
    "activeVisionFrame",
    "visionMode",
    "visionScreenStream",
    "normalizeSarembokSpeech",
    "SAREMBOK_PRODUCT_PRONUNCIATION_20260914",
    MARKER,
]
missing = [x for x in required if x not in s]
if missing:
    fail("missing required symbols: " + ", ".join(missing))

old_identifier_hits = re.findall(
    r'(?i)\b(?:astra|activeastra|toggleastra|captureastra|setastra|clearastra)\w*\b', s
)
if old_identifier_hits:
    fail("old vision identifiers remain: " + ", ".join(sorted(set(old_identifier_hits))[:20]))

# No standalone obsolete voice/product token may remain. Standard aria-* HTML
# accessibility attributes are intentionally exempted.
for i, line in enumerate(s.splitlines(), 1):
    low = line.lower()
    if "aria" in low and not re.search(r'aria-[a-z-]+', low):
        fail(f"non-accessibility Aria reference remains on line {i}: {line.strip()}")

# Ensure all previous production repairs remain present.
for token in (
    "SAREMBOK_VIDEO_LAYOUT_V2_20260914",
    "SAREMBOK_COLLAPSED_TABLE_RECOVERY_20260914",
    "SAREMBOK_PRODUCT_CONSISTENCY_V2_20260914",
    "SaveUserChatSession",
    "ListUserChatSessions",
    "DeleteUserChatSession",
):
    if token not in s:
        fail("previous production repair missing: " + token)

PATH.write_text(s, encoding="utf-8")
print("FRONTEND IDENTITY/PRONUNCIATION REPAIR: PASS")
print("Visual product name: SarembokVE")
print("Spoken product name: Sarembok V E")
print("Old vision identifiers: removed")
print("Browser voice named aria: removed")
print("aria-* accessibility attributes: preserved")

run("git", "diff", "--check")
run("git", "diff", "--stat")

# Remove this one-shot repair utility before committing; only the actual
# frontend change belongs in the production commit.
run("git", "rm", "--", str(Path(__file__).relative_to(ROOT)))
run("git", "add", "frontend/index.html")
run("git", "diff", "--cached", "--check")
run("git", "status", "--short")
run("git", "commit", "-m", "fix: standardize vision identity and SarembokVE pronunciation")
run("git", "push", "origin", "main")

print("\n===== DEPLOY =====")
run(
    "docker", "compose",
    "-f", "Deployment/cloud/compose.yaml",
    "-f", "Deployment/cloud/compose.production.yaml",
    "up", "-d", "--build", "sarembok-runtime", "sarembok-edge",
)

print("\n===== HEALTH =====")
run("docker", "exec", "sarembok-runtime", "python", "-c",
    'import urllib.request; print(urllib.request.urlopen("http://127.0.0.1:9000/health", timeout=5).read().decode().strip())')
run("docker", "exec", "sarembok-edge", "wget", "-qO-", "http://sarembok-runtime:9000/health")
run("curl", "-fsS", "--max-time", "15", "https://sarembok.com/health")

print("\n===== LIVE FRONTEND VERIFY =====")
live = ROOT / "sarembok-live.html"
run("curl", "-fsS", "--max-time", "15", "https://sarembok.com/", "-o", str(live))
ls = live.read_text(encoding="utf-8")
checks = {
    "identity marker": MARKER in ls,
    "pronunciation function": "normalizeSarembokSpeech" in ls,
    "spoken Sarembok V E": "Sarembok V E" in ls,
    "vision layout V2": "SAREMBOK_VIDEO_LAYOUT_V2_20260914" in ls,
    "table recovery": "SAREMBOK_COLLAPSED_TABLE_RECOVERY_20260914" in ls,
    "session save RPC": "SaveUserChatSession" in ls,
    "session list RPC": "ListUserChatSessions" in ls,
    "session delete RPC": "DeleteUserChatSession" in ls,
    "text selection": "user-select:text" in ls,
}
for k, ok in checks.items():
    print(f"{k}: {'PASS' if ok else 'FAIL'}")
if not all(checks.values()):
    fail("live frontend verification failed")

# Cleanup verification artifact and verify a clean worktree.
Path("sarembok-live.html").unlink(missing_ok=True)
run("git", "status", "--short")
run("git", "rev-parse", "--short", "HEAD")
print("IDENTITY/PRONUNCIATION REPAIR COMPLETE")
