"""Test suite for Enterprise Streaming, CDC, Vector Database, Tracing, and Reasoning Engine."""

from __future__ import annotations

import asyncio
import os
import sys
import unittest

_CLOUD_DIR = os.path.dirname(os.path.abspath(__file__))
if _CLOUD_DIR not in sys.path:
    sys.path.insert(0, _CLOUD_DIR)

from sarembok_distributed_tracing import tracer, Span, generate_trace_id, generate_span_id
from sarembok_event_bus import event_bus, CloudEvent
from sarembok_cdc import cdc_pipeline, CDCOperation
from sarembok_vector_store import vector_store
from sarembok_reasoning_engine import reasoning_engine, DomainType
from server import dispatch


class TestDistributedTracing(unittest.TestCase):
    def setUp(self) -> None:
        tracer.clear()

    def test_trace_and_span_generation(self) -> None:
        t_id = generate_trace_id()
        s_id = generate_span_id()
        self.assertEqual(len(t_id), 32)
        self.assertEqual(len(s_id), 16)

    def test_w3c_traceparent_format_and_parsing(self) -> None:
        with tracer.start_span("test.parent") as parent:
            tp = parent.to_w3c_traceparent()
            self.assertTrue(tp.startswith("00-"))
            parsed = tracer.parse_traceparent(tp)
            self.assertIsNotNone(parsed)
            if parsed:
                trace_id, span_id = parsed
                self.assertEqual(trace_id, parent.trace_id)
                self.assertEqual(span_id, parent.span_id)

    def test_nested_span_hierarchy_and_retrieval(self) -> None:
        with tracer.start_span("root_op", attributes={"env": "production"}) as root:
            with tracer.start_span("child_op", attributes={"step": 1}) as child:
                self.assertEqual(child.trace_id, root.trace_id)
                self.assertEqual(child.parent_span_id, root.span_id)
                child.add_event("sub_step_done", {"items": 5})

        traces = tracer.get_traces(name_filter="child_op")
        self.assertTrue(len(traces) >= 1)
        self.assertEqual(traces[0]["name"], "child_op")
        self.assertEqual(traces[0]["attributes"]["step"], 1)
        self.assertEqual(len(traces[0]["events"]), 1)


class TestEventBusAndPubSub(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        event_bus.clear()

    async def test_cloudevents_conformance(self) -> None:
        evt = CloudEvent(
            event_type="sarembok.test.ping",
            source="unit_test",
            data={"status": "ok"},
            subject="health",
        )
        d = evt.to_dict()
        self.assertEqual(d["specversion"], "1.0")
        self.assertEqual(d["type"], "sarembok.test.ping")
        self.assertEqual(d["source"], "unit_test")
        self.assertEqual(d["data"]["status"], "ok")

    async def test_publish_and_subscribe(self) -> None:
        received = []

        async def handler(evt: CloudEvent) -> None:
            received.append(evt)

        event_bus.subscribe("sarembok.telemetry.metrics", handler)
        await event_bus.publish("sarembok.telemetry.metrics", {"cpu_percent": 42.5})

        self.assertEqual(len(received), 1)
        self.assertEqual(received[0].data["cpu_percent"], 42.5)

    async def test_wildcard_pattern_subscription(self) -> None:
        received_topics = []

        async def wildcard_handler(evt: CloudEvent) -> None:
            received_topics.append(evt.subject)

        event_bus.subscribe("sarembok.cdc.*", wildcard_handler)
        await event_bus.publish("sarembok.cdc.conversations", {"op": "c"}, subject="conversations")
        await event_bus.publish("sarembok.cdc.tasks", {"op": "u"}, subject="tasks")
        await event_bus.publish("sarembok.other.topic", {"op": "x"}, subject="other")

        self.assertEqual(received_topics, ["conversations", "tasks"])


class TestChangeDataCapture(unittest.IsolatedAsyncioTestCase):
    async def test_cdc_mutation_emission(self) -> None:
        rec = await cdc_pipeline.capture_insert(
            table="tasks",
            row={"task_id": "tsk_001", "status": "PENDING", "goal": "Index repository"}
        )
        self.assertEqual(rec.op, CDCOperation.CREATE)
        self.assertEqual(rec.table, "tasks")
        self.assertEqual(rec.after["task_id"], "tsk_001")
        self.assertIn("ts_ms", rec.to_dict())

    async def test_cdc_change_log_retrieval(self) -> None:
        await cdc_pipeline.capture_update(
            table="agents",
            before={"agent_id": "ag_1", "status": "IDLE"},
            after={"agent_id": "ag_1", "status": "BUSY"},
        )
        changes = cdc_pipeline.get_change_log(table="agents", limit=5)
        self.assertTrue(len(changes) >= 1)
        self.assertEqual(changes[-1]["op"], CDCOperation.UPDATE)
        self.assertEqual(changes[-1]["after"]["status"], "BUSY")


class TestVectorStoreAndSemanticRetrieval(unittest.TestCase):
    def setUp(self) -> None:
        vector_store.clear()

    def test_semantic_insert_and_query(self) -> None:
        vector_store.insert(
            collection="knowledge_base",
            record_id="doc_ue5",
            document="Unreal Engine 5 MetaHuman rendering with ARKit morph blendshapes and Pixel Streaming.",
            metadata={"domain": "unreal"}
        )
        vector_store.insert(
            collection="knowledge_base",
            record_id="doc_kafka",
            document="Apache Kafka distributed event streaming with Change Data Capture and pubsub pipelines.",
            metadata={"domain": "data"}
        )

        results = vector_store.query(
            collection="knowledge_base",
            query="MetaHuman blendshape facial animation",
            top_k=1
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], "doc_ue5")
        self.assertTrue(results[0]["score"] > 0.0)

    def test_metadata_filtering(self) -> None:
        vector_store.insert(
            collection="agent_memory",
            record_id="m1",
            document="System kernel checkpoint",
            metadata={"env": "prod"}
        )
        vector_store.insert(
            collection="agent_memory",
            record_id="m2",
            document="System kernel backup",
            metadata={"env": "dev"}
        )

        prod_results = vector_store.query(
            collection="agent_memory",
            query="System kernel",
            filter_metadata={"env": "prod"}
        )
        self.assertEqual(len(prod_results), 1)
        self.assertEqual(prod_results[0]["id"], "m1")


