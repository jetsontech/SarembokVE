from pathlib import Path

INDEX = Path('/app/frontend/index.html')

text = INDEX.read_text(encoding='utf-8')

# This patch is intentionally small, deterministic, and idempotent.
# The container build must fail if the expected source has drifted rather
# than silently producing a partially patched frontend.
required = [
    'document.querySelectorAll(".view").forEach(v => {',
    'const tab = document.querySelector(`[data-tab="${tabId}"]`);',
    'const url = `${protocol}//${window.location.host}`;',
]

missing = [needle for needle in required if needle not in text]
if missing:
    # Already patched is acceptable; otherwise fail loudly.
    already_patched = (
        'document.querySelectorAll(".view-section").forEach(v => {' in text
        and 'window.location.host}/ws' in text
    )
    if not already_patched:
        raise RuntimeError(
            'Frontend patch refused: expected source pattern(s) not found: '
            + ', '.join(repr(x) for x in missing)
        )
    raise SystemExit(0)

text = text.replace(
    'document.querySelectorAll(".view").forEach(v => {',
    'document.querySelectorAll(".view-section").forEach(v => {'
)

old_tab_block = '''const tab = document.querySelector(`[data-tab="${tabId}"]`);
            if (tab) tab.classList.add("active");'''

new_tab_block = '''document.querySelectorAll(".nav-tab").forEach(t => {
                const handler = t.getAttribute("onclick") || "";
                const selected =
                    handler.includes(`switchTab('${tabId}')`) ||
                    handler.includes(`switchTab("${tabId}")`);
                t.classList.toggle("active", selected);
            });'''

if old_tab_block not in text:
    raise RuntimeError('Frontend patch refused: navigation active-state block not found')

text = text.replace(old_tab_block, new_tab_block)

text = text.replace(
    'const url = `${protocol}//${window.location.host}`;',
    'const url = `${protocol}//${window.location.host}/ws`;'
)

INDEX.write_text(text, encoding='utf-8')
print('Sarembok VE frontend patch applied successfully.')
