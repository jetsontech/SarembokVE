"""Sarembok VE Dynamic Skills Engine.

Discovers, parses, and executes modular skills structured according to the
SKILL.md frontier standard (YAML frontmatter + Markdown instructions).

Important: discovery is not execution. A skill without a registered handler
must never be reported as successfully executed.
"""
from __future__ import annotations

import json
import logging
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
        return {"type": "function", "function": {"name": self.name, "description": self.description, "parameters": self.parameters if self.parameters else {"type": "object", "properties": {}}}}

    def to_mcp_tool(self) -> dict[str, Any]:
        return {"name": self.name, "description": self.description, "inputSchema": self.parameters if self.parameters else {"type": "object", "properties": {}}}


class SkillsEngine:
    def __init__(self, skills_dir: str | Path | None = None) -> None:
        base = Path(__file__).resolve().parent
        self.skills_dir = Path(skills_dir or base / "skills")
        self._skills: dict[str, SkillDefinition] = {}
        self._handlers: dict[str, Callable[[dict[str, Any], dict[str, Any]], Any]] = {}
        self._load_skills()

    def register_handler(self, skill_name: str, handler: Callable[[dict[str, Any], dict[str, Any]], Any]) -> None:
        self._handlers[skill_name] = handler

    def _parse_frontmatter(self, text: str) -> tuple[dict[str, Any], str]:
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.DOTALL)
        if not match:
            return {}, text
        raw_fm, body = match.group(1), match.group(2)
        meta: dict[str, Any] = {}
        try:
            in_params = False
            param_lines: list[str] = []
            for line in raw_fm.splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                if ":" in line and not in_params:
                    k, v = line.split(":", 1)
                    k, v = k.strip(), v.strip()
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
                try:
                    meta["parameters"] = json.loads("\n".join(param_lines).strip())
                except Exception:
                    meta["parameters"] = {"type": "object", "properties": {}}
        except Exception as exc:
            logger.warning("Error parsing SKILL.md frontmatter: %s", exc)
        return meta, body.strip()

    def _load_skills(self) -> None:
        self._skills.clear()
        if not self.skills_dir.exists():
            return
        for entry in self.skills_dir.iterdir():
            if not entry.is_dir():
                continue
            skill_file = entry / "SKILL.md"
            if not skill_file.exists():
                continue
            try:
                content = skill_file.read_text(encoding="utf-8")
                meta, body = self._parse_frontmatter(content)
                name = meta.get("name", entry.name)
                self._skills[name] = SkillDefinition(name=name, description=meta.get("description", f"Autonomous skill for {name}"), domain=meta.get("domain", "general"), parameters=meta.get("parameters", {"type": "object", "properties": {}}), instructions=body, skill_dir=str(entry), metadata=meta)
                logger.info("Loaded skill: %s", name)
            except Exception as exc:
                logger.error("Failed to load skill from %s: %s", skill_file, exc)

    def reload(self) -> int:
        self._load_skills()
        return len(self._skills)

    def list_skills(self) -> list[SkillDefinition]:
        return list(self._skills.values())

    def get_skill(self, name: str) -> SkillDefinition | None:
        return self._skills.get(name)

    def get_openai_tools(self) -> list[dict[str, Any]]:
        tools = [skill.to_openai_tool() for skill in self._skills.values() if skill.enabled]
        try:
            try:
                from mcp_client import get_mcp_client_manager
            except ImportError:
                try:
                    from Deployment.cloud.mcp_client import get_mcp_client_manager
                except ImportError:
                    from .mcp_client import get_mcp_client_manager
            for et in get_mcp_client_manager().get_all_external_tools():
                tools.append({"type": "function", "function": {"name": et["name"], "description": et.get("description", f"External MCP tool from {et.get('mcp_server')}"), "parameters": et.get("inputSchema", {"type": "object", "properties": {}})}})
        except Exception as exc:
            logger.debug("External MCP tools unavailable: %s", exc)
        return tools

    def get_mcp_tools(self) -> list[dict[str, Any]]:
        return [skill.to_mcp_tool() for skill in self._skills.values() if skill.enabled]

    def skill_status(self, name: str) -> dict[str, Any]:
        skill = self._skills.get(name)
        if not skill:
            return {"name": name, "status": "NOT_FOUND"}
        if not skill.enabled:
            return {"name": name, "status": "DISABLED"}
        if name in self._handlers:
            return {"name": name, "status": "EXECUTABLE", "domain": skill.domain}
        return {"name": name, "status": "DISCOVERED", "domain": skill.domain}

    def execute_skill(self, name: str, arguments: dict[str, Any] | None = None, context: dict[str, Any] | None = None) -> dict[str, Any]:
        args = arguments or {}
        ctx = context or {}
        if name.startswith("mcp_"):
            try:
                try:
                    from mcp_client import get_mcp_client_manager
                except ImportError:
                    try:
                        from Deployment.cloud.mcp_client import get_mcp_client_manager
                    except ImportError:
                        from .mcp_client import get_mcp_client_manager
                mgr = get_mcp_client_manager()
                for et in mgr.get_all_external_tools():
                    if et["name"] == name:
                        out = mgr.call_external_tool(et["mcp_server"], et["mcp_original_name"], args)
                        return {"success": True, "skill": name, "status": "EXECUTED", "output": out}
                return {"success": False, "skill": name, "error": f"External MCP tool '{name}' not found."}
            except Exception as exc:
                return {"success": False, "skill": name, "error": f"External MCP call failed: {exc}"}
        skill = self._skills.get(name)
        if not skill:
            return {"success": False, "error": f"Skill '{name}' not found in registered skills.", "availableSkills": list(self._skills.keys())}
        if not skill.enabled:
            return {"success": False, "skill": name, "status": "DISABLED", "error": f"Skill '{name}' is disabled."}
        handler = self._handlers.get(name)
        if not handler:
            return {"success": False, "skill": name, "status": "DISCOVERED", "error": f"Skill '{name}' is discovered but has no executable handler."}
        try:
            return {"success": True, "skill": name, "status": "EXECUTED", "output": handler(args, ctx)}
        except Exception as exc:
            logger.error("Error executing handler for skill %s: %s", name, exc)
            return {"success": False, "skill": name, "status": "FAILED", "error": str(exc)}


_GLOBAL_SKILLS_ENGINE: SkillsEngine | None = None


def get_skills_engine() -> SkillsEngine:
    global _GLOBAL_SKILLS_ENGINE
    if _GLOBAL_SKILLS_ENGINE is None:
        _GLOBAL_SKILLS_ENGINE = SkillsEngine()
    return _GLOBAL_SKILLS_ENGINE
