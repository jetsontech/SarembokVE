import asyncio
import base64
import json
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from google import genai
from google.genai import types

app = FastAPI(title="Sarembok_VE Frontier Live Core")

client = genai.Client(
    api_key=os.environ.get("GEMINI_API_KEY", ""),
    http_options={'api_version': 'v1alpha'}
)

@app.get("/")
async def serve_frontend():
    frontend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "index.html"))
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path, media_type="text/html")
    return {"error": "index.html not found."}

@app.websocket("/ws/live")
async def gemini_live_proxy(websocket: WebSocket):
    await websocket.accept()
    print("[SYSTEM] Client connected to live proxy.")
    
    try:
        async with client.aio.live.connect(
            model="gemini-3.1-flash-live-preview",
            config=types.LiveConnectConfig(
                response_modalities=[types.Modality.AUDIO],
                output_audio_transcription=types.AudioTranscriptionConfig(),
                system_instruction=types.Content(parts=[types.Part.from_text(
                    text="You are the AI core of Sarembok_VE, a frontier multimodal terminal application. "
                         "You operate through a real-time WebSocket bridge. Keep your answers sharp, "
                         "technical, and concise."
                )])
            )
        ) as session:
            print("[SYSTEM] Bridged to Gemini Live Frontier API via SDK.")

            async def client_to_gemini():
                try:
                    while True:
                        raw_msg = await websocket.receive_text()
                        data = json.loads(raw_msg)
                        
                        if data.get("type") == "vision":
                            base64_data = data["image"].split(",")[1]
                            image_bytes = base64.b64decode(base64_data)
                            
                            await session.send_realtime_input(
                                video=types.Blob(
                                    data=image_bytes,
                                    mime_type="image/jpeg"
                                )
                            )
                            print("[OUT] Sent vision frame chunk via realtime video input.")
                            
                        elif data.get("type") == "text":
                            text_content = data["text"]
                            await session.send_realtime_input(text=text_content)
                            print(f"[OUT] Sent text: {text_content}")
                except Exception as e:
                    print(f"[ERROR] Client relay fault: {e}")

            async def gemini_to_client():
                try:
                    async for response in session.receive():
                        server_content = response.server_content
                        if server_content:
                            if hasattr(server_content, "audio_transcription") and server_content.audio_transcription:
                                transcript_text = server_content.audio_transcription.text
                                if transcript_text:
                                    await websocket.send_text(json.dumps({"text": transcript_text}))
                                    print(f"[IN TRANSCRIPT] {transcript_text}")

                        if server_content and server_content.model_turn:
                            for part in server_content.model_turn.parts:
                                if part.text:
                                    await websocket.send_text(json.dumps({"text": part.text}))
                                    print(f"[IN TEXT] {part.text}")
                                elif part.inline_data:
                                    audio_b64 = base64.b64encode(part.inline_data.data).decode("utf-8")
                                    await websocket.send_text(json.dumps({"audio": audio_b64}))
                except Exception as e:
                    print(f"[ERROR] Gemini relay fault: {e}")

            await asyncio.gather(client_to_gemini(), gemini_to_client())

    except WebSocketDisconnect:
        print("[SYSTEM] Client disconnected from live bridge.")
    except Exception as e:
        print(f"[ERROR] Live bridge fault: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)