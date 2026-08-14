# Sarembok VE — First 60-Second Digital Human Demonstration

## Goal

Demonstrate Sarembok as an embodied AI runtime in under one minute:

1. A real avatar is visible in Unreal.
2. Sarembok connects to the avatar through the Bridge.
3. One `sarembok.v1` `Speak` command changes emotion and produces speech.
4. A trace ID is visible in the Unreal log.
5. A second interaction recalls a memory from the same session.

## Before the demonstration

### Cloud

- Runtime is ONLINE.
- WebSocket endpoint is reachable.
- Authentication is configured.
- No GPU is required for the control-plane demonstration.

### Unreal

- UE 5.8 project opens without module errors.
- TextToSpeech plugin is enabled.
- A renderable MetaHuman/avatar actor is actually present in the demo map.
- The avatar has a face skeletal mesh with the configured morph targets.
- SarembokBridge is initialized.

Run the repository-side static checks first:

```powershell
python Tools/validate_digital_human_demo.py
```

A PASS here means the repository contract is internally consistent. It does **not** replace the Unreal visual/audio acceptance test.

## Live demonstration

### Step 1 — Start Unreal

Open the demonstration map and confirm the avatar is visible before discussing the architecture.

### Step 2 — Connect the Bridge

Confirm the log contains:

```text
[SAREMBOK] Bridge Service Ready
```

### Step 3 — Send one command

Use `Docs/digital-human-demo-command.json` or send the same `sarembok.v1` payload through the runtime.

Expected payload:

```json
{
  "command": "Speak",
  "target": "Avatar",
  "payload": {
    "text": "Hello. I am the Sarembok digital human.",
    "emotion": "Joyful"
  }
}
```

Expected result:

- Avatar speaks.
- Facial expression changes toward Joyful.
- Jaw movement occurs while speech is active.
- Unreal log reports the command and trace.

### Step 4 — Demonstrate memory

Tell the system:

```text
Remember that my name is Tim.
```

Then ask:

```text
What is my name?
```

The second response must use the stored value without manually supplying it again.

## What to say

> "Sarembok is the orchestration layer. The AI decides what should happen, the runtime carries the state and memory, the Bridge delivers the command, and the digital human becomes the visible and audible embodiment of that decision."

## Hard stop conditions

Do not claim the demo is complete if any of these fail:

- no visible avatar
- no WebSocket connection
- no Speak command reaching Unreal
- no audible speech
- no visible facial response
- no trace correlation
- memory cannot be recalled in the same session

The repository intentionally distinguishes a **control-plane fallback actor** from a real renderable MetaHuman. The fallback is useful for routing tests but is not a visual digital-human demonstration.
