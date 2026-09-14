from pathlib import Path
import re
import subprocess
import sys
import time

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

# Controlled rename of the entire vision identifier family. All dependent
# references are in this frontend file, so this preserves the existing feature.
for old, new in (("Astra", "Vision"), ("astra", "vision")):
    s = s.replace(old, new)

# Remove the browser voice named "aria" from voice heuristics. Do NOT alter
# standard aria-* accessibility attributes.
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

# Browser TTS: visual branding stays SarembokVE; spoken branding becomes
# "Sarembok V E".
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

PATH.write_text(s, encoding="utf-8")

# Structural integrity checks.
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
    r'(?i)\\b(?:astra|activeastra|toggleastra|captureastra|setastra|clearastra)\\w*\\b', s
)
if old_identifier_hits:
    fail("old vision identifiers remain: " + ", ".join(sorted(set(old_identifier_hits))[:20]))

# The only remaining case-insensitive 'aria' matches should be HTML
# accessibility attributes (aria-label, aria-hidden, etc.), not a product or
# voice name.
voice_hits = []
for i, line in enumerate(s.splitlines(), 1):
    low = line.lower()
    if "aria" in low and not re.search(r'aria-[a-z-]+', low):
        voice_hits.append((i, line.strip()))
if voice_hits:
    fail("non-accessibility Aria references remain: " + str(voice_hits[:10]))

# Preserve the important V2 repairs while making the identifier change.
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

print("\n===== FRONTEND IDENTITY REPAIR: PASS =====")
print("Visual product name: SarembokVE")
print("Spoken product name: Sarembok V E")
print("Old Vision/Astra identifiers: removed")
print("Browser voice named Aria: removed from selection heuristics")
print("Standard aria-* accessibility attributes: preserved")

print("\n===== DIFF =====")
run("git", "diff", "--check")
run("git", "diff", "--stat")
run("git", "diff", "--", "frontend/index.html")

# Remove this one-shot repair utility before committing so production history
# contains only the actual frontend fix.
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
live = ROOT / "/tmp/sarembok-live.html"
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

print("\n===== FINAL GIT =====")
run("git", "status", "--short")
run("git", "rev-parse", "--short", "HEAD")
print("\nIDENTITY/PRONUNCIATION REPAIR COMPLETE")
