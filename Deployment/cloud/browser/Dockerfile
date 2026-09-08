FROM mcr.microsoft.com/playwright/python:v1.55.0-noble

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SAREMBOK_BROWSER_PORT=9100 \
    SAREMBOK_BROWSER_MAX_TEXT=120000 \
    SAREMBOK_BROWSER_NAVIGATION_TIMEOUT_MS=15000

WORKDIR /app

COPY server.py /app/server.py

RUN pip install --no-cache-dir playwright==1.55.0

RUN useradd --create-home --uid 10002 sarembok-browser \
    && chown -R sarembok-browser:sarembok-browser /app

USER sarembok-browser

EXPOSE 9100

HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=6 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:9100/health', timeout=3).read()"

CMD ["python", "/app/server.py"]
