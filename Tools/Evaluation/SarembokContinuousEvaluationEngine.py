#!/usr/bin/env python3
"""
SarembokContinuousEvaluationEngine.py
Runtime evaluation daemon — consumes live decision record events via WebSocket
and computes rolling cognitive reliability metrics. Sarembok_VE v2.0.
"""

import asyncio
import json
import os
import sys
import time
from collections import deque
from datetime import datetime, timezone

WS_HOST = "127.0.0.1"
WS_PORT = 9000
WINDOW_SIZE = 500          # rolling window of decisions
REPORT_INTERVAL_SEC = 30   # emit scorecard every N seconds
REGRESSION_BASELINE = 0.945  # v1.9 certified baseline

class CognitiveReliabilityTracker:
    def __init__(self, window: int = WINDOW_SIZE):
        self.decisions       = deque(maxlen=window)
        self.latencies_ms    = deque(maxlen=window)
        self.goal_outcomes   = deque(maxlen=window)
        self.policy_decisions = deque(maxlen=window)
        self.confidence_scores = deque(maxlen=window)
        self.memory_hits     = deque(maxlen=window)
        self.llm_used        = deque(maxlen=window)
        self.start_time      = time.time()
        self.total_decisions = 0

    def record(self, event: dict):
        self.total_decisions += 1
        self.decisions.append(event)
        self.latencies_ms.append(event.get("latency_ms", 420.0))
        self.goal_outcomes.append(event.get("goal_success", True))
        self.policy_decisions.append(event.get("policy_result", "ALLOW"))
        self.confidence_scores.append(event.get("confidence", 0.90))
        self.memory_hits.append(event.get("memory_hit", True))
        self.llm_used.append(event.get("llm_used", True))

    def scorecard(self) -> dict:
        if not self.decisions:
            return {"overall": 0.0, "decisions": 0}

        sorted_latencies = sorted(self.latencies_ms)
        n = len(sorted_latencies)
        p50 = sorted_latencies[int(n * 0.50)] if n else 0.0
        p95 = sorted_latencies[int(n * 0.95)] if n else 0.0

        goal_success_rate  = sum(self.goal_outcomes) / len(self.goal_outcomes)
        policy_denial_rate = sum(1 for r in self.policy_decisions if r == "DENY") / len(self.policy_decisions)
        avg_confidence     = sum(self.confidence_scores) / len(self.confidence_scores)
        memory_hit_rate    = sum(self.memory_hits) / len(self.memory_hits)
        llm_use_rate       = sum(self.llm_used) / len(self.llm_used)

        # Overall reliability = weighted combination of key dimensions
        overall = (
            goal_success_rate      * 0.30 +
            avg_confidence         * 0.25 +
            memory_hit_rate        * 0.20 +
            (1.0 - policy_denial_rate) * 0.15 +
            (1.0 if p95 < 2000 else 0.5) * 0.10
        )

        regression = overall < REGRESSION_BASELINE
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "window_size": len(self.decisions),
            "total_decisions": self.total_decisions,
            "p50_latency_ms": round(p50, 1),
            "p95_latency_ms": round(p95, 1),
            "goal_success_rate": round(goal_success_rate, 4),
            "policy_denial_rate": round(policy_denial_rate, 4),
            "average_confidence": round(avg_confidence, 4),
            "memory_hit_rate": round(memory_hit_rate, 4),
            "llm_use_rate": round(llm_use_rate, 4),
            "overall_reliability": round(overall, 4),
            "baseline": REGRESSION_BASELINE,
            "regression_detected": regression,
            "status": "REGRESSION" if regression else "HEALTHY",
        }


tracker = CognitiveReliabilityTracker()


async def handle_decision_event(raw: str):
    try:
        event = json.loads(raw)
        if event.get("type") == "decision_record":
            tracker.record(event.get("payload", {}))
    except Exception:
        pass


async def emit_scorecard_loop():
    while True:
        await asyncio.sleep(REPORT_INTERVAL_SEC)
        sc = tracker.scorecard()
        print(f"\n[{sc['timestamp']}] CONTINUOUS EVALUATION SCORECARD")
        print(f"  Window          : {sc['window_size']} / {WINDOW_SIZE}")
        print(f"  Total decisions : {sc['total_decisions']}")
        print(f"  P50 latency     : {sc['p50_latency_ms']} ms")
        print(f"  P95 latency     : {sc['p95_latency_ms']} ms")
        print(f"  Goal success    : {sc['goal_success_rate'] * 100:.1f}%")
        print(f"  Policy denials  : {sc['policy_denial_rate'] * 100:.1f}%")
        print(f"  Avg confidence  : {sc['average_confidence']:.3f}")
        print(f"  Memory hit rate : {sc['memory_hit_rate'] * 100:.1f}%")
        print(f"  Overall         : {sc['overall_reliability'] * 100:.1f}%  (baseline {REGRESSION_BASELINE * 100:.1f}%)")
        print(f"  Status          : {sc['status']}")
        if sc["regression_detected"]:
            print("  ⚠ REGRESSION DETECTED — overall reliability below v1.9 baseline!")


async def connect_and_consume():
    try:
        import websockets
    except ImportError:
        print("[ERROR] websockets not installed. Run: pip install websockets")
        return

    uri = f"ws://{WS_HOST}:{WS_PORT}"
    print(f"[SAREMBOK][CONTINUOUS_EVAL] Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as ws:
            print("[SAREMBOK][CONTINUOUS_EVAL] Connected. Consuming decision record events...")
            # Subscribe to decision_record event stream
            subscribe = json.dumps({"protocol": "sarembok.v1", "command": "subscribe", "target": "DecisionRecords"})
            await ws.send(subscribe)
            async for message in ws:
                await handle_decision_event(message)
    except Exception as e:
        print(f"[WARN] WebSocket connection ended: {e}. Running in offline demo mode.")
        await demo_mode()


async def demo_mode():
    """Inject synthetic decision events to demonstrate the engine works standalone."""
    import random
    print("[SAREMBOK][CONTINUOUS_EVAL] DEMO MODE — injecting synthetic events...")
    for i in range(200):
        event = {
            "type": "decision_record",
            "payload": {
                "latency_ms": random.gauss(420, 80),
                "goal_success": random.random() > 0.07,
                "policy_result": "DENY" if random.random() < 0.015 else "ALLOW",
                "confidence": random.gauss(0.91, 0.06),
                "memory_hit": random.random() > 0.09,
                "llm_used": random.random() > 0.05,
            }
        }
        tracker.record(event["payload"])
        await asyncio.sleep(0.01)

    sc = tracker.scorecard()
    print(f"\n[DEMO] Final scorecard after {sc['total_decisions']} decisions:")
    print(f"  Overall reliability : {sc['overall_reliability'] * 100:.1f}%")
    print(f"  Goal success        : {sc['goal_success_rate'] * 100:.1f}%")
    print(f"  P95 latency         : {sc['p95_latency_ms']:.0f} ms")
    print(f"  Status              : {sc['status']}")
    return sc


async def main():
    print("============================================================")
    print("  SAREMBOK_VE v2.0 CONTINUOUS EVALUATION ENGINE             ")
    print(f"  Baseline: {REGRESSION_BASELINE * 100:.1f}% | Window: {WINDOW_SIZE} decisions")
    print("============================================================")

    if "--demo" in sys.argv:
        await demo_mode()
        return

    await asyncio.gather(
        connect_and_consume(),
        emit_scorecard_loop()
    )


if __name__ == "__main__":
    asyncio.run(main())
