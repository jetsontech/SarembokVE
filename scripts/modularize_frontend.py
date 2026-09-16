from pathlib import Path

p = Path('frontend/index.html')
s = p.read_text(encoding='utf-8')
css = '<link rel="stylesheet" href="/frontend/css/sarembok-simplified.css">'
js = '<script src="/frontend/js/sarembok-simplified.js" defer></script>'
if css not in s:
    marker='</head>'
    if marker not in s: raise SystemExit('Missing </head>')
    s=s.replace(marker, css+'\n'+marker, 1)
if js not in s:
    marker='</body>'
    if marker not in s: raise SystemExit('Missing </body>')
    s=s.replace(marker, js+'\n'+marker, 1)
p.write_text(s,encoding='utf-8')
print('frontend/index.html modular presentation hooks installed')
