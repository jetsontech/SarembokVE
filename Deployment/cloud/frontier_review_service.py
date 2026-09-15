"""Bounded frontier review service for Sarembok engineering work.

This is an engineering-review tool, not a runtime execution dependency. It sends
only the compact task/implementation/verification packet to configured reviewers
and returns independent findings for a human decision gate.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from frontier_review_council import ReviewModel, build_review_prompt, configured_review_models


def _request_json(url: str, headers: dict[str, str], payload: dict[str, Any], timeout: int) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={**headers, "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _review_openai(model: ReviewModel, prompt: str, timeout: int) -> str:
    payload = {
        "model": model.model_id,
        "messages": [
            {"role": "system", "content": "You are Sarembok's independent engineering review council. Return concrete findings, severity, evidence, and recommended correction. Do not invent repository facts."},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 4096,
        "temperature": 0.1,
    }
    data = _request_json(
        "https://api.openai.com/v1/chat/completions",
        {"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
        payload,
        timeout,
    )
    return str((((data.get("choices") or [{}])[0].get("message") or {}).get("content") or "")).strip()


def _review_anthropic(model: ReviewModel, prompt: str, timeout: int) -> str:
    payload = {
        "model": model.model_id,
        "max_tokens": 4096,
        "temperature": 0.1,
        "system": "You are Sarembok's independent engineering review council. Return concrete findings, severity, evidence, and recommended correction. Do not invent repository facts.",
        "messages": [{"role": "user", "content": prompt}],
    }
    data = _request_json(
        "https://api.anthropic.com/v1/messages",
        {
            "x-api-key": os.environ["ANTHROPIC_API_KEY"],
            "anthropic-version": "2023-06-01",
        },
        payload,
        timeout,
    )
    blocks = data.get("content") or []
    return "\n".join(str(block.get("text", "")) for block in blocks if isinstance(block, dict) and block.get("type") == "text").strip()


def run_frontier_review(*, task: str, implementation_summary: str, verification: str, timeout: int = 45) -> dict[str, Any]:
    prompt = build_review_prompt(task=task, implementation_summary=implementation_summary, verification=verification)
    reviews: list[dict[str, Any]] = []
    for model in configured_review_models():
        try:
            if model.provider == "OpenAI":
                text = _review_openai(model, prompt, timeout)
            else:
                text = _review_anthropic(model, prompt, timeout)
            reviews.append({"reviewer": model.name, "provider": model.provider, "model": model.model_id, "ok": True, "findings": text})
        except (urllib.error.URLError, TimeoutError, ValueError, RuntimeError) as exc:
            reviews.append({"reviewer": model.name, "provider": model.provider, "model": model.model_id, "ok": False, "error": f"{type(exc).__name__}: {exc}"})
    return {
        "enabled": bool(reviews),
        "mode": "independent-review-only",
        "humanDecisionGate": True,
        "reviewCount": len(reviews),
        "reviews": reviews,
    }
