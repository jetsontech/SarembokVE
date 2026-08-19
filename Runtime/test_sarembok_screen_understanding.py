import unittest

from sarembok_screen_understanding import (
    ScreenObservation,
    ScreenRegion,
    StaticScreenUnderstanding,
    observation_to_events,
)


class ScreenUnderstandingTests(unittest.TestCase):
    def test_static_adapter_preserves_reference(self):
        observation = StaticScreenUnderstanding().analyze("screen://test-1")
        self.assertEqual(observation.source_ref, "screen://test-1")

    def test_regions_become_normalized_events(self):
        observation = ScreenObservation(
            source_ref="screen://test-2",
            width=1920,
            height=1080,
            regions=[
                ScreenRegion("r1", "text", "Continue", 0.99),
                ScreenRegion("r2", "button", "", 0.97),
            ],
        )
        events = observation_to_events(observation)
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["text"], "Continue")
        self.assertEqual(events[1]["kind"], "button")

    def test_region_views(self):
        observation = ScreenObservation(
            source_ref="screen://test-3",
            width=1,
            height=1,
            regions=[
                ScreenRegion("r1", "text", "Hello"),
                ScreenRegion("r2", "input"),
                ScreenRegion("r3", "image"),
            ],
        )
        self.assertEqual(len(observation.text_regions), 1)
        self.assertEqual(len(observation.interactive_regions), 1)


if __name__ == "__main__":
    unittest.main()
