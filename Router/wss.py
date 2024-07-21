from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from generate import check_room_token

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[int, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room_id: int):
        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = []
        self.active_connections[room_id].append(websocket)

    def disconnect(self, websocket: WebSocket, room_id: int):
        if room_id in self.active_connections:
            self.active_connections[room_id].remove(websocket)
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]

    async def broadcast(self, room_id: int, message: dict):
        connections = self.active_connections.get(room_id, [])
        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                # Handle the exception if the connection is already closed or any other error
                print(f"Error sending message: {e}")
                self.disconnect(connection, room_id)

manager = ConnectionManager()

@router.websocket("/wss/connect/room/{room_id}/")
async def websocket_endpoint(websocket: WebSocket, room_id: int, token: str):
    # Check if the token is valid for the given room_id
    if not check_room_token(token, room_id):
        await websocket.close(code=1008)  # Close with policy violation
        return

    await manager.connect(websocket, room_id)
    try:
        while True:
            data = await websocket.receive_json()
            user_id = data.get("user_id")
            message = data.get("message")
            if user_id and message:
                broadcast_message = {"user_id": user_id, "message": message}
                await manager.broadcast(room_id, broadcast_message)
    except WebSocketDisconnect:
        manager.disconnect(websocket, room_id)
    except Exception as e:
        print(f"Error: {e}")
        manager.disconnect(websocket, room_id)

# Speichere diese Datei als Router/wss.py
