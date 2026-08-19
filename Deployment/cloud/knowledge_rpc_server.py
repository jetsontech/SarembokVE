"""Production JSON-RPC entrypoint that bridges cloud dispatch to persistent knowledge APIs."""
from __future__ import annotations

import asyncio
import sys

sys.path.insert(0, "/app/Runtime")

import server as cloud_server
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
