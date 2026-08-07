import asyncio
import json
import websockets

from agent import SarembokAgent
from memory import SarembokMemory

memory = SarembokMemory()
agent = SarembokAgent(memory)


async def handler(websocket):
    async for message in websocket:
        event = json.loads(message)
        commands = agent.process(event)

        for command in commands:
            await websocket.send(command.to_json())


async def main():
    print("Sarembok Runtime WebSocket listening on 8765")

    async with websockets.serve(
        handler,
        "0.0.0.0",
        8765
    ):
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
