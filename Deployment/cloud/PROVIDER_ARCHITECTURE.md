# Sarembok VE Provider Architecture

Sarembok VE is provider-agnostic. External model APIs are optional interchangeable backends, not the platform itself.

## Development and validation

The runtime must be able to execute its conversation contract without a paid external provider. The deterministic provider is the canonical offline/CI backend.

## Production

A production deployment may select an external provider with environment configuration. Provider credentials must never be committed to Git or embedded in frontend code.

Recommended configuration variables:

- `SAREMBOK_MODEL_PROVIDER`
- `SAREMBOK_MODEL_NAME`
- `SAREMBOK_MODEL_ENDPOINT`
- `SAREMBOK_MODEL_API_KEY`

## Client architecture

Browsers, mobile applications, and Unreal clients communicate with Sarembok's runtime protocol. They do not communicate directly with OpenAI or another model vendor.

## Hardware architecture

Unreal Engine and local GPU hardware are development/worker technologies only. They are not requirements for public access to Sarembok VE.
