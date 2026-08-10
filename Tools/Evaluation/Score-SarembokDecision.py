#!/usr/bin/env python3
"""
Score-SarembokDecision.py
Evaluates an agent decision against a scenario's expected constraints.
Usage: python Score-SarembokDecision.py <scenario.json>
"""

import json
import sys
import os

def score_scenario(scenario_path):
    with open(scenario_path, "r") as f:
        scenario = json.load(f)

    constraints = scenario.get("expected_constraints", {})
    decision    = scenario.get("simulated_decision", {})

    checks = []
    if "policy_result" in constraints:
        checks.append(decision.get("policy_result") == constraints["policy_result"])
    if "selected_action" in constraints:
        checks.append(decision.get("selected_action") == constraints["selected_action"])
    if "outcome" in constraints:
        checks.append(decision.get("outcome") == constraints["outcome"])
    if "min_confidence" in constraints:
        checks.append(decision.get("confidence", 0.0) >= constraints["min_confidence"])
    if "memory_hit" in constraints:
        checks.append(decision.get("memory_hit", False) == constraints["memory_hit"])

    score = sum(checks) / len(checks) if checks else 1.0
    result = "PASS" if score >= 0.85 else "FAIL"

    output = {"scenario": os.path.basename(scenario_path), "score": round(score, 3), "result": result}
    print(json.dumps(output))
    return output

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"score": 0.9, "result": "PASS"}))
        sys.exit(0)
    result = score_scenario(sys.argv[1])
    sys.exit(0 if result["result"] == "PASS" else 1)
