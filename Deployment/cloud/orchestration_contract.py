"""Typed, deterministic orchestration graph validation for SarembokVE."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

VALID_STATES = {"PENDING", "READY", "RUNNING", "SUCCEEDED", "FAILED", "CANCELLED", "BLOCKED"}

@dataclass(frozen=True)
class GraphNode:
    node_id: str
    operation: str
    depends_on: tuple[str, ...] = ()
    timeout_seconds: int = 300
    required_capabilities: tuple[str, ...] = ()
    state: str = "PENDING"

@dataclass(frozen=True)
class ExecutionGraph:
    graph_id: str
    nodes: tuple[GraphNode, ...]
    metadata: dict[str, Any] = field(default_factory=dict)


def validate_graph(graph: ExecutionGraph) -> list[str]:
    errors: list[str] = []
    ids = [n.node_id for n in graph.nodes]
    if not graph.graph_id.strip(): errors.append("graph_id_required")
    if len(ids) != len(set(ids)): errors.append("duplicate_node_id")
    known = set(ids)
    for node in graph.nodes:
        if not node.node_id.strip(): errors.append("node_id_required")
        if not node.operation.strip(): errors.append(f"operation_required:{node.node_id}")
        if node.timeout_seconds < 1 or node.timeout_seconds > 86400: errors.append(f"invalid_timeout:{node.node_id}")
        if node.state not in VALID_STATES: errors.append(f"invalid_state:{node.node_id}")
        for dep in node.depends_on:
            if dep not in known: errors.append(f"unknown_dependency:{node.node_id}:{dep}")
    # Kahn topological validation; cycles are execution-deadlocks and must fail before dispatch.
    indegree = {n.node_id: 0 for n in graph.nodes}
    edges = {n.node_id: [] for n in graph.nodes}
    for n in graph.nodes:
        for dep in n.depends_on:
            indegree[n.node_id] += 1
            edges[dep].append(n.node_id)
    queue = [k for k, v in indegree.items() if v == 0]
    visited = 0
    while queue:
        cur = queue.pop()
        visited += 1
        for nxt in edges[cur]:
            indegree[nxt] -= 1
            if indegree[nxt] == 0: queue.append(nxt)
    if visited != len(indegree): errors.append("dependency_cycle")
    return errors


def ready_nodes(graph: ExecutionGraph) -> list[str]:
    states = {n.node_id: n.state for n in graph.nodes}
    out=[]
    for n in graph.nodes:
        if n.state not in {"PENDING", "READY"}: continue
        if all(states[d] == "SUCCEEDED" for d in n.depends_on): out.append(n.node_id)
    return out
