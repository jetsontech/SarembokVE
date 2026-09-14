from pathlib import Path
import re

PATH = Path("frontend/index.html")
MARKER = "SAREMBOK_IDENTITY_PRONUNCIATION_REPAIR_20260914"

s = PATH.read_text(encoding="utf-8")
original = s

# Controlled rename of the vision subsystem. All references live in this
# frontend file, so renaming the identifier family together preserves behavior.
for old, new in (("Astra", "Vision"), ("astra", "vision")):
    s = s.replace(old, new)

# Remove the browser voice named "aria" from voice heuristics. This does not
# touch standard accessibility attributes such as aria-label.
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

# Browser TTS pronunciation: visual branding stays SarembokVE, speech becomes
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
        raise SystemExit("PATCH FAILED: speakText anchor not found")
    s = s.replace(anchor, pronunciation + "\n" + anchor, 1)

old = '            const utterance = new SpeechSynthesisUtterance(clean);'
new = '            const utterance = new SpeechSynthesisUtterance(normalizeSarembokSpeech(clean));'
if old not in s:
    raise SystemExit("PATCH FAILED: SpeechSynthesisUtterance anchor not found")
s = s.replace(old, new, 1)

if MARKER not in s:
    style = '<style>\n'
    if style not in s:
        raise SystemExit("PATCH FAILED: style tag not found")
    s = s.replace(style, style + f"        /* {MARKER} */\n", 1)

if s == original:
    raise SystemExit("PATCH FAILED: no changes made")

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
    raise SystemExit("PATCH FAILED: missing required symbols: " + ", ".join(missing))

old_identifier_hits = re.findall(
    r'(?i)\\b(?:astra|activeastra|toggleastra|captureastra|setastra|clearastra)\\w*\\b', s
)
if old_identifier_hits:
    raise SystemExit("PATCH FAILED: old vision identifiers remain: " + ", ".join(sorted(set(old_identifier_hits))[:20]))

PATH.write_text(s, encoding="utf-8")
print("FRONTEND IDENTITY/PRONUNCIATION REPAIR: PASS")
print("Product TTS: SarembokVE -> Sarembok V E")
print("Old vision identifiers: removed")
print("Voice named aria: removed from voice heuristics")
print("aria-* accessibility attributes: preserved")
