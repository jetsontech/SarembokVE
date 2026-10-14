# Local Gemma Inference: Configuration and Verification

## Current implementation boundary

The runtime's `ProviderRouter` supports an OpenAI-compatible local inference endpoint.
The production Compose files now pass through the following variables:

- `SAREMBOK_LOCAL_ONLY` — hard application-level routing policy; defaults to `false`.
- `SAREMBOK_LOCAL_GEMMA_URL` — complete OpenAI-compatible chat-completions endpoint URL.
- `SAREMBOK_LOCAL_GEMMA_MODEL` — exact model identifier served by that endpoint.
- `SAREMBOK_LOCAL_GEMMA_KEY` — optional endpoint credential.

This change does **not** deploy a model server or download model weights. Do not enable local-only mode until a reachable local/private endpoint and exact served model identifier have been configured.

## Local-only routing behavior

When `SAREMBOK_LOCAL_ONLY=true`:

1. The provider router selects only `LocalGemma`.
2. Client-supplied dynamic API keys and configured external providers are ignored by this router.
3. A missing endpoint URL or model name fails closed.
4. A local inference failure is returned as an error; the router does not fall back to Gemini, OpenAI, Groq, OpenRouter, or a custom provider.

This is application-level enforcement within `ProviderRouter`. It is **not**, by itself, proof of host/container network isolation or proof that unrelated code cannot make external requests. A production local-only claim requires a separate egress audit and a controlled test showing that external inference endpoints cannot be reached.

## Configure only after confirming the endpoint

Set these values in the deployment environment file used by the Compose invocation. Do not commit credentials.

```dotenv
SAREMBOK_LOCAL_ONLY=true
SAREMBOK_LOCAL_GEMMA_URL=http://<private-inference-host>:<port>/v1/chat/completions
SAREMBOK_LOCAL_GEMMA_MODEL=<exact-model-id-served-by-endpoint>
SAREMBOK_LOCAL_GEMMA_KEY=<endpoint-key-if-required>
```

Replace every angle-bracket value with a verified value before deployment. Do not use these placeholders literally. Use a Docker service name when the inference server is on the same Compose network; use a private address only when the host and firewall rules restrict access appropriately.

If no compatible endpoint is deployed, leave `SAREMBOK_LOCAL_ONLY=false`. Enabling it without an endpoint intentionally causes inference requests to fail instead of silently using a paid/external provider.

## Regression tests

From the repository root:

```bash
python -m unittest Deployment.cloud.test_local_only_routing -v
```

The tests verify provider selection and fail-closed configuration handling. They do not make a real network request and do not prove that the endpoint is reachable.

## Required production acceptance evidence

Before declaring Gemma production-ready, record:

- deployed Git commit SHA and image IDs;
- exact model repository/checkpoint, quantization, license, inference engine/version, and served model ID;
- successful request through the real SarembokVE UI, correlated with runtime and inference-server logs;
- warm and cold time-to-first-token, generated tokens/second, total response time, and peak RAM under load;
- behavior when the model server is stopped, including proof that no provider fallback occurs;
- concurrent tests with Kokoro voice synthesis active;
- network egress evidence showing whether external inference endpoints are blocked or reachable;
- request cancellation results and the test method used.

Do not report benchmark numbers without the raw measurements, prompt/output sizes, warm/cold state, and exact hardware/software configuration.
