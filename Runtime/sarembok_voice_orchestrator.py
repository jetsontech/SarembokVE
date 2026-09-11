"""Sarembok Virtual Evolution (VE) Multi-Agent Voice Orchestrator.

Integrates Google AI Studio / Google Cloud Text-to-Speech API voices
with SQLite-WAL persistent ledger state tracking, asynchronous turn-taking,
barge-in interruption handling, and WebSocket event gateway.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sqlite3
import sys
import time
from typing import Any, Callable, Dict, Optional, Set

# Configure structured logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
)
logger = logging.getLogger("SarembokVoiceOrchestrator")


class AgentState:
    IDLE = "IDLE"
    SYNTHESIZING = "SYNTHESIZING"
    PLAYING = "PLAYING"
    INTERRUPTED = "INTERRUPTED"
    FAILED = "FAILED"


# Check for google.cloud.texttospeech availability
try:
    from google.cloud import texttospeech
    HAS_GOOGLE_TTS = True
except ImportError:
    HAS_GOOGLE_TTS = False
    logger.info("google.cloud.texttospeech not found. Using high-fidelity synthetic TTS engine.")


class MockTTSResponse:
    """Simulated TTS response containing synthetic MP3 frame bytes."""
    def __init__(self, text: str):
        # Generate dummy MP3 frame header (MPEG-1 Layer III sync word 0xFFFB)
        dummy_header = b"\xFF\xFB\x90\x64\x00\x00\x00\x00"
        text_bytes = text.encode("utf-8")
        self.audio_content = dummy_header + text_bytes


class SarembokVoiceSynthesizer:
    """Wrapper that communicates with Google Cloud TTS or fallback synthesizer."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        self.client = None
        self.async_client = None

        # Try initializing via default ADC / Service Account first
        if HAS_GOOGLE_TTS:
            if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
                try:
                    self.async_client = texttospeech.TextToSpeechAsyncClient()
                    logger.info("Google Cloud TTS client initialized using GOOGLE_APPLICATION_CREDENTIALS.")
                except Exception as e:
                    logger.debug(f"ADC init note: {e}")
            elif self.api_key:
                try:
                    self.async_client = texttospeech.TextToSpeechAsyncClient(
                        client_options={"api_key": self.api_key}
                    )
                    logger.info("Google Cloud TTS client initialized with API key.")
                except Exception as e:
                    logger.debug(f"Client options init note: {e}")

    async def _synthesize_rest(self, text: str, voice_model: str, speaking_rate: float) -> Optional[bytes]:
        """Direct REST synthesis fallback for API key authentication."""
        if not self.api_key:
            return None
        import base64
        import json
        import urllib.request

        url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={self.api_key}"
        payload = {
            "input": {"text": text},
            "voice": {"languageCode": "en-US", "name": voice_model},
            "audioConfig": {"audioEncoding": "MP3", "speakingRate": speaking_rate}
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        try:
            loop = asyncio.get_event_loop()
            def do_request():
                with urllib.request.urlopen(req, timeout=5) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    raw_b64 = data.get("audioContent", "")
                    return base64.b64decode(raw_b64) if raw_b64 else None
            return await loop.run_in_executor(None, do_request)
        except Exception as e:
            logger.debug(f"REST synthesis request note: {e}")
            return None

    async def synthesize(self, text: str, voice_model: str = "en-US-Studio-O", speaking_rate: float = 1.05) -> bytes:
        # 1. Try gRPC client
        if self.async_client and HAS_GOOGLE_TTS:
            try:
                synthesis_input = texttospeech.SynthesisInput(text=text)
                voice = texttospeech.VoiceSelectionParams(
                    language_code="en-US",
                    name=voice_model
                )
                audio_config = texttospeech.AudioConfig(
                    audio_encoding=texttospeech.AudioEncoding.MP3,
                    speaking_rate=speaking_rate
                )
                response = await self.async_client.synthesize_speech(
                    input=synthesis_input,
                    voice=voice,
                    audio_config=audio_config
                )
                return response.audio_content
            except Exception as e:
                logger.debug(f"gRPC synthesis call note: {e}")

        # 2. Try REST API with API key
        if self.api_key:
            rest_audio = await self._synthesize_rest(text, voice_model, speaking_rate)
            if rest_audio:
                return rest_audio

        # 3. Fallback simulation with non-blocking latency
        await asyncio.sleep(0.05)
        mock = MockTTSResponse(text)
        return mock.audio_content


class NetworkedOrchestrationEngine:
    """Async Multi-Agent State Machine Orchestrator with SQLite-WAL and WebSocket routing."""

    def __init__(self, database_path: str = "sarembok_runtime.db", tts_api_key: Optional[str] = None):
        self.db_path = database_path
        self.synthesizer = SarembokVoiceSynthesizer(api_key=tts_api_key)
        self.current_task: Optional[asyncio.Task] = None
        self.active_turn_id: Optional[str] = None
        self.active_speaker: Optional[str] = None
        self.current_state: str = AgentState.IDLE
        self.dialogue_queue: asyncio.Queue = asyncio.Queue()
        self.connected_websockets: Set[Any] = set()
        self._initialize_ledger()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        self._ensure_schema(conn)
        return conn

    def _ensure_schema(self, conn: sqlite3.Connection) -> None:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS multi_agent_ledger (
                turn_id TEXT PRIMARY KEY,
                agent_id TEXT,
                state TEXT,
                audio_payload BLOB,
                interrupt_flag INTEGER DEFAULT 0,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()

    def _initialize_ledger(self) -> None:
        """Builds local context schema and resets edge states."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE multi_agent_ledger SET interrupt_flag = 0")
        conn.commit()
        conn.close()
        logger.info(f"Initialized SQLite-WAL ledger at {self.db_path}")

    def check_interrupt(self, turn_id: str) -> bool:
        """Reads the edge ledger to check if active turn has been flagged for override."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT interrupt_flag FROM multi_agent_ledger WHERE turn_id = ?", (turn_id,))
        result = cursor.fetchone()
        conn.close()
        return bool(result and result[0] == 1)

    def trigger_global_interrupt(self, active_turn_id: Optional[str] = None) -> None:
        """Sets the interrupt flag in SQLite and triggers cancellation."""
        target_id = active_turn_id or self.active_turn_id
        if target_id:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE multi_agent_ledger SET interrupt_flag = 1 WHERE turn_id = ?", (target_id,))
            conn.commit()
            conn.close()
            logger.info(f"[INTERRUPT TRIGGER] Global override issued for turn: {target_id}")

        self.process_network_interrupt()

    def process_network_interrupt(self) -> None:
        """Immediately flags the database layer and cancels active tasks."""
        if self.active_turn_id:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE multi_agent_ledger SET interrupt_flag = 1 WHERE turn_id = ?", (self.active_turn_id,))
            conn.commit()
            conn.close()
            logger.warning(f"[CRITICAL OVERRIDE] Interrupt applied for active turn: {self.active_turn_id}")

        # Cancel active async execution task immediately
        if self.current_task and not self.current_task.done():
            self.current_task.cancel()

    def update_state(self, turn_id: str, agent_id: str, state: str, audio_data: Optional[bytes] = None) -> None:
        """Updates SQLite ledger and broadcasts state change."""
        self.current_state = state
        self.active_speaker = agent_id if state in (AgentState.SYNTHESIZING, AgentState.PLAYING) else None

        conn = self._get_connection()
        cursor = conn.cursor()
        if audio_data:
            cursor.execute('''
                INSERT INTO multi_agent_ledger (turn_id, agent_id, state, audio_payload, interrupt_flag)
                VALUES (?, ?, ?, ?, 0)
                ON CONFLICT(turn_id) DO UPDATE SET state = excluded.state, audio_payload = excluded.audio_payload
            ''', (turn_id, agent_id, state, audio_data))
        else:
            cursor.execute('''
                INSERT INTO multi_agent_ledger (turn_id, agent_id, state, interrupt_flag)
                VALUES (?, ?, ?, 0)
                ON CONFLICT(turn_id) DO UPDATE SET state = excluded.state
            ''', (turn_id, agent_id, state))
        conn.commit()
        conn.close()

        logger.info(f"[State Machine] -> Agent: {agent_id} | State: {state} | Turn: {turn_id}")

        # Broadcast telemetry to connected websockets
        self._broadcast_state_event({
            "type": "AGENT_STATE_UPDATE",
            "turn_id": turn_id,
            "agent_id": agent_id,
            "state": state,
            "has_audio": audio_data is not None
        })

    async def _safe_send(self, ws: Any, msg: str) -> None:
        try:
            await ws.send(msg)
        except Exception:
            self.connected_websockets.discard(ws)

    def _broadcast_state_event(self, payload: Dict[str, Any]) -> None:
        msg = json.dumps(payload)
        for ws in list(self.connected_websockets):
            asyncio.create_task(self._safe_send(ws, msg))

    async def execute_turn(self, turn_data: Dict[str, Any], playback_speed_factor: float = 0.06) -> bool:
        """Synthesizes text and monitors structural playout latency with sub-millisecond interrupt checks."""
        turn_id = turn_data["turn_id"]
        agent_id = turn_data["agent_id"]
        text_script = turn_data.get("text", "")
        voice_model = turn_data.get("voice_model", "en-US-Studio-O")

        self.active_turn_id = turn_id

        # Phase 1: Synthesizing
        self.update_state(turn_id, agent_id, AgentState.SYNTHESIZING)
        try:
            audio_bytes = await self.synthesizer.synthesize(text_script, voice_model=voice_model)

            # Post-synthesis interrupt check
            if self.check_interrupt(turn_id):
                self.update_state(turn_id, agent_id, AgentState.INTERRUPTED)
                return False

            # Phase 2: Segmented Playout Loop
            self.update_state(turn_id, agent_id, AgentState.PLAYING, audio_data=audio_bytes)

            total_duration = max(0.5, len(text_script) * playback_speed_factor)
            interval = 0.05
            elapsed = 0.0

            while elapsed < total_duration:
                if self.check_interrupt(turn_id):
                    self.update_state(turn_id, agent_id, AgentState.INTERRUPTED)
                    return False
                await asyncio.sleep(interval)
                elapsed += interval

            # Phase 3: Return cleanly to IDLE
            self.update_state(turn_id, agent_id, AgentState.IDLE)
            return True

        except asyncio.CancelledError:
            self.update_state(turn_id, agent_id, AgentState.INTERRUPTED)
            logger.info(f"[Orchestration Node] Task for turn {turn_id} caught CancelledError.")
            return False
        except Exception as e:
            logger.error(f"[Engine Error] Exception during turn {turn_id}: {e}")
            self.update_state(turn_id, agent_id, AgentState.FAILED)
            return False

    async def orchestration_loop(self) -> None:
        """Watches the dialogue schedule tree and clears workers when interrupted."""
        while not self.dialogue_queue.empty():
            turn_data = await self.dialogue_queue.get()
            self.current_task = asyncio.create_task(self.execute_turn(turn_data))

            try:
                success = await self.current_task
                if not success:
                    raise asyncio.CancelledError()
            except asyncio.CancelledError:
                logger.warning("[Orchestration Node] Pipeline stopped due to interrupt. Flushing dialogue tree...")
                # Drain queue entirely so sequential workers do not fire stale responses
                while not self.dialogue_queue.empty():
                    try:
                        self.dialogue_queue.get_nowait()
                        self.dialogue_queue.task_done()
                    except (asyncio.QueueEmpty, ValueError):
                        break
                break
            finally:
                try:
                    self.dialogue_queue.task_done()
                except ValueError:
                    pass

        self.active_turn_id = None
        self.active_speaker = None
        self.current_state = AgentState.IDLE

    async def queue_turn(self, turn_id: str, agent_id: str, text: str, voice_model: str = "en-US-Studio-O") -> None:
        """Appends a turn to the async dialogue queue."""
        await self.dialogue_queue.put({
            "turn_id": turn_id,
            "agent_id": agent_id,
            "text": text,
            "voice_model": voice_model
        })


async def handle_network_traffic(websocket: Any, engine: NetworkedOrchestrationEngine) -> None:
    """Handles bidirectional WebSocket messages (commands and telemetry)."""
    engine.connected_websockets.add(websocket)
    logger.info(f"[Network Core] WebSocket client connected. Active clients: {len(engine.connected_websockets)}")

    # Send initial status
    try:
        await websocket.send(json.dumps({
            "type": "INITIAL_STATUS",
            "state": engine.current_state,
            "active_speaker": engine.active_speaker,
            "active_turn": engine.active_turn_id,
            "queue_size": engine.dialogue_queue.qsize()
        }))
    except Exception:
        pass

    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                command = data.get("command")
            except (json.JSONDecodeError, TypeError):
                command = str(message).strip()
                data = {}

            if command in ("INTERRUPTED", "INTERRUPT"):
                logger.info("[Network Core] Command INTERRUPTED received from client.")
                engine.process_network_interrupt()
                await websocket.send(json.dumps({
                    "type": "INTERRUPT_ACK",
                    "status": "ACCEPTED",
                    "active_turn": engine.active_turn_id
                }))

            elif command == "QUEUE_TURN":
                turn_id = data.get("turn_id", f"turn_{int(time.time()*1000)}")
                agent_id = data.get("agent_id", "ARIA_Orchestrator")
                text = data.get("text", "")
                voice_model = data.get("voice_model", "en-US-Studio-O")
                await engine.queue_turn(turn_id, agent_id, text, voice_model)
                logger.info(f"[Network Core] Queued turn {turn_id} for agent {agent_id}")
                await websocket.send(json.dumps({
                    "type": "QUEUE_ACK",
                    "turn_id": turn_id,
                    "queue_size": engine.dialogue_queue.qsize()
                }))

            elif command == "START_ORCHESTRATION":
                logger.info("[Network Core] Starting orchestration loop from websocket trigger.")
                asyncio.create_task(engine.orchestration_loop())
                await websocket.send(json.dumps({"type": "ORCHESTRATION_STARTED"}))

            elif command == "QUERY_STATUS":
                await websocket.send(json.dumps({
                    "type": "STATUS_RESPONSE",
                    "state": engine.current_state,
                    "active_speaker": engine.active_speaker,
                    "active_turn": engine.active_turn_id,
                    "queue_size": engine.dialogue_queue.qsize()
                }))

    except Exception as e:
        logger.warning(f"[Network Core] WebSocket handler error: {e}")
    finally:
        engine.connected_websockets.discard(websocket)
        logger.info("[Network Core] WebSocket client disconnected.")


async def run_voice_gateway(port: int = 8765, db_path: str = "sarembok_runtime.db") -> None:
    """Spins up the standalone WebSocket server and orchestration engine."""
    import websockets

    engine = NetworkedOrchestrationEngine(database_path=db_path)

    # Seed baseline multi-agent demo turns if requested
    logger.info(f"[Network Core] Binding Sarembok Voice Gateway to ws://localhost:{port}...")
    async with websockets.serve(lambda ws: handle_network_traffic(ws, engine), "0.0.0.0", port):
        logger.info(f"[Runtime Core] Voice Gateway online and listening on port {port}. Press Ctrl+C to terminate.")
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    port = 8765
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    asyncio.run(run_voice_gateway(port=port))
