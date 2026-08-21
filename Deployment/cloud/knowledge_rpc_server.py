"""Production JSON-RPC entrypoint that bridges cloud dispatch to persistent knowledge APIs."""
from __future__ import annotations

import asyncio
import importlib.util
import sys

# The production control-plane server lives at /app/server.py.
# Do not import Runtime/server.py here: that is the local runtime's legacy
# WebSocket server on port 8765 and does not expose the cloud gateway contract.
CLOUD_SERVER_PATH = "/app/server.py"
spec = importlib.util.spec_from_file_location("sarembok_cloud_server", CLOUD_SERVER_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Unable to load cloud server: {CLOUD_SERVER_PATH}")
cloud_server = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = cloud_server
spec.loader.exec_module(cloud_server)

sys.path.insert(0, "/app/Runtime")
from sarembok_knowledge_api import KnowledgeRuntimeAPI
from sarembok_knowledge_runtime import PersistentKnowledgeRuntime


knowledge_runtime = PersistentKnowledgeRuntime(cloud_server.DB_PATH)
knowledge_api = KnowledgeRuntimeAPI(knowledge_runtime)
_original_dispatch = cloud_server.dispatch


def dispatch(method: str, params: dict) -> dict:
    if method in KnowledgeRuntimeAPI.METHODS:
        return knowledge_api.dispatch(method, params)
    return _original_dispatch(method, params)


cloud_server.dispatch = dispatch


if __name__ == "__main__":
    asyncio.run(cloud_server.main())
