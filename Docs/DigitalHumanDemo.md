# Sarembok VE — First Working Digital Human Demonstration

## Purpose

This is the canonical demonstration path for Sarembok VE. It proves the platform as an **embodied AI runtime**, not merely a cloud control plane.

The demonstration connects:

```text
Human input
   -> Sarembok Runtime / Agent
   -> sarembok.v1 command
   -> SarembokBridge
   -> SarembokAvatar / Voice
   -> MetaHuman in Unreal
   -> visible expression + spoken response
```

## What the demo must visibly prove

1. A digital human exists in the Unreal world.
2. The digital human can receive a Sarembok command.
3. The command can change emotion/facial state.
4. The command can produce speech through the voice subsystem.
5. The response is correlated to an agent/trace ID.
6. The same session can retain a memory item for the next interaction.

## Canonical demo sequence

### 1. Start Unreal

Open the Sarembok VE Unreal Engine 5.8 project and load the demonstration map containing the MetaHuman/avatar actor.

### 2. Start the cloud runtime

The runtime must be reachable through the configured WebSocket endpoint.

### 3. Establish the avatar session

The Unreal client registers/discovers the avatar and exposes it as the active Sarembok digital-human target.

### 4. Send a greeting command

```json
{
  "protocol": "sarembok.v1",
  "id": "demo-greeting-001",
  "timestamp": "2026-08-14T00:00:00Z",
  "command": "Speak",
  "target": "Avatar",
  "payload": {
    "text": "Hello. I am the Sarembok digital human.",
    "emotion": "Joyful"
  },
  "context": {
    "agent": "demo-agent",
    "trace": "demo-trace-001",
    "reason": "Demo greeting"
  }
}
```

Expected visible behavior:

- avatar receives command
- facial expression changes toward Joyful
- voice playback starts
- command trace is logged

### 5. Demonstrate memory

Store a simple fact such as:

```text
user_name = Tim
```

Then issue a second request that requires recalling it:

```text
What is my name?
```

The digital human should answer using the remembered value.

## Subsystem responsibilities

| Component | Demo responsibility |
|---|---|
| SarembokBridge | WebSocket transport and command dispatch |
| SarembokAgent | Intent/reasoning and action selection |
| SarembokAvatar | Facial/expression control |
| SarembokVoice | Speech/TTS execution and visemes |
| SarembokMemory | Session and episodic/semantic recall |
| SarembokVision | Optional world/actor awareness |

## Acceptance criteria

The demo is **not considered complete** until all of these are true:

- [ ] Unreal opens without a plugin/module failure.
- [ ] A visible digital-human/avatar actor is present.
- [ ] Runtime WebSocket connection is established.
- [ ] `Speak` reaches the avatar.
- [ ] Emotion reaches the avatar.
- [ ] Speech is audible.
- [ ] Facial state changes are visible.
- [ ] A trace ID can be followed from request to avatar action.
- [ ] One memory can be written and recalled.
- [ ] The complete sequence can be repeated without restarting Unreal.

## Important distinction

`Content/MetaHuman/metahuman.json` describes the intended MetaHuman capabilities, including animation, facial control, voice synchronization, and emotion support. It is a capability declaration, **not proof that a renderable MetaHuman asset is present in the current checkout**.

Therefore the final acceptance test must verify the actual Unreal world/actor rather than relying on configuration files.
