class EventRouter:


    def route(self,event):

        handlers={

        "CHAT":
        self.chat,

        "VOICE":
        self.voice,

        "VISION":
        self.vision

        }


        handler=handlers.get(
        event
        )


        if handler:

            return handler()


        return "Unknown Event"



    def chat(self):

        return "Chat Handler"


    def voice(self):

        return "Voice Handler"


    def vision(self):

        return "Vision Handler"
