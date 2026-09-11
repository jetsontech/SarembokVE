---
name: media_streamer
description: Search, embed, and stream music, podcasts, comedy routines, live news broadcasts (e.g. BBC News), or focus audio directly into the conversation UI.
domain: media
parameters:
  {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "Artist, genre, song title, or broadcast name to stream."
      },
      "mediaType": {
        "type": "string",
        "enum": ["music", "video", "podcast", "news"],
        "description": "Type of media to embed (music, video, podcast, or news).",
        "default": "music"
      }
    },
    "required": ["query"]
  }
---

# Universal Media Streamer Skill
Embeds interactive audio players or video cards using :::music and :::video blocks with dedicated pop-out window controls.
