FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SAREMBOK_PORT=9000 \
    SAREMBOK_DB_PATH=/data/sarembok_cloud.db

WORKDIR /app

COPY Runtime/requirements.txt /app/Runtime/requirements.txt
RUN apt-get update \
    && apt-get install -y --no-install-recommends openssh-client \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir -r /app/Runtime/requirements.txt \
    && rm -rf /root/.cache

COPY Deployment/cloud/server.py /app/server.py
COPY Deployment/cloud/entrypoint.py /app/entrypoint.py
COPY Deployment/cloud/conversation_runtime.py /app/conversation_runtime.py
COPY Deployment/cloud/engineering_runtime.py /app/engineering_runtime.py
COPY Deployment/cloud/public_session.py /app/public_session.py
COPY Engineering /app/Engineering
COPY frontend /app/frontend
COPY Deployment/cloud/patch_frontend.py /app/patch_frontend.py

# Apply deterministic frontend fixes during the image build. This keeps
# source editing centralized and prevents ad-hoc production copy/paste.
RUN python /app/patch_frontend.py

RUN useradd --create-home --uid 10001 sarembok \
    && mkdir -p /data \
    && chown -R sarembok:sarembok /app /data

USER sarembok
EXPOSE 9000
VOLUME ["/data"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import os,socket; s=socket.create_connection(('127.0.0.1',int(os.getenv('SAREMBOK_PORT','9000'))),2); s.close()"

CMD ["python", "/app/entrypoint.py"]

