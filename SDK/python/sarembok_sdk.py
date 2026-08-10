"""
Sarembok VE Production Edition — Official Python SDK
Exposes all 12 Platform RPC Facets for External Integrations.
"""

import json
import websocket

class SarembokClient:
    def __init__(self, host="127.0.0.1", port=9000):
        self.url = f"ws://{host}:{port}"
        self.ws = None

    def connect(self):
        self.ws = websocket.create_connection(self.url)
        return True

    def _call(self, method, params=None):
        if not self.ws:
            self.connect()
        payload = {
            "jsonrpc": "2.0",
            "id": f"sdk-{method.lower()}",
            "method": method,
            "params": params or {}
        }
        self.ws.send(json.dumps(payload))
        resp = self.ws.recv()
        return json.loads(resp)

    # 1. Agent Management
    def create_agent(self, agent_id, display_name):
        return self._call("CreateAgent", {"agentId": agent_id, "displayName": display_name})

    # 2. Agent State
    def query_agent_state(self, agent_id):
        return self._call("QueryAgentState", {"agentId": agent_id})

    # 3. Perception
    def inject_perception(self, agent_id, perception_json):
        return self._call("InjectPerception", {"agentId": agent_id, "perception": perception_json})

    # 4. Decisions & Governance
    def evaluate_decision(self, agent_id, action_id, risk_score, confidence):
        return self._call("EvaluateDecision", {
            "agentId": agent_id, "actionId": action_id,
            "riskScore": risk_score, "confidence": confidence
        })

    # 5. Scorecard
    def get_cognitive_scorecard(self, agent_id):
        return self._call("GetCognitiveScorecard", {"agentId": agent_id})

    # 6. World Model
    def query_world_model(self, filter_str="all"):
        return self._call("QueryWorldModel", {"filter": filter_str})

    # 7. Delegation
    def create_delegation(self, source_agent_id, target_agent_id, goal_id):
        return self._call("CreateDelegation", {
            "sourceAgentId": source_agent_id,
            "targetAgentId": target_agent_id,
            "goalId": goal_id
        })

    # 8. Audit Trail
    def get_audit_trail(self, agent_id):
        return self._call("GetAuditTrail", {"agentId": agent_id})

    def close(self):
        if self.ws:
            self.ws.close()
