---
name: spatial_visual_recall
description: Query or register spatial visual memory observations, items, objects, or notes seen via the Astra camera or screen perception pipeline (e.g., 'where did I put my keys?', 'what was on the whiteboard?').
parameters:
  action:
    type: string
    description: Action to perform - 'query' to search visual memory, or 'record' to store a visual observation.
    required: true
  query:
    type: string
    description: Visual item or object description to search for (for 'query' action).
  observation:
    type: string
    description: Visual observation description and location (for 'record' action).
  location:
    type: string
    description: Location tag or bounding area where item was observed.
---

# Spatial Visual Recall Skill (Astra-Grade Memory)

Maintains an episodic log of spatial observations captured via Sarembok's Astra camera and screen perception feeds.

## Operational Workflow
1. When the user asks where an object was seen or what was visible earlier, query the SQLite episodic memory with the keyword.
2. When a frame is analyzed containing distinct named objects, landmarks, or text notes, record the item with timestamp and spatial coordinates.
