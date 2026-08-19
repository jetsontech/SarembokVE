import unittest

from sarembok_multimodal import (
    Modality,
    ModalityInput,
    MultimodalInteraction,
    build_response,
    modalities_present,
)


class MultimodalTests(unittest.TestCase):
    def test_multiple_modalities_share_one_interaction(self):
        interaction = MultimodalInteraction(
            interaction_id="i1",
            user_id="u1",
            inputs=[
                ModalityInput(Modality.VOICE, "audio://1", transcript="open the app"),
                ModalityInput(Modality.VISION, "screen://1"),
                ModalityInput(Modality.UI, "ui://1"),
            ],
        )
        self.assertEqual(
            modalities_present(interaction),
            {Modality.VOICE, Modality.VISION, Modality.UI},
        )

    def test_response_can_drive_text_speech_avatar_and_actions(self):
        interaction = MultimodalInteraction("i2", "u1")
        response = build_response(
            interaction,
            text="I opened it.",
            speech_ref="speech://2",
            avatar_state={"expression": "engaged"},
            action_refs=["execution://42"],
        )
        self.assertEqual(response.text, "I opened it.")
        self.assertEqual(response.speech_ref, "speech://2")
        self.assertEqual(response.action_refs, ["execution://42"])


if __name__ == "__main__":
    unittest.main()
