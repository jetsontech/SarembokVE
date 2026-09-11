"""Sarembok VE Dynamic Skills Engine.

Discovers, parses, and executes modular skills structured according to the
SKILL.md frontier standard (YAML frontmatter + Markdown instructions).
"""
from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger("sarembok.skills_engine")


@dataclass
class SkillDefinition:
    name: str
    description: str
    domain: str
    parameters: dict[str, Any]
    instructions: str
    skill_dir: str
    enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_openai_tool(self) -> dict[str, Any]:
        """Format as an OpenAI / Gemini / Anthropic compatible function tool."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters if self.parameters else {
                    "type": "object",
                    "properties": {},
                },
            },
        }

    def to_mcp_tool(self) -> dict[str, Any]:
        """Format as a standard Model Context Protocol (MCP) tool schema."""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.parameters if self.parameters else {
                "type": "object",
                "properties": {},
            },
        }


class SkillsEngine:
    def __init__(self, skills_dir: str | Path | None = None) -> None:
        if skills_dir is None:
            base = Path(__file__).resolve().parent
            skills_dir = base / "skills"
        self.skills_dir = Path(skills_dir)
        self._skills: dict[str, SkillDefinition] = {}
        self._handlers: dict[str, Callable[[dict[str, Any], dict[str, Any]], Any]] = {}
        self._load_skills()

    def register_handler(self, skill_name: str, handler: Callable[[dict[str, Any], dict[str, Any]], Any]) -> None:
        """Register a native Python execution handler for a skill."""
        self._handlers[skill_name] = handler

    def _parse_frontmatter(self, text: str) -> tuple[dict[str, Any], str]:
        """Parse YAML/JSON style frontmatter delimited by ---."""
        pattern = r"^---\s*\n(.*?)\n---\s*\n(.*)$"
        match = re.match(pattern, text, re.DOTALL)
        if not match:
            return {}, text

        raw_fm, body = match.group(1), match.group(2)
        meta: dict[str, Any] = {}

        try:
            in_params = False
            param_lines = []

            for line in raw_fm.splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue

                if ":" in line and not in_params:
                    parts = line.split(":", 1)
                    k = parts[0].strip()
                    v = parts[1].strip()
                    if k == "parameters":
                        in_params = True
                        if v:
                            param_lines.append(v)
                    else:
                        if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
                            v = v[1:-1]
                        meta[k] = v
                elif in_params:
                    param_lines.append(line)

            if in_params and param_lines:
                param_text = "\n".join(param_lines).strip()
                try:
                    meta["parameters"] = json.loads(param_text)
                except Exception:
                    meta["parameters"] = {"type": "object", "properties": {}}

        except Exception as exc:
            logger.warning("Error parsing SKILL.md frontmatter: %s", exc)

        return meta, body.strip()

    def _load_skills(self) -> None:
        """Scan skills_dir and load all valid SKILL.md files."""
        self._skills.clear()
        if not self.skills_dir.exists():
            return

        for entry in self.skills_dir.iterdir():
            if entry.is_dir():
                skill_file = entry / "SKILL.md"
                if skill_file.exists():
                    try:
                        content = skill_file.read_text(encoding="utf-8")
                        meta, body = self._parse_frontmatter(content)
                        name = meta.get("name", entry.name)
                        desc = meta.get("description", f"Autonomous skill for {name}")
                        domain = meta.get("domain", "general")
                        params = meta.get("parameters", {"type": "object", "properties": {}})

                        skill = SkillDefinition(
                            name=name,
                            description=desc,
                            domain=domain,
                            parameters=params,
                            instructions=body,
                            skill_dir=str(entry),
                            metadata=meta,
                        )
                        self._skills[name] = skill
                        logger.info("Loaded skill: %s (domain=%s)", name, domain)
                    except Exception as exc:
                        logger.error("Failed to load skill from %s: %s", skill_file, exc)

    def reload(self) -> int:
        """Hot-reload all skills from disk."""
        self._load_skills()
        return len(self._skills)

    def list_skills(self) -> list[SkillDefinition]:
        return list(self._skills.values())

    def get_skill(self, name: str) -> SkillDefinition | None:
        return self._skills.get(name)

    def get_openai_tools(self) -> list[dict[str, Any]]:
        """Return function calling schema list for OpenAI / Gemini / Groq / Anthropic."""
        return [skill.to_openai_tool() for skill in self._skills.values() if skill.enabled]

    def get_mcp_tools(self) -> list[dict[str, Any]]:
        """Return MCP tools list conforming to Model Context Protocol specification."""
        return [skill.to_mcp_tool() for skill in self._skills.values() if skill.enabled]

    def execute_skill(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute a skill by name with arguments and context."""
        skill = self._skills.get(name)
        if not skill:
            return {
                "success": False,
                "error": f"Skill '{name}' not found in registered skills.",
                "availableSkills": list(self._skills.keys()),
            }

        args = arguments or {}
        ctx = context or {}

        # 1. Custom native execution handler
        handler = self._handlers.get(name)
        if handler:
            try:
                result = handler(args, ctx)
                return {
                    "success": True,
                    "skill": name,
                    "output": result,
                }
            except Exception as exc:
                logger.error("Error executing handler for skill %s: %s", name, exc)
                return {
                    "success": False,
                    "skill": name,
                    "error": str(exc),
                }

        # 2. Default execution dispatch
        return {
            "success": True,
            "skill": name,
            "output": f"Executed skill '{name}' with arguments: {args}",
        }


# Global singleton instance
_GLOBAL_SKILLS_ENGINE: SkillsEngine | None = None


def get_skills_engine() -> SkillsEngine:
    global _GLOBAL_SKILLS_ENGINE
    if _GLOBAL_SKILLS_ENGINE is None:
        _GLOBAL_SKILLS_ENGINE = SkillsEngine()
    return _GLOBAL_SKILLS_ENGINE
