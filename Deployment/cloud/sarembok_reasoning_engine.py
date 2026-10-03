"""Sarembok Robust Reasoning Engine & Cross-Domain Adaptability System.

Orchestrates multi-phase chain-of-thought reasoning, self-correction verification loops,
and seamless cross-domain prompt synthesis across Unreal, Code, Knowledge, Robotics,
Creative Audio, and Cloud Operations.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from sarembok_distributed_tracing import tracer
from sarembok_vector_store import vector_store

LOG = logging.getLogger("sarembok.reasoning")


class DomainType:
    CODE_ARCHITECTURE = "code_and_architecture"
    SIMULATION_UNREAL = "simulation_and_unreal"
    KNOWLEDGE_ANALYTICS = "knowledge_and_analytics"
    ROBOTICS_EMBODIMENT = "robotics_and_embodiment"
    CREATIVE_VOICE = "creative_and_voice"
    AUTONOMOUS_OPS = "autonomous_ops_and_cloud"


# Domain characteristic keywords and axioms
DOMAIN_PROFILES: Dict[str, Dict[str, Any]] = {
    DomainType.CODE_ARCHITECTURE: {
        "title": "Systems Code & Architecture",
        "keywords": {"python", "c++", "rust", "javascript", "api", "database", "sql", "git", "backend", "frontend", "concurrency", "refactor"},
        "axioms": [
            "Enforce strict type safety, zero uncaught exceptions, and zero undefined behavior.",
            "Maintain modular boundary isolation between core logic and presentation adapters.",
            "Prioritize idempotent execution and reproducible deterministic builds."
        ],
    },
    DomainType.SIMULATION_UNREAL: {
        "title": "Simulation & Unreal Engine 5",
        "keywords": {"unreal", "ue5", "metahuman", "pixelstreaming", "blueprint", "render", "shader", "arkit", "morph", "mesh", "level", "pie"},
        "axioms": [
            "MetaHuman is a presentation layer, decoupled from intelligence and state authority.",
            "Render operations belong on GPU/client; state logic remains authoritative in the runtime.",
            "Pixel Streaming must manage WebRTC bitrate and NVENC hardware latency gracefully."
        ],
    },
    DomainType.KNOWLEDGE_ANALYTICS: {
        "title": "Knowledge Retrieval & Data Analytics",
        "keywords": {"vector", "embedding", "semantic", "rag", "retrieval", "cdc", "kafka", "pipeline", "etl", "dataset", "analytics", "memory"},
        "axioms": [
            "Ground claims in verified episodic and semantic memory vectors before generating output.",
            "Change Data Capture must preserve full causal transaction history and replay order.",
            "Semantic embeddings must cluster concepts with cosine consistency."
        ],
    },
    DomainType.ROBOTICS_EMBODIMENT: {
        "title": "Robotics & Spatial Embodiment",
        "keywords": {"viseme", "gaze", "head", "pose", "kinematics", "spatial", "perception", "servo", "motor", "actuator", "physics"},
        "axioms": [
            "Map facial visemes to 51 ARKit standard blendshapes with sub-50ms latency.",
            "Spatial collision prevention overrides artistic animation priorities.",
            "Attention and gaze vectors must orient toward the primary conversational locus."
        ],
    },
    DomainType.CREATIVE_VOICE: {
        "title": "Creative Voice & Media Synthesis",
        "keywords": {"tts", "kokoro", "audio", "speech", "voice", "stream", "music", "timbre", "pitch", "video", "youtube", "media"},
        "axioms": [
            "TTS voice synthesis must balance natural prosody with crisp enunciation at 24kHz.",
            "Media playback must provide non-blocking always-on-top picture-in-picture popouts.",
            "Gracefully fall back across audio backends without interrupting user dialogue."
        ],
    },
    DomainType.AUTONOMOUS_OPS: {
        "title": "Autonomous Operations & Infrastructure",
        "keywords": {"docker", "compose", "vps", "server", "linux", "cloud", "caddy", "nginx", "telemetry", "tracing", "opentelemetry", "pubsub"},
        "axioms": [
            "All services must run non-root, self-healing, and bounded by memory limits.",
            "Propagate W3C distributed traceparent headers across every network hop.",
            "Event pub/sub buffers must prevent memory leaks via bounded circular retention."
        ],
    },
}


class ReasoningEngine:
    """Multi-phase reasoning engine with cross-domain adaptability."""

    def __init__(self) -> None:
        pass

    def classify_domains(self, text: str) -> List[str]:
        """Classify input prompt into one or more operational domains with confidence weighting."""
        lower = text.lower()
        scores: Dict[str, int] = {}
        for domain, profile in DOMAIN_PROFILES.items():
            score = 0
            for kw in profile["keywords"]:
                if kw in lower:
                    score += 1
            if score > 0:
                scores[domain] = score

        if not scores:
            return [DomainType.CODE_ARCHITECTURE]

        # Sort domains descending by matching keyword count
        sorted_domains = sorted(scores.keys(), key=lambda d: scores[d], reverse=True)
        return sorted_domains

    def build_cross_domain_context(self, domains: List[str], query: str) -> Dict[str, Any]:
        """Synthesize domain profiles, axioms, and semantic memory vectors."""
        with tracer.start_span("reasoning.adapt_context", attributes={"domains": ",".join(domains)}):
            axioms: List[str] = []
            titles: List[str] = []

            for d in domains:
                profile = DOMAIN_PROFILES.get(d)
                if profile:
                    titles.append(profile["title"])
                    axioms.extend(profile["axioms"])

            # Semantic retrieval from vector store for relevant memories
            semantic_memories = vector_store.query(
                collection="knowledge_base",
                query=query,
                top_k=3,
                min_score=0.25,
            )

            return {
                "active_domains": domains,
                "domain_titles": titles,
                "domain_axioms": axioms,
                "retrieved_memories": semantic_memories,
            }

    def format_system_prompt(self, base_prompt: str, context: Dict[str, Any]) -> str:
        """Inject cross-domain adaptability directives into system prompt."""
        domain_str = " + ".join(context.get("domain_titles", []))
        axioms_str = "\n".join(f"- {a}" for a in context.get("domain_axioms", []))

        memories = context.get("retrieved_memories", [])
        memories_str = ""
        if memories:
            memories_str = "\n### RELEVANT SEMANTIC MEMORY CONTEXT:\n" + "\n".join(
                f"- [Score: {m['score']}] {m['document']}" for m in memories
            )

        adaptability_block = (
            f"\n\n[CROSS-DOMAIN ADAPTABILITY MODE: {domain_str}]\n"
            f"Apply the following domain axioms and operational rules to this task:\n"
            f"{axioms_str}\n"
            f"{memories_str}\n"
            f"\nReasoning Directive: Formulate a clear chain-of-thought, verify edge cases, "
            f"and provide robust, production-ready execution steps.\n"
        )
        return base_prompt + adaptability_block

    def parse_reasoning_trace(self, response_text: str) -> Tuple[Optional[str], str]:
        """Extract `<think>...</think>` internal reasoning block from public answer."""
        think_match = re.search(r"<think>(.*?)</think>", response_text, re.DOTALL)
        if think_match:
            thought = think_match.group(1).strip()
            answer = re.sub(r"<think>.*?</think>", "", response_text, flags=re.DOTALL).strip()
            return thought, answer
        return None, response_text

    def verify_plan(self, plan_steps: List[str], domain: str) -> Dict[str, Any]:
        """Perform automated self-correction and sanity verification on a proposed reasoning plan."""
        with tracer.start_span("reasoning.verify_plan", attributes={"domain": domain}):
            issues: List[str] = []
            if not plan_steps:
                issues.append("Plan contains zero actionable steps.")

            has_verification = any("verify" in s.lower() or "test" in s.lower() or "check" in s.lower() for s in plan_steps)
            if not has_verification:
                issues.append("Plan lacks an explicit verification or qualification step.")

            return {
                "valid": len(issues) == 0,
                "issues": issues,
                "step_count": len(plan_steps),
                "domain": domain,
            }


# Global singleton reasoning engine
reasoning_engine = ReasoningEngine()
