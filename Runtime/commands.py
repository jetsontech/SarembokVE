from dataclasses import dataclass, asdict
import json


@dataclass
class SarembokCommand:
    command: str
    target: str
    payload: dict

    def to_json(self):
        return json.dumps(asdict(self))


def speak(text, emotion="neutral"):
    return SarembokCommand(
        command="Speak",
        target="Avatar",
        payload={"text": text, "emotion": emotion},
    )


def emotion(state):
    return SarembokCommand(
        command="Emotion",
        target="Avatar",
        payload={"state": state},
    )
