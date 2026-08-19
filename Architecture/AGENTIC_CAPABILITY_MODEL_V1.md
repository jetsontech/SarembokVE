# Sarembok Agentic Capability Model v1

## Capability classes

Sarembok capabilities are explicit, addressable operations exposed to agents through policy-controlled interfaces.

### Observe

Examples: camera perception, filesystem inspection, process status, network state, application state.

### Reason

Examples: planning, classification, diagnosis, code analysis, prioritization.

### Create

Examples: write files, generate code, create documents, produce media, construct plans.

### Execute

Examples: run approved commands, invoke APIs, operate applications, deploy services, schedule work.

### Communicate

Examples: speech, text, notifications, avatar interaction, collaboration.

### Remember

Examples: durable memory, task checkpoints, user preferences, execution history.

## Capability descriptor

A capability should declare:

```text
id
version
class
input_schema
output_schema
required_permissions
risk_level
supports_dry_run
supports_rollback
provider
availability
```

## Provider independence

A capability may be implemented by local software, cloud services, device APIs, GPU runtimes, or third-party models. The agent sees the Sarembok capability contract rather than provider-specific internals.

## Permission boundary

An agent cannot infer permission from capability availability. Permission is separately evaluated before execution.

## Composition

Capabilities can be composed into workflows. A workflow must preserve execution IDs, step IDs, observations, validations, and checkpoints so long-running work remains recoverable and auditable.

## Computer control

Computer interaction is a first-class capability family. Future implementations may control a Windows-compatible application, Linux environment, macOS device, Android device, iOS device, or Sarembok-native operating environment through adapters.

The contract deliberately does not require Microsoft Windows, Linux, Android, iOS, Unreal Engine, or any single operating system.
