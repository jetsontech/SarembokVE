FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SAREMBOK_PORT=9000 \
    SAREMBOK_DB_PATH=/data/sarembok_cloud.db

WORKDIR /app

COPY Runtime/requirements.txt /app/Runtime/requirements.txt
RUN pip install --no-cache-dir -r /app/Runtime/requirements.txt \
    && rm -rf /root/.cache

COPY Runtime /app/Runtime
COPY Deployment/cloud/*.py /app/
COPY Deployment/cloud /app/Deployment/cloud
COPY frontend /app/frontend

# Additive production UI layer. The authoritative frontend remains frontend/index.html;
# these assets provide the live capability fabric, wider response surface, and a
# defensive text-selection policy without duplicating the dialogue dispatcher.
RUN python - <<'PY'
from pathlib import Path
index = Path('/app/frontend/index.html')
text = index.read_text(encoding='utf-8')
css = '<link rel="stylesheet" href="/sarembok-capability-fabric.css">'
js = '<script src="/sarembok-capability-fabric.js" defer></script>'
if css not in text:
    text = text.replace('</head>', f'    {css}\n</head>', 1)
if js not in text:
    text = text.replace('</body>', f'    {js}\n</body>', 1)
index.write_text(text, encoding='utf-8')
PY

RUN useradd --create-home --uid 10001 sarembok \
    && mkdir -p /data \
    && chown -R sarembok:sarembok /app /data

USER sarembok
EXPOSE 9000
VOLUME ["/data"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import os,socket; s=socket.create_connection(('127.0.0.1',int(os.getenv('SAREMBOK_PORT','9000'))),2); s.close()"

CMD ["python", "/app/knowledge_rpc_server.py"]
