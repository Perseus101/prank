from sanic import Sanic, Request, Websocket
from sanic.response import text, redirect, file
from sanic_ext import render
import json
import glob
import os
import uuid

app = Sanic("App")


@app.before_server_start
async def setup(app, loop):
    app.ctx.clients = {}

    files = []

    files.extend(glob.glob("server_files/*.wav"))
    files.extend(glob.glob("server_files/*.mp3"))
    files = [f.replace("server_files/", "") for f in files]
    app.ctx.files = files


@app.get("/")
async def index(request: Request):
    error_msg = request.args.get("error_msg", None)
    return await render(
        "index.html",
        context={
            "clients": app.ctx.clients.keys(),
            "error_msg": error_msg,
            "files": app.ctx.files,
        },
        status=200,
    )


@app.get("/soundboard/<client_name:str>")
async def soundboard(request: Request, client_name: str):
    if client_name not in app.ctx.clients:
        return redirect("/?error_msg=Client+not+found")
    error_msg = request.args.get("error_msg", None)
    return await render(
        "soundboard.html",
        context={
            "client_name": client_name,
            "files": app.ctx.files,
            "error_msg": error_msg,
        },
        status=200,
    )


@app.post("/soundboard/<client_name:str>")
async def play_sound(request: Request, client_name: str):
    if client_name not in app.ctx.clients:
        return redirect("/?error_msg=Client+not+found")
    file = request.form.get("file")
    if file not in app.ctx.files:
        return redirect(f"/soundboard/{client_name}?error_msg=File+not+found")
    ws = app.ctx.clients[client_name]
    await ws.send(json.dumps({"type": "play_sound", "filename": file}))
    return redirect(f"/soundboard/{client_name}")


@app.post("/soundboard/<client_name:str>/restart")
async def restart_client(request: Request, client_name: str):
    ws = app.ctx.clients.get(client_name)
    if ws is None:
        return redirect("/?error_msg=Client+not+found")
    await ws.send(json.dumps({"type": "restart"}))
    return redirect("/")


@app.get("/file/<filename:str>")
async def get_file(request: Request, filename: str):
    full_path = f"server_files/{filename}"
    if not os.path.exists(full_path):
        return text("File not found", status=404)
    return await file(full_path, filename=filename)


@app.get("/client/client.py")
async def get_client(request: Request):
    client_name = request.args.get("client_name", None)
    if client_name is None:
        # Generate random uuid
        client_name = str(uuid.uuid4())
    server_url = request.host

    return await render(
        "client.py.template",
        context={"client_name": client_name, "server_url": server_url},
        headers={
            "Content-Type": "text/plain",
            "Content-Disposition": "attachment; filename=client.py",
        },
        status=200,
    )


@app.post("/send/<client_id:str>")
async def send_message(request: Request, client_id: str):
    print("Sending message to client", client_id)
    ws = app.ctx.clients.get(client_id)
    if ws is None:
        return redirect("/?error_msg=Client+not+found")
    await ws.send(json.dumps({"type": "server", "message": request.body.decode()}))
    return redirect("/")


@app.websocket("/ws")
async def websocket_handler(request: Request, ws: Websocket):
    id_msg = await ws.recv()
    json_msg = json.loads(id_msg)
    assert json_msg["type"] == "id"
    app.ctx.clients[json_msg["id"]] = ws
    print(f"Client with id {json_msg['id']} connected")
    await ws.send(json.dumps({"type": "file_list", "files": app.ctx.files}))

    await ws.auto_closer_task
    print(f"Client with id {json_msg['id']} disconnected")
    del app.ctx.clients[json_msg["id"]]
