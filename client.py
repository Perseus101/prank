import asyncio
import websockets
import json

NAME = "colin-desktop"


async def main():
    uri = "ws://localhost:8000/ws"
    async with websockets.connect(uri) as websocket:
        await websocket.send(json.dumps({"type": "id", "id": NAME}))
        while True:
            response = await websocket.recv()
            print(f"Received from server: {response}")


if __name__ == "__main__":
    asyncio.run(main())
