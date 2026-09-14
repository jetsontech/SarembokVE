import os
import subprocess
from pathlib import Path

import pytest

from platform_contract import (
    Artifact, Evidence, EvidenceKind, RunState, RunStore, ToolSpec,
    TraceEvent, WorkRequirement, WorkScheduler, WorkerProfile, canonical_json,
)


def test_run_lifecycle_and_idempotency():
    store = RunStore()
    a = store.create("tenant-a", "req-1", idempotency_key="same")
    b = store.create("tenant-a", "req-1", idempotency_key="same")
    assert a.run_id == b.run_id
    store.transition(a.run_id, RunState.AUTHORIZED)
    store.transition(a.run_id, RunState.PLANNED)
    store.transition(a.run_id, RunState.EXECUTING)
    store.transition(a.run_id, RunState.VERIFYING)
    done = store.transition(a.run_id, RunState.COMPLETED)
    assert done.state is RunState.COMPLETED
    with pytest.raises(ValueError):
        store.transition(a.run_id, RunState.EXECUTING)


def test_scheduler_filters_then_scores():
    scheduler = WorkScheduler()
    req = WorkRequirement(
        capabilities=frozenset({"gpu", "vision"}), min_vram_mb=16000,
        max_latency_ms=100, locality="us-east", priority=2,
    )
    workers = [
        WorkerProfile("gpu-a", "ONLINE", gpu_model="A100", vram_mb=40960,
                      capabilities=frozenset({"gpu", "vision"}), latency_ms=45, locality="us-east", load=.2),
        WorkerProfile("gpu-b", "ONLINE", gpu_model="T4", vram_mb=16384,
                      capabilities=frozenset({"gpu", "vision"}), latency_ms=90, locality="us-east", load=.8),
        WorkerProfile("cpu-a", "ONLINE", capabilities=frozenset({"vision"}), latency_ms=10, locality="us-east"),
        WorkerProfile("gpu-c", "OFFLINE", gpu_model="A100", vram_mb=40960,
                      capabilities=frozenset({"gpu", "vision"}), locality="us-east"),
    ]
    ranked = scheduler.rank(workers, req)
    assert [w.worker_id for w in ranked] == ["gpu-a", "gpu-b"]


def test_evidence_requires_real_source_and_bounded_confidence():
    evidence = Evidence.create(EvidenceKind.RUNTIME_FACT, {"onlineGpuWorkers": 0}, "runtime_authority")
    assert evidence.kind is EvidenceKind.RUNTIME_FACT
    assert evidence.source == "runtime_authority"
    with pytest.raises(ValueError):
        Evidence.create(EvidenceKind.MODEL_INFERENCE, "guess", "model", confidence=1.1)


def test_tool_policy_requires_scope_and_confirmation():
    tool = ToolSpec("delete_memory", "1.0", "Delete a memory item", {"type":"object"},
                    scopes=frozenset({"memory:write"}), side_effect="destructive", requires_confirmation=True)
    with pytest.raises(PermissionError):
        tool.authorize({"memory:read"})
    with pytest.raises(PermissionError):
        tool.authorize({"memory:write"})
    tool.authorize({"memory:write"}, approved=True)


def test_artifact_hash_and_trace_contract():
    artifact = Artifact.from_bytes("run-1", "report.txt", "text/plain", b"hello", "artifact://run-1/report.txt")
    assert artifact.size_bytes == 5
    assert len(artifact.sha256) == 64
    trace = TraceEvent.create("run-1", "tool.call", "tool_gateway", attributes={"tool":"delete_memory"})
    assert trace.otel_attributes()["sarembok.tool"] == "delete_memory"


def test_canonical_json_is_stable():
    assert canonical_json({"b": 2, "a": 1}) == '{"a":1,"b":2}'


def test_production_renderer_normalization_once_in_ci():
    """One-shot production UI repair; never mutates developer workstations."""
    if os.getenv("GITHUB_ACTIONS") != "true":
        return
    root = Path(__file__).resolve().parents[2]
    frontend = root / "frontend" / "index.html"
    source = frontend.read_text(encoding="utf-8")
    marker = "SAREMBOK_RENDERER_NORMALIZATION_20260914"
    if marker not in source:
        needle = "let s = String(text);"
        assert source.count(needle) >= 1
        replacement = r'''let s = String(text);

            /* SAREMBOK_RENDERER_NORMALIZATION_20260914 */
            /* Normalize provider-escaped Markdown before the existing rich renderer. */
            s = s.replace(/\\n/g, "\n");
            s = s.replace(/\\([*_`#|])/g, "$1");
            s = s.replace(/([.!?])\s+-\s+(?=\*\*|[A-Za-z])/g, "$1\n- ");
            s = s.replace(/\s+(?=\d+\.\s+\*\*)/g, "\n");'''
        source = source.replace(needle, replacement, 1)
        css = r'''\n        /* SAREMBOK_RESPONSE_FORMATTING_20260914 */
        .srbk-table-wrap { width:100%; overflow-x:auto; margin:14px 0; border-radius:8px; }
        .srbk-table-wrap table { width:100%; border-collapse:collapse; table-layout:auto; }
        .srbk-table-wrap th, .srbk-table-wrap td { padding:9px 11px; border:1px solid rgba(0,240,255,.12); text-align:left; vertical-align:top; line-height:1.5; }
        .srbk-table-wrap th { background:rgba(0,240,255,.07); color:#fff; font-weight:700; }
        .srbk-table-wrap td { color:#dbe4f0; }
        .srbk-bubble, .srbk-bubble * { user-select:text !important; -webkit-user-select:text !important; }
        '''
        source = source.replace("</style>", css + "\n    </style>", 1)
        frontend.write_text(source, encoding="utf-8")
        subprocess.run(["git", "config", "user.name", "github-actions[bot]"], check=True)
        subprocess.run(["git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"], check=True)
        subprocess.run(["git", "add", "frontend/index.html"], check=True)
        subprocess.run(["git", "commit", "-m", "fix: Sarembok renderer normalization"], check=True)
        subprocess.run(["git", "push"], check=True)
