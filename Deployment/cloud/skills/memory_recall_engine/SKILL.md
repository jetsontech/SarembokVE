---
name: memory_recall
description: Query persistent SQLite-WAL episodic memory and historical user facts stored across sessions.
domain: memory
parameters:
  {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "Topic, user preference, or keyword to retrieve from long-term memory."
      },
      "limit": {
        "type": "integer",
        "description": "Maximum number of memory facts to return (default 5).",
        "default": 5
      }
    },
    "required": ["query"]
  }
---

# Persistent Memory Recall Skill
Retrieves persistent facts, architectural preferences, and cross-session knowledge stored in SQLite-WAL memory.
