FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    SAREMBOK_VOICE_PORT=9200 \
    SAREMBOK_VOICE_DEFAULT=af_heart \
    SAREMBOK_VOICE_LANG=en-us \
    SAREMBOK_VOICE_MAX_CHARS=4000

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends espeak-ng libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir "kokoro>=0.9.4,<1.0" "soundfile>=0.12,<1.0"

COPY server.py /app/server.py

RUN useradd --create-home --uid 10002 sarembokvoice \
    && chown -R sarembokvoice:sarembokvoice /app

USER sarembokvoice

EXPOSE 9200

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:9200/health', timeout=5).read()"

CMD ["python", "/app/server.py"]