class TestReasoningEngineAndCrossDomain(unittest.TestCase):
    def test_domain_classification(self) -> None:
        ue_domains = reasoning_engine.classify_domains("Optimize MetaHuman Pixel Streaming in Unreal Engine 5")
        self.assertIn(DomainType.SIMULATION_UNREAL, ue_domains)

        data_domains = reasoning_engine.classify_domains("Set up Kafka CDC pipeline with vector semantic embeddings")
        self.assertIn(DomainType.KNOWLEDGE_ANALYTICS, data_domains)

    def test_cross_domain_context_synthesis(self) -> None:
        context = reasoning_engine.build_cross_domain_context(
            [DomainType.SIMULATION_UNREAL, DomainType.AUTONOMOUS_OPS],
            "Unreal Engine Docker deployment"
        )
        self.assertEqual(len(context["domain_titles"]), 2)
        self.assertTrue(len(context["domain_axioms"]) >= 4)

    def test_think_tag_parsing(self) -> None:
        raw_output = "<think>Step 1: check memory.\nStep 2: compute trajectory.</think>Here is the final execution plan."
        thought, answer = reasoning_engine.parse_reasoning_trace(raw_output)
        self.assertIsNotNone(thought)
        if thought:
            self.assertIn("compute trajectory", thought)
        self.assertEqual(answer, "Here is the final execution plan.")

    def test_plan_verification(self) -> None:
        unverified = reasoning_engine.verify_plan(["Deploy containers", "Mount volume"], "autonomous_ops")
        self.assertFalse(unverified["valid"])
        self.assertTrue(any("verification" in i.lower() for i in unverified["issues"]))

        verified = reasoning_engine.verify_plan(["Deploy containers", "Mount volume", "Verify health endpoint"], "autonomous_ops")
        self.assertTrue(verified["valid"])


class TestServerRPCEndpoints(unittest.TestCase):
    def test_rpc_get_traces(self) -> None:
        res = dispatch("GetTraces", {"limit": 10})
        self.assertIn("traces", res)
        self.assertIsInstance(res["traces"], list)

    def test_rpc_vector_insert_and_query(self) -> None:
        ins = dispatch("InsertVector", {
            "collection": "knowledge_base",
            "id": "rpc_vec_1",
            "document": "Change Data Capture streaming using Apache Kafka and Debezium.",
            "metadata": {"type": "architecture"}
        })
        self.assertTrue(ins.get("inserted"))

        qry = dispatch("QueryVectorStore", {
            "collection": "knowledge_base",
            "query": "Kafka streaming CDC",
            "top_k": 1
        })
        self.assertIn("results", qry)
        self.assertTrue(len(qry["results"]) >= 1)
        self.assertEqual(qry["results"][0]["id"], "rpc_vec_1")

    def test_rpc_reason_and_adapt(self) -> None:
        res = dispatch("ReasonAndAdapt", {
            "query": "Stream MetaHuman telemetry through Kafka CDC",
            "plan_steps": ["Configure Kafka", "Connect MetaHuman", "Verify stream latency"]
        })
        self.assertIn("classified_domains", res)
        self.assertIn("domain_context", res)
        self.assertTrue(res["verification"]["valid"])


if __name__ == "__main__":
    unittest.main()
