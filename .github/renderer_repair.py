from pathlib import Path

p = Path('frontend/index.html')
s = p.read_text(encoding='utf-8')
marker = 'SAREMBOK_RENDERER_NORMALIZATION_20260914'
if marker in s:
    print('already repaired')
    raise SystemExit(0)
needle = 'let s = String(text);'
if s.count(needle) != 1:
    raise SystemExit(f'expected one renderer anchor, found {s.count(needle)}')
replacement = r'''let s = String(text);

            /* SAREMBOK_RENDERER_NORMALIZATION_20260914 */
            /* Normalize provider-escaped Markdown before the existing rich renderer. */
            s = s.replace(/\\n/g, "\n");
            s = s.replace(/\\([*_`#|])/g, "$1");
            s = s.replace(/([.!?])\s+-\s+(?=\*\*|[A-Za-z])/g, "$1\n- ");
            s = s.replace(/\s+(?=\d+\.\s+\*\*)/g, "\n");'''
s = s.replace(needle, replacement, 1)
css = r'''\n        /* SAREMBOK_RESPONSE_FORMATTING_20260914 */
        .srbk-table-wrap { width:100%; overflow-x:auto; margin:14px 0; border-radius:8px; }
        .srbk-table-wrap table { width:100%; border-collapse:collapse; table-layout:auto; }
        .srbk-table-wrap th, .srbk-table-wrap td { padding:9px 11px; border:1px solid rgba(0,240,255,.12); text-align:left; vertical-align:top; line-height:1.5; }
        .srbk-table-wrap th { background:rgba(0,240,255,.07); color:#fff; font-weight:700; }
        .srbk-table-wrap td { color:#dbe4f0; }
        .srbk-bubble, .srbk-bubble * { user-select:text !important; -webkit-user-select:text !important; }
        '''
if 'SAREMBOK_RESPONSE_FORMATTING_20260914' not in s:
    s = s.replace('</style>', css + '\n    </style>', 1)
p.write_text(s, encoding='utf-8')
print('patched', p)
