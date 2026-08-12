# Sarembok VE Security Architecture Guide

## Security Protections

1. **Authentication Token Protection**:
   - Authentication secret is supplied via environment variable `SAREMBOK_AUTH_TOKEN`.
   - Token comparisons use constant-time HMAC comparison (`hmac.compare_digest`).
   - Tokens are stored in browser `sessionStorage` (never in source files, HTML, logs, or image layers).

2. **Container Security & Privileges**:
   - `no-new-privileges:true` enabled on containers.
   - `cap_drop: ALL` drops Linux capabilities.
   - Read-only root filesystem enabled (`read_only: true` with ephemeral `/tmp` tmpfs).
   - Process runs under dedicated unprivileged user `sarembok` (UID 10001).

3. **Edge Proxy Isolation**:
   - Runtime port `9000` is bound strictly to `127.0.0.1` or container network.
   - Caddy edge container acts as the sole public gateway for ports `80` and `443`.
   - Security headers enforced (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`).

4. **Resource Limits**:
   - Max connection limit (`SAREMBOK_MAX_CONNECTIONS`: 100).
   - Max request size (`SAREMBOK_MAX_REQUEST_BYTES`: 1MB).
   - Max RPC method length (`SAREMBOK_MAX_METHOD_LENGTH`: 128 chars).
