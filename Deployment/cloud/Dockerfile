FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SAREMBOK_PORT=9000 \
    SAREMBOK_DB_PATH=/data/sarembok_cloud.db

WORKDIR /app

COPY Runtime/requirements.txt /app/Runtime/requirements.txt
RUN pip install --no-cache-dir -r /app/Runtime/requirements.txt

COPY Deployment/cloud/server.py /app/server.py

RUN useradd --create-home --uid 10001 sarembok \
    && mkdir -p /data \
    && chown -R sarembok:sarembok /app /data

USER sarembok
EXPOSE 9000
VOLUME ["/data"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import socket; s=socket.create_connection(('127.0.0.1',9000),2); s.close()"

CMD ["python", "/app/server.py"]
