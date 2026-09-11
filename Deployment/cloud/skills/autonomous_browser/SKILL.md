---
name: browser_navigate
description: Navigate to a verified public URL using headless Chromium, extract structured page markdown, text, or capture full-page viewport screenshots.
domain: browser
parameters:
  {
    "type": "object",
    "properties": {
      "url": {
        "type": "string",
        "description": "The target HTTP or HTTPS URL to navigate to."
      },
      "extractText": {
        "type": "boolean",
        "description": "Extract structured text and readable markdown from the page.",
        "default": true
      },
      "screenshot": {
        "type": "boolean",
        "description": "Capture a viewport screenshot as base64 png.",
        "default": false
      }
    },
    "required": ["url"]
  }
---

# Autonomous Headless Browser Skill
Navigates web pages with JavaScript rendering, bypassing static page limitations. Extracts clean readability text and DOM elements.
