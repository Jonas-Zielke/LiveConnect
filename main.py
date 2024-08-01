from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
import uvicorn
from dotenv import load_dotenv
import os
from generate import generate_room_id, generate_room_token, check_room_token
from database import Database
from contextlib import asynccontextmanager
from Router import wss, audio


load_dotenv()

SERVER_IP = os.getenv("SERVER_IP", "127.0.0.1")
SERVER_PORT = int(os.getenv("SERVER_PORT", 8000))
SSL_KEYFILE = os.getenv("SSL_KEYFILE", "key.pem")
SSL_CERTFILE = os.getenv("SSL_CERTFILE", "cert.pem")

db = Database()

@asynccontextmanager
async def lifespan(app: FastAPI):
    db.connect()
    yield
    db.close()

app = FastAPI(lifespan=lifespan, debug=True)


@app.get("/")
async def read_root():
    return {"message": "Hello, World!"}

@app.get("/generate-room-id/")
async def api_generate_room_id(max_member: int, name: str, type: int):
    try:
        room_id = generate_room_id(max_member, name, type)
        return {"room_id": room_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/generate-room-token/")
async def api_generate_room_token(room_id: int, user_id: str, uuid: str):
    try:
        token = generate_room_token(room_id, user_id, uuid)
        return {"token": token}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/check-room-token/")
async def api_check_room_token(token: str, room_id: int):
    try:
        is_valid = check_room_token(token, room_id)
        return {"valid": is_valid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


app.include_router(wss.router)
app.include_router(audio.router)
if __name__ == "__main__":
    uvicorn.run(app, host=SERVER_IP, port=SERVER_PORT, ssl_keyfile=SSL_KEYFILE, ssl_certfile=SSL_CERTFILE)


