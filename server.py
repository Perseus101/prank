from sanic import Sanic, Request, Websocket
from sanic.response import text, redirect
from sanic_ext import render
import json
import asyncio

app = Sanic("App")


@app.before_server_start
async def setup(app, loop):
    app.ctx.memory = {}


@app.get("/")
async def index(request):
    error_msg = request.args.get("error_msg", None)
    return await render(
        "index.html",
        context={"clients": app.ctx.memory.keys(), "error_msg": error_msg},
        status=200,
    )


@app.post("/send/<client_id:str>")
async def send_message(request: Request, client_id):
    print("Sending message to client", client_id)
    ws = app.ctx.memory.get(client_id)
    if ws is None:
        return redirect("/?error_msg=Client+not+found")
    await ws.send(json.dumps({"type": "server", "message": request.body.decode()}))
    return redirect("/")


@app.websocket("/ws")
async def websocket_handler(request: Request, ws: Websocket):
    id_msg = await ws.recv()
    json_msg = json.loads(id_msg)
    assert json_msg["type"] == "id"
    app.ctx.memory[json_msg["id"]] = ws
    print(f"Client with id {json_msg['id']} connected")
    while True:
        await asyncio.sleep(10)
        await ws.ping()
    print("Closed")
