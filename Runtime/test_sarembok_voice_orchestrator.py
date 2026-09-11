"""Unit and integration tests for Sarembok Multi-Agent Voice Orchestrator."""

import asyncio
import json
import os
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import websockets

from sarembok_voice_orchestrator import (
    AgentState,
    NetworkedOrchestrationEngine,
    handle_network_traffic
)


class VoiceOrchestratorTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        self.engine = NetworkedOrchestrationEngine(database_path=self.temp_db.name)

    async def asyncTearDown(self):
        if os.path.exists(self.temp_db.name):
            try:
                os.remove(self.temp_db.name)
            except OSError:
                pass

    async def test_ledger_initialization(self):
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='multi_agent_ledger'")
        table = cursor.fetchone()
        self.assertIsNotNone(table)
        self.assertEqual(table[0], "multi_agent_ledger")
        conn.close()

    async def test_single_turn_lifecycle(self):
        turn_data = {
            "turn_id": "T_TEST_001",
            "agent_id": "ARIA_Orchestrator",
            "text": "Diagnostics online.",
            "voice_model": "en-US-Studio-O"
        }
        # Execute turn with accelerated playback factor for fast testing
        success = await self.engine.execute_turn(turn_data, playback_speed_factor=0.01)
        self.assertTrue(success)

        # Verify ledger has state and audio payload
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()
        cursor.execute("SELECT state, audio_payload FROM multi_agent_ledger WHERE turn_id = ?", ("T_TEST_001",))
        row = cursor.fetchone()
        conn.close()

        self.assertIsNotNone(row)
        self.assertEqual(row[0], AgentState.IDLE)
        self.assertIsNotNone(row[1])
        self.assertTrue(len(row[1]) > 0)

    async def test_turn_interruption_via_trigger(self):
        await self.engine.queue_turn(
            turn_id="T_INT_001",
            agent_id="ARIA_Orchestrator",
            text="Long speech that will be interrupted before finishing completely."
        )
        await self.engine.queue_turn(
            turn_id="T_INT_002",
            agent_id="Worker_03_Analyst",
            text="This turn should be drained and discarded."
        )

        async def interrupt_after_delay():
            await asyncio.sleep(0.08)
            self.engine.trigger_global_interrupt("T_INT_001")

        orchestration_task = asyncio.create_task(self.engine.orchestration_loop())
        interrupt_task = asyncio.create_task(interrupt_after_delay())

        await asyncio.gather(orchestration_task, interrupt_task)

        # Check that T_INT_001 was marked INTERRUPTED
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()
        cursor.execute("SELECT state, interrupt_flag FROM multi_agent_ledger WHERE turn_id = ?", ("T_INT_001",))
        row = cursor.fetchone()
        conn.close()

        self.assertIsNotNone(row)
        self.assertEqual(row[0], AgentState.INTERRUPTED)

        # Check queue drained: T_INT_002 was not executed
        self.assertTrue(self.engine.dialogue_queue.empty())

    async def test_websocket_interrupt_handling(self):
        # Start a local test websocket server on a dynamic port
        server = await websockets.serve(
            lambda ws: handle_network_traffic(ws, self.engine),
            "127.0.0.1",
            8769
        )

        try:
            async with websockets.connect("ws://127.0.0.1:8769") as ws:
                # Receive initial status
                msg = await ws.recv()
                self.assertIn("INITIAL_STATUS", msg)

                # Queue a turn via websocket
                await ws.send('{"command": "QUEUE_TURN", "turn_id": "WS_01", "agent_id": "ARIA", "text": "Testing websocket."}')
                queue_ack = await ws.recv()
                self.assertIn("QUEUE_ACK", queue_ack)

                # Start orchestration
                orch_task = asyncio.create_task(self.engine.orchestration_loop())

                # Give it a moment to enter synthesize/playing
                await asyncio.sleep(0.04)

                # Send interrupt and collect responses until INTERRUPT_ACK is received
                await ws.send('{"command": "INTERRUPTED"}')
                received_types = []
                for _ in range(5):
                    raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    data = json.loads(raw)
                    received_types.append(data.get("type"))
                    if data.get("type") == "INTERRUPT_ACK":
                        break

                self.assertIn("INTERRUPT_ACK", received_types)

                await orch_task

                # Check that active turn was recorded
                conn = sqlite3.connect(self.temp_db.name)
                cursor = conn.cursor()
                cursor.execute("SELECT state FROM multi_agent_ledger WHERE turn_id = 'WS_01'")
                res = cursor.fetchone()
                conn.close()

                self.assertIsNotNone(res)
                self.assertIn(res[0], (AgentState.INTERRUPTED, AgentState.IDLE))
        finally:
            server.close()
            await server.wait_closed()


if __name__ == "__main__":
    unittest.main()
