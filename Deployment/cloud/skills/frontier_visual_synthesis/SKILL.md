---
name: generate_image
description: Synthesize photorealistic 1024x1024 visual imagery, product mockups, and retail concept renders powered by SarembokVE Visual Synthesis Engine.
domain: frontier-vision
parameters:
  {
    "type": "object",
    "properties": {
      "prompt": {
        "type": "string",
        "description": "Descriptive visual prompt for photorealistic synthesis."
      },
      "width": {
        "type": "integer",
        "description": "Width of generated image in pixels (default: 1024).",
        "default": 1024
      },
      "height": {
        "type": "integer",
        "description": "Height of generated image in pixels (default: 1024).",
        "default": 1024
      }
    },
    "required": ["prompt"]
  }
---

# SarembokVE Visual Synthesis Engine
This skill executes high-fidelity image generation and 3D product mockups directly via the SarembokVE Neural Render Matrix.
Generates an interactive image card with 4K download link and instant lightbox view.
