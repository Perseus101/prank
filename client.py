import asyncio
import websockets
import traceback
import json
import os
import glob
import requests

NAME = "colin-desktop"
SERVER_URL = "localhost:8000"


async def load_files(file_list):
    os.makedirs("client_files", exist_ok=True)
    files = []
    files.extend(glob.glob("client_files/*.wav"))
    files.extend(glob.glob("client_files/*.mp3"))
    files = [f.replace("client_files/", "") for f in files]
    for server_file in file_list:
        if server_file in files:
            continue
        # Download file from server
        response = requests.get(f"http://{SERVER_URL}/file/{server_file}")
        if response.status_code != 200:
            print(f"Failed to download file: {server_file}")
            continue
        with open(f"client_files/{server_file}", "wb") as f:
            print(f"Downloaded file: {server_file}")
            f.write(response.content)
        files.append(server_file)

    return files


async def play_sound(filename):
    process = await asyncio.create_subprocess_exec(
        "aplay",
        filename,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        print(f"Failed to play sound: {filename}")
        print(f"stdout: {stdout}")
        print(f"stderr: {stderr}")


class RestartNow(Exception):
    pass


async def client_main():
    uri = f"ws://{SERVER_URL}/ws"
    async with websockets.connect(uri) as websocket:
        await websocket.send(json.dumps({"type": "id", "id": NAME}))
        response = await websocket.recv()
        response_json = json.loads(response)
        assert response_json["type"] == "file_list"
        files = await load_files(response_json["files"])

        while True:
            response = await websocket.recv()
            response_json = json.loads(response)

            if response_json["type"] == "restart":
                raise RestartNow()
            elif response_json["type"] == "file_list":
                files = await load_files(response_json["files"])
                print(f"Received updated file list: {files}")
            elif response_json["type"] == "play_sound":
                print(f"Playing sound: {response_json['filename']}")

                assert (
                    response_json["filename"] in files
                ), f"File not found: {response_json['filename']}"

                filename = os.path.join("client_files", response_json["filename"])

                await play_sound(filename)
            else:
                print(f"Received from server: {response}")


async def main():
    while True:
        try:
            await client_main()
        except RestartNow:
            print("Restarting")
            continue
        except KeyboardInterrupt:
            break
        except websockets.ConnectionClosedError:
            print("Connection closed")
        except Exception as e:
            traceback.print_exc()

        await asyncio.sleep(10)


if __name__ == "__main__":
    asyncio.run(main())
