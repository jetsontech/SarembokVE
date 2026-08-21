import unittest

from sarembok_perception_bridge import PerceptionKind, SarembokPerceptionBridge
from sarembok_gui_control import UIElement, UIObservation


class PerceptionBridgeTests(unittest.TestCase):
    def test_vision_events_are_normalized(self):
        bridge = SarembokPerceptionBridge()
        events = bridge.ingest_vision_events([
            {"kind": "object", "source": "opencv", "label": "person", "confidence": 0.98}
        ])
        self.assertEqual(events[0].kind, PerceptionKind.OBJECT)
        self.assertEqual(events[0].label, "person")

    def test_gui_observation_becomes_ui_event(self):
        bridge = SarembokPerceptionBridge()
        observation = UIObservation(
            application="Editor",
            window_title="Project",
            elements=[UIElement("b1", "button", "Build")],
            screenshot_ref="protected://frame/1",
        )
        events = bridge.ingest_ui_observation(observation)
        self.assertEqual(events[0].kind, PerceptionKind.UI)
        self.assertEqual(events[0].data["elements"][0]["name"], "Build")
        self.assertEqual(events[0].source_ref, "protected://frame/1")

    def test_raw_source_is_not_copied_into_event(self):
        bridge = SarembokPerceptionBridge()
        events = bridge.ingest_vision_events([
            {"kind": "scene", "source": "camera", "source_ref": "protected://camera/frame"}
        ])
        self.assertNotIn("raw_frame", events[0].data)


if __name__ == "__main__":
    unittest.main()
