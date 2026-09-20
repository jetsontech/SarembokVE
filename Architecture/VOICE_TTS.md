# SarembokVE Neural Voice Architecture

SarembokVE uses a private, self-hosted Kokoro TTS service for neural speech output.

## Runtime path

```
Browser
  -> /api/tts
  -> Caddy
  -> Sarembok runtime :9000
  -> private sarembok-voice :9200
  -> Kokoro-82M
  -> WAV
  -> Browser Audio
```

The browser session token is required at the runtime boundary. The voice container is
not published to the Internet.

## Engine

- Engine: Kokoro
- Model: Kokoro-82M v1.x
- Default voice: `af_heart`
- Sample rate: 24 kHz PCM WAV
- Default speed: 0.95
- Maximum synthesis input: 4,000 characters
- CPU-only deployment is supported
- Model/cache data is stored in the `sarembok-voice-cache` Docker volume

Kokoro's model weights are distributed under Apache-2.0 according to the upstream
model card. The inference package is installed in the isolated voice container.

## Browser fallback

If the private neural voice service is unavailable or browser audio playback is
blocked by autoplay policy, Sarembok falls back to the browser's native
`SpeechSynthesis` API. That fallback is compatibility behavior, not the primary
Sarembok neural voice engine.

## Voice profiles

| Sarembok profile | Kokoro voice |
|---|---|
| Vega | `af_heart` |
| Ada | `bf_emma` |
| Aoede | `af_bella` |
| Kore | `af_nicole` |
| Onyx | `am_michael` |
| Sovereign Synth | `am_adam` |

## Deployment

The service is included by `Deployment/cloud/compose.yaml` and therefore participates
in the production compose stack. The runtime waits for the voice service health check
before starting.

First startup can take longer because Kokoro model/voice assets are downloaded into
the persistent voice cache. Subsequent restarts reuse that cache.
