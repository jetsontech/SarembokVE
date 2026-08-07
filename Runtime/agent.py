from commands import speak, emotion


class SarembokAgent:
    def __init__(self, memory):
        self.memory = memory

    def process(self, event):
        event_type = event.get("event")

        if event_type == "user_detected":
            self.memory.remember("last_event", "User detected")
            return [
                emotion("friendly"),
                speak("Hello, I am Sarembok.", "friendly"),
            ]

        return []
