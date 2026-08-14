#!/usr/bin/env python3
"""Static acceptance checks for the Sarembok VE Digital Human demo path.

This script deliberately does not claim that Unreal has been visually tested.
It verifies the repository-side contract so the remaining workstation test is
small, explicit, and repeatable.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    ROOT / "Docs" / "DigitalHumanDemo.md",
    ROOT / "Docs" / "digital-human-demo-command.json",
    ROOT / "Plugins" / "SarembokAvatar" / "Source" / "SarembokAvatar" / "Private" / "SarembokAvatarComponent.cpp",
    ROOT / "Plugins" / "SarembokAvatar" / "Source" / "SarembokAvatar" / "Public" / "SarembokAvatarComponent.h",
    ROOT / "Plugins" / "SarembokBridge" / "Source" / "SarembokBridge" / "Private" / "SarembokMessageDispatcher.cpp",
]


def check(label: str, condition: bool) -> bool:
    print(f"[{'PASS' if condition else 'FAIL'}] {label}")
    return condition


def main() -> int:
    ok = True
    for path in REQUIRED:
        ok &= check(f"required file: {path.relative_to(ROOT)}", path.is_file())

    command_path = ROOT / "Docs" / "digital-human-demo-command.json"
    if command_path.is_file():
        try:
            command = json.loads(command_path.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"[FAIL] command JSON parses: {exc}")
            ok = False
        else:
            payload = command.get("payload", {})
            context = command.get("context", {})
            ok &= check("protocol is sarembok.v1", command.get("protocol") == "sarembok.v1")
            ok &= check("command is Speak", command.get("command") == "Speak")
            ok &= check("target is Avatar", command.get("target") == "Avatar")
            ok &= check("Speak text is non-empty", bool(str(payload.get("text", "")).strip()))
            ok &= check("Speak emotion is present", bool(str(payload.get("emotion", "")).strip()))
            ok &= check("trace correlation is present", bool(str(context.get("trace", "")).strip()))

    avatar_cpp = ROOT / "Plugins" / "SarembokAvatar" / "Source" / "SarembokAvatar" / "Private" / "SarembokAvatarComponent.cpp"
    bridge_cpp = ROOT / "Plugins" / "SarembokBridge" / "Source" / "SarembokBridge" / "Private" / "SarembokMessageDispatcher.cpp"
    avatar_text = avatar_cpp.read_text(encoding="utf-8") if avatar_cpp.is_file() else ""
    bridge_text = bridge_cpp.read_text(encoding="utf-8") if bridge_cpp.is_file() else ""

    ok &= check("avatar uses UTextToSpeechEngineSubsystem", "UTextToSpeechEngineSubsystem" in avatar_text)
    ok &= check("avatar creates/activates a TTS channel", "AddDefaultChannel" in avatar_text and "ActivateChannel" in avatar_text)
    ok &= check("avatar drives speech", "SpeakOnChannel" in avatar_text)
    ok &= check("avatar stops speech cleanly", "StopSpeakingOnChannel" in avatar_text)
    ok &= check("avatar has speech jaw animation", "SetMorph(JawOpenMorph" in avatar_text and "IsSpeakingOnChannel" in avatar_text)
    ok &= check("bridge passes emotion into Speak", bool(re.search(r"->Speak\(Text, Emotion\)", bridge_text)))
    ok &= check("bridge records trace IDs", "ExtractTraceId" in bridge_text and "Trace.Complete()" in bridge_text)

    print()
    if ok:
        print("SAREMBOK DIGITAL HUMAN REPOSITORY CONTRACT: PASS")
        print("Remaining acceptance test: compile/run Unreal and verify a real renderable avatar, audible speech, visible facial response, and repeatable memory recall.")
        return 0

    print("SAREMBOK DIGITAL HUMAN REPOSITORY CONTRACT: FAIL")
    return 1


if __name__ == "__main__":
    sys.exit(main())
