# Sarembok VE Production Edition — External Platform SDKs

The official SDK libraries for interacting with **Sarembok VE Production Edition** via JSON-RPC 2.0 over WebSocket (`ws://127.0.0.1:9000`).

---

## Supported SDK Languages

- **Python**: [SDK/python/sarembok_sdk.py](file:///c:/Sarembok_VE/SDK/python/sarembok_sdk.py)
- **TypeScript / JavaScript**: [SDK/typescript/sarembok_sdk.ts](file:///c:/Sarembok_VE/SDK/typescript/sarembok_sdk.ts)

---

## 12 Platform RPC Facets

| RPC Method | Description | Parameters |
| :--- | :--- | :--- |
| `CreateAgent` | Spawns and registers a new agent identity profile | `agentId`, `displayName` |
| `QueryAgentState` | Queries cognitive cycle stage and reliability | `agentId` |
| `InjectPerception` | Pushes vision/audio stimuli into cognitive engine | `agentId`, `perception` |
| `EvaluateDecision` | Runs multi-factor governance check | `agentId`, `actionId`, `riskScore`, `confidence` |
| `GetCognitiveScorecard` | Retrieves cognitive scorecard breakdown (94.5%) | `agentId` |
| `QueryWorldModel` | Queries spatial-temporal-belief entities | `filter` |
| `CreateDelegation` | Submits task delegation between agents | `sourceAgentId`, `targetAgentId`, `goalId` |
| `GetAuditTrail` | Retrieves cryptographic governance decision trail | `agentId` |

---

## Usage Example (Python)

```python
from sarembok_sdk import SarembokClient

client = SarembokClient(host="127.0.0.1", port=9000)
client.connect()

# Create Agent
res = client.create_agent("agent-prime", "Sarembok Prime")
print(res)

# Query Scorecard
scorecard = client.get_cognitive_scorecard("agent-prime")
print(scorecard)

client.close()
```
