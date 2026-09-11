---
name: generate_image
description: Synthesize photorealistic 1024x1024 visual imagery and concept renders powered by FLUX.1 Tensor Cores.
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

# Frontier Visual Synthesis Skill
This skill dispatches high-fidelity image generation to sovereign ComfyUI nodes, Fal.ai FLUX.1, or Together AI.
Generates an interactive image card with 4K download link and instant lightbox view.
