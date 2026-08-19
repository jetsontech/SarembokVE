"""Provider-neutral screen understanding contracts for Sarembok.

Turns OCR/object/UI detector output into normalized perception records. Actual
OCR and vision engines remain adapters so Sarembok is not tied to one vendor.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class ScreenRegion:
    region_id: str
    kind: str
    text: str = ""
    confidence: float = 0.0
    bounds: Optional[Dict[str, float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ScreenObservation:
    source_ref: str
    width: int
    height: int
    regions: List[ScreenRegion] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def text_regions(self) -> List[ScreenRegion]:
        return [r for r in self.regions if r.kind == "text" and r.text]

    @property
    def interactive_regions(self) -> List[ScreenRegion]:
        return [r for r in self.regions if r.kind in {"button", "input", "link", "menu"}]


class ScreenUnderstandingAdapter:
    """Interface implemented by OpenCV/OCR/OS/UI perception adapters."""

    def analyze(self, image_ref: str) -> ScreenObservation:
        raise NotImplementedError


class StaticScreenUnderstanding(ScreenUnderstandingAdapter):
    """Small deterministic adapter useful for integration tests and pipelines."""

    def analyze(self, image_ref: str) -> ScreenObservation:
        return ScreenObservation(
            source_ref=image_ref,
            width=0,
            height=0,
            metadata={"engine": "static", "privacy": "reference_only"},
        )


def observation_to_events(observation: ScreenObservation) -> List[Dict[str, Any]]:
    """Convert perception into agent-consumable normalized events."""
    events: List[Dict[str, Any]] = []
    for region in observation.regions:
        events.append(
            {
                "type": "screen.perception",
                "regionId": region.region_id,
                "kind": region.kind,
                "text": region.text,
                "confidence": region.confidence,
                "bounds": region.bounds,
                "sourceRef": observation.source_ref,
            }
        )
    return events
