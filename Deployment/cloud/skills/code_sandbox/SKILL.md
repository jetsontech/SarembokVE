---
name: execute_code
description: Execute Python, JavaScript, Shell, or SQL code inside an isolated sandboxed runtime and capture standard output and execution metrics.
domain: compute
parameters:
  {
    "type": "object",
    "properties": {
      "language": {
        "type": "string",
        "enum": ["python", "javascript", "bash", "sql"],
        "description": "Programming language of the code block."
      },
      "code": {
        "type": "string",
        "description": "Code string to execute in the sandbox."
      },
      "timeoutSeconds": {
        "type": "integer",
        "description": "Execution timeout limit in seconds (default 15).",
        "default": 15
      }
    },
    "required": ["language", "code"]
  }
---

# Code Sandbox Execution Skill
Runs code within containerized boundaries, capturing stdout, stderr, execution duration, and return codes.
