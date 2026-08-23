import asyncio
import os
import websockets

async def main():
    token = os.environ["SAREMBOK_AUTH_TOKEN"]

    print("=" * 60)
    print(" SAREMBOK PUBLIC WSS TEST")
    print("=" * 60)

    try:
        async with websockets.connect(
            "wss://sarembok.com/",
            additional_headers={
                "Authorization": f"Bearer {token}"
            },
            origin="https://sarembok.com",
        ) as ws:
            print("CONNECTED: wss://sarembok.com/")
            print("WebSocket state:", ws.state)
            print("PUBLIC WSS TEST PASSED")

    except Exception as e:
        print("PUBLIC WSS TEST FAILED")
        print(type(e).__name__, str(e))

asyncio.run(main())
