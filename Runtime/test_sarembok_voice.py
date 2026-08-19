import unittest

from sarembok_voice import (
    AudioChunk,
    AudioEventType,
    SpeechEvent,
    VoiceSession,
)


class FakeRecognizer:
    def accept_audio(self, chunk):
        return [SpeechEvent(AudioEventType.TRANSCRIPT_PARTIAL, chunk.stream_id, "hello")]

    def end_stream(self, stream_id):
        return [SpeechEvent(AudioEventType.TRANSCRIPT_FINAL, stream_id, "hello")]


class FakeSynthesizer:
    def synthesize(self, text, stream_id):
        return [AudioChunk(stream_id, 0, f"audio://{text}")]


class VoiceTests(unittest.TestCase):
    def test_streaming_audio_produces_speech_events(self):
        session = VoiceSession(FakeRecognizer(), FakeSynthesizer())
        events = session.ingest(AudioChunk("s1", 0, "audio://chunk"))
        self.assertEqual(events[0].event_type, AudioEventType.TRANSCRIPT_PARTIAL)
        self.assertEqual(events[0].text, "hello")

    def test_barge_in_interrupts_output(self):
        session = VoiceSession(FakeRecognizer(), FakeSynthesizer())
        event = session.interrupt("s2")
        self.assertEqual(event.event_type, AudioEventType.INTERRUPT)
        self.assertTrue(session.output_interrupted)

    def test_speech_output_resets_interrupt_state(self):
        session = VoiceSession(FakeRecognizer(), FakeSynthesizer())
        session.interrupt("s3")
        chunks = session.speak("hello", "s4")
        self.assertFalse(session.output_interrupted)
        self.assertEqual(chunks[0].payload_ref, "audio://hello")


if __name__ == "__main__":
    unittest.main()
