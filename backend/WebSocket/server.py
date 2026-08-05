import asyncio
import json
import websockets


async def client(websocket):

    print("Sarembok Client Connected")

    try:

        async for message in websocket:

            print("Received:")
            print(message)

            response = {
                "type": "ai_response",
                "text": "Sarembok Runtime Online",
                "state": "active"
            }

            await websocket.send(
                json.dumps(response)
            )

    except websockets.exceptions.ConnectionClosed:
        print("Client disconnected")



async def main():

    print("")
    print("==============================")
    print(" Sarembok WebSocket Runtime")
    print(" Port: 9000")
    print("==============================")
    print("")


    async with websockets.serve(
        client,
        "0.0.0.0",
        9000
    ):

        await asyncio.Future()



asyncio.run(main())
