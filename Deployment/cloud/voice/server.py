"""SarembokVE local neural speech service.

Uses the open-weight Kokoro TTS model locally. The runtime remains the
authentication boundary; this service is reachable only on the Docker
network and is never published directly to the Internet.
"""

from __future__ import annotations

import io
import json
import base64
import logging
import os
import threading

# The VPS voice container is CPU-limited to two cores. Pin PyTorch to that
# same budget so Kokoro does not oversubscribe the host and thrash the CPU.
import torch

VOICE_THREADS = max(1, int(os.getenv("SAREMBOK_VOICE_THREADS", "2")))
torch.set_num_threads(VOICE_THREADS)
torch.set_num_interop_threads(1)

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

import soundfile as sf
from kokoro import KPipeline

PORT = int(os.getenv("SAREMBOK_VOICE_PORT", "9200"))
DEFAULT_VOICE = os.getenv("SAREMBOK_VOICE_DEFAULT", "af_heart").strip() or "af_heart"
DEFAULT_LANG = os.getenv("SAREMBOK_VOICE_LANG", "en-us").strip().lower() or "en-us"
MAX_CHARS = max(100, int(os.getenv("SAREMBOK_VOICE_MAX_CHARS", "4000")))
SAMPLE_RATE = 24000

logging.basicConfig(
    level=os.getenv("SAREMBOK_VOICE_LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
LOG = logging.getLogger("sarembok.voice")

LANG_ALIASES = {
    "en": "a",
    "en-us": "a",
    "en-gb": "b",
    "es": "e",
    "fr": "f",
    "hi": "h",
    "it": "i",
    "pt-br": "p",
    "ja": "j",
    "zh": "z",
}

pipeline_cache: dict[str, KPipeline] = {}
pipeline_lock = threading.Lock()
synthesis_lock = threading.Lock()


def get_pipeline(language: str) -> KPipeline:
    lang_code = LANG_ALIASES.get(language, "a")
    with pipeline_lock:
        pipeline = pipeline_cache.get(lang_code)
        if pipeline is None:
            LOG.info("loading Kokoro pipeline language=%s code=%s", language, lang_code)
            pipeline = KPipeline(lang_code=lang_code, repo_id="hexgrad/Kokoro-82M")
            pipeline_cache[lang_code] = pipeline
        return pipeline


def synthesize(text: str, voice: str, speed: float, language: str) -> bytes:
    clean = " ".join(str(text).split()).strip()
    if not clean:
        raise ValueError("text is required")
    if len(clean) > MAX_CHARS:
        raise ValueError(f"text exceeds {MAX_CHARS} character limit")

    voice_name = voice.strip() or DEFAULT_VOICE
    rate = min(1.5, max(0.6, float(speed)))
    pipeline = get_pipeline(language)

    chunks = []
    # KPipeline is intentionally serialized: one model instance is not
    # thread-safe for concurrent generation.
    with synthesis_lock:
        for _, _, audio in pipeline(clean, voice=voice_name, speed=rate):
            chunks.append(audio)

    if not chunks:
        raise RuntimeError("Kokoro returned no audio")

    import numpy as np

    audio = np.concatenate(chunks)
    output = io.BytesIO()
    sf.write(output, audio, SAMPLE_RATE, format="WAV", subtype="PCM_16")
    return output.getvalue()


class Handler(BaseHTTPRequestHandler):
    server_version = "SarembokVoice/1.0"

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _stream_tts(self, payload: dict) -> None:
        clean = " ".join(str(payload.get("text", "")).split()).strip()
        if not clean:
            raise ValueError("text is required")
        if len(clean) > MAX_CHARS:
            raise ValueError(f"text exceeds {MAX_CHARS} character limit")
        voice_name = str(payload.get("voice", DEFAULT_VOICE)).strip() or DEFAULT_VOICE
        rate = min(1.5, max(0.6, float(payload.get("speed", 0.95))))
        language = str(payload.get("language", DEFAULT_LANG)).strip().lower() or DEFAULT_LANG
        pipeline = get_pipeline(language)
        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()
        import numpy as np
        with synthesis_lock:
            emitted = 0
            for _, _, audio in pipeline(clean, voice=voice_name, speed=rate):
                if audio is None: continue
                samples = audio.detach().cpu().numpy() if hasattr(audio, "detach") else np.asarray(audio)
                samples = np.asarray(samples).squeeze()
                if samples.size == 0: continue
                output = io.BytesIO()
                sf.write(output, samples, SAMPLE_RATE, format="WAV", subtype="PCM_16")
                frame = {"audio": base64.b64encode(output.getvalue()).decode("ascii"), "index": emitted}
                self.wfile.write((json.dumps(frame, separators=(",", ":")) + "\n").encode("utf-8"))
                self.wfile.flush()
                emitted += 1
            if emitted == 0: raise RuntimeError("Kokoro returned no audio")

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/health":
            self._send_json(200, {
                "status": "ONLINE",
                "engine": "kokoro",
                "model": "Kokoro-82M",
                "voice": DEFAULT_VOICE,
                "sampleRate": SAMPLE_RATE,
            })
            return
        if path == "/voices":
            self._send_json(200, {
                "engine": "kokoro",
                "voices": [
                    "af_heart", "af_bella", "af_nicole", "af_sarah", "af_sky",
                    "am_adam", "am_michael",
                    "bf_emma", "bf_isabella", "bm_george", "bm_lewis",
                ],
            })
            return
        self._send_json(404, {"error": "not_found"})

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path != "/tts":
            self._send_json(404, {"error": "not_found"})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 65536:
                raise ValueError("invalid_request_size")
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            if path == "/tts/stream":
                self._stream_tts(payload)
                return

            audio = synthesize(
                payload.get("text", ""),
                str(payload.get("voice", DEFAULT_VOICE)),
                float(payload.get("speed", 0.95)),
                str(payload.get("language", DEFAULT_LANG)),
            )
            self.send_response(200)
            self.send_header("Content-Type", "audio/wav")
            self.send_header("Content-Length", str(len(audio)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            try:
                self.wfile.write(audio)
            except BrokenPipeError:
                # Client interruption is normal during barge-in or replacement
                # speech. The response was already successful; do not emit a
                # second 400 response onto a closed socket.
                LOG.info("client disconnected during audio delivery")
        except BrokenPipeError:
            LOG.info("client disconnected during TTS request")
        except Exception as exc:
            LOG.warning("synthesis failed: %s", exc)
            try:
                self._send_json(400, {"error": str(exc)})
            except BrokenPipeError:
                LOG.info("client disconnected before TTS error response")

    def log_message(self, fmt: str, *args) -> None:
        LOG.info("%s - %s", self.address_string(), fmt % args)


def main() -> None:
    # Warm the default English pipeline and perform one real synthesis before
    # binding the HTTP server. This makes startup failure explicit instead of
    # allowing a container to report healthy while the first request fails.
    get_pipeline(DEFAULT_LANG)
    warmup_audio = synthesize("Sarembok voice ready.", DEFAULT_VOICE, 0.95, DEFAULT_LANG)
    LOG.info(
        "Kokoro neural TTS ready port=%s voice=%s threads=%s max_chars=%s warmup_bytes=%s",
        PORT, DEFAULT_VOICE, VOICE_THREADS, MAX_CHARS, len(warmup_audio),
    )
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
