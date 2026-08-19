import json
import unittest

from sarembok_avatar import AvatarCommand, AvatarExpression, AvatarSignal, AvatarState
from sarembok_unreal_avatar_bridge import SarembokUnrealAvatarBridge


class FakeTransport:
    def __init__(self):
        self.messages = []

    def send(self, message):
        self.messages.append(message)
        return {"ok": True}


class UnrealBridgeTests(unittest.TestCase):
    def test_avatar_state_is_serialized_for_unreal(self):
        transport = FakeTransport()
        bridge = SarembokUnrealAvatarBridge(transport)
        command = AvatarCommand(
            command_id="cmd-1",
            state=AvatarState(
                session_id="session-1",
                signal=AvatarSignal.SPEAKING,
                expression=AvatarExpression("engaged", 0.8),
                speech_stream_ref="speech://1",
            ),
            animation_ref="anim://speak",
            viseme_ref="viseme://1",
        )
        result = bridge.apply(command)
        payload = json.loads(transport.messages[0])
        self.assertTrue(result["ok"])
        self.assertEqual(payload["message_type"], "sarembok.avatar.state")
        self.assertEqual(payload["session_id"], "session-1")
        self.assertEqual(payload["signal"], "speaking")
        self.assertEqual(payload["expression"], "engaged")
        self.assertEqual(payload["viseme_ref"], "viseme://1")


if __name__ == "__main__":
    unittest.main()
