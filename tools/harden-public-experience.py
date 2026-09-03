from pathlib import Path

server = Path('Deployment/cloud/server.py')
text = server.read_text(encoding='utf-8')

old_public = '''PUBLIC_METHODS = {
    "Health",
    "RuntimeInfo",
    "ListWorkers",
    "ListProjects",
    "ListMemories",
    "ListFiles",
    "ListCheckpoints",
    "ListGovernanceApprovals",
    "ListDigitalHumanSessions",
    "ListEvents",
    "QueryCognitiveGraph",
}
'''
new_public = '''PUBLIC_METHODS = {
    "Health",
    "RuntimeInfo",
}
'''
if old_public not in text:
    raise SystemExit('public method block not found')
text = text.replace(old_public, new_public, 1)

old_injection = '''        elif AUTH_TOKEN:
            token_injection = f'<script>window.__SAREMBOK_DEFAULT_TOKEN__ = "{AUTH_TOKEN}";</script>'
            if "<head>" in html_str:
                html_str = html_str.replace("<head>", f"<head>\\n    {token_injection}", 1)
            else:
                html_str = token_injection + html_str
'''
new_injection = '''        # Never expose SAREMBOK_AUTH_TOKEN to the browser or public HTML.
'''
if old_injection not in text:
    raise SystemExit('token injection block not found')
text = text.replace(old_injection, new_injection, 1)

server.write_text(text, encoding='utf-8')
