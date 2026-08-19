from pathlib import Path

INDEX = Path('/app/frontend/index.html')

text = INDEX.read_text(encoding='utf-8')

# Deterministic, idempotent production patch.
# The frontend source is the source of truth: fail loudly if the expected
# navigation or WebSocket structure has drifted instead of guessing.
if 'document.querySelectorAll(\'.view-section\').forEach(s => s.classList.remove(\'active\'));' not in text:
    raise RuntimeError(
        'Frontend patch refused: expected current view-section navigation source not found'
    )

# Production WebSocket traffic must terminate at the /ws reverse-proxy route.
if 'const url = `${protocol}//${host}`;' in text:
    text = text.replace(
        'const url = `${protocol}//${host}`;',
        'const url = `${protocol}//${host}/ws`;'
    )
elif 'const url = `${protocol}//${host}/ws`;' in text:
    pass
else:
    raise RuntimeError(
        'Frontend patch refused: expected WebSocket URL construction not found'
    )

INDEX.write_text(text, encoding='utf-8')
print('Sarembok VE frontend patch applied successfully.')
