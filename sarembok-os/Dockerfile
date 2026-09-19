FROM python:3.11-slim
WORKDIR /app
COPY sim /app/sim
COPY console /app/console
RUN pip install --no-cache-dir websockets
ENV SAREMBOK_DB=/data/sarembok.db
VOLUME ["/data"]
EXPOSE 8080 9001
CMD ["python", "sim/console_bridge.py", "--host", "0.0.0.0", "--http-port", "8080", "--ws-port", "9001", "--db", "/data/sarembok.db"]
