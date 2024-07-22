import os
import base64
import hmac
import hashlib
import time
import logging
import asyncio
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCConfiguration, RTCIceServer
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

STUN_SERVER = os.getenv("STUN_SERVER")
TURN_SERVER = os.getenv("TURN_SERVER")
TURN_SECRET = os.getenv("TURN_SECRET")
REALM = os.getenv("REALM")
TURN_SERVER_USER = os.getenv("TURN_SERVER_USER")
TURN_SERVER_PW = os.getenv("TURN_SERVER_PW")

logging.basicConfig(level=logging.DEBUG)

router = APIRouter()

class Offer(BaseModel):
    sdp: str
    type: str

class WebRTCPeerConnectionManager:
    def __init__(self):
        self.pcs = {}
        self.connections = {}

    async def create_peer_connection(self, client_id: str):
        ice_servers = [RTCIceServer(urls=[STUN_SERVER])]
        if TURN_SERVER:
            if TURN_SECRET:
                username, password = generate_turn_credentials(TURN_SECRET, REALM)
            elif TURN_SERVER_USER and TURN_SERVER_PW:
                username = TURN_SERVER_USER
                password = TURN_SERVER_PW
            else:
                raise HTTPException(status_code=500, detail="TURN credentials are not set.")
            logging.debug(f"TURN Server: {TURN_SERVER}, Username: {username}, Credential: {password}")
            ice_servers.append(RTCIceServer(
                urls=[TURN_SERVER],
                username=username,
                credential=password
            ))

        configuration = RTCConfiguration(iceServers=ice_servers)
        pc = RTCPeerConnection(configuration)
        self.pcs[client_id] = pc
        self.connections[client_id] = []
        return pc

    async def close_peer_connection(self, pc, client_id):
        await pc.close()
        del self.pcs[client_id]
        del self.connections[client_id]

    async def close_all(self):
        for pc in self.pcs.values():
            await pc.close()
        self.pcs.clear()
        self.connections.clear()

    def get_clients(self):
        return list(self.pcs.keys())

    def add_connection(self, client_id, connected_id):
        if client_id in self.connections:
            self.connections[client_id].append(connected_id)
        else:
            self.connections[client_id] = [connected_id]

    def get_connections(self, client_id):
        return self.connections.get(client_id, [])

pc_manager = WebRTCPeerConnectionManager()

def generate_turn_credentials(secret, realm):
    username = str(int(time.time()) + 3600)  # Gültigkeit für 1 Stunde
    username_bytes = username.encode('utf-8')
    secret_bytes = secret.encode('utf-8')
    hmac_sha1 = hmac.new(secret_bytes, username_bytes, hashlib.sha1)
    password = base64.b64encode(hmac_sha1.digest()).decode('utf-8')
    return username, password

@router.post("/webrtc/offer/{client_id}", response_class=HTMLResponse)
async def create_offer(client_id: str, offer: Offer):
    try:
        pc = await pc_manager.create_peer_connection(client_id)

        @pc.on("iceconnectionstatechange")
        async def on_iceconnectionstatechange():
            logging.debug(f"ICE Connection State: {pc.iceConnectionState}")
            if pc.iceConnectionState == "failed":
                await pc_manager.close_peer_connection(pc, client_id)

        @pc.on("track")
        def on_track(track):
            logging.debug(f"Track {track.kind} received")
            for other_client_id, other_pc in pc_manager.pcs.items():
                if other_client_id != client_id:
                    other_pc.addTrack(track)
                    pc_manager.add_connection(client_id, other_client_id)
                    pc_manager.add_connection(other_client_id, client_id)

        offer = RTCSessionDescription(sdp=offer.sdp, type=offer.type)
        await pc.setRemoteDescription(offer)
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)

        return HTMLResponse(
            content=pc.localDescription.sdp,
            media_type="application/sdp"
        )
    except Exception as e:
        logging.error(f"Error in create_offer: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/audio/room", response_class=HTMLResponse)
async def get_audio_room():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Audio Room</title>
    </head>
    <body>
        <h1>Join Audio Room</h1>
        <input type="text" id="room_id" placeholder="Room ID">
        <input type="text" id="token" placeholder="Token">
        <input type="text" id="client_id" placeholder="Client ID">
        <button onclick="joinRoom()">Join Room</button>
        <div id="videos"></div>
        <script>
            let pc;

            async function joinRoom() {
                const roomId = document.getElementById('room_id').value;
                const token = document.getElementById('token').value;
                const clientId = document.getElementById('client_id').value;
                if (!roomId || !token || !clientId) {
                    alert('Please enter Room ID, Token and Client ID');
                    return;
                }

                const response = await fetch('/webrtc/turn-credentials');
                const credentials = await response.json();

                pc = new RTCPeerConnection({
                    iceServers: [
                        { urls: 'stun:stun.kanonen-studio.de:3478' },
                        { 
                            urls: 'turn:turn.kanonen-studio.de:5349',
                            username: credentials.username,
                            credential: credentials.password
                        }
                    ]
                });

                pc.onicecandidate = event => {
                    if (event.candidate) {
                        console.log('New ICE candidate: ', event.candidate);
                    }
                };

                pc.ontrack = event => {
                    const video = document.createElement('video');
                    video.srcObject = event.streams[0];
                    video.autoplay = true;
                    document.getElementById('videos').appendChild(video);
                };

                const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
                stream.getTracks().forEach(track => pc.addTrack(track, stream));

                const offer = await pc.createOffer();
                await pc.setLocalDescription(offer);

                const responseOffer = await fetch(`/webrtc/offer/${clientId}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ sdp: pc.localDescription.sdp, type: pc.localDescription.type })
                });
                const answer = await responseOffer.text();

                await pc.setRemoteDescription(new RTCSessionDescription({ sdp: answer, type: 'answer' }));

                setInterval(async () => {
                    const response = await fetch(`/webrtc/connections/${clientId}`);
                    const connections = await response.json();
                    console.log('Connected Clients: ', connections);
                }, 5000);
            }
        </script>
    </body>
    </html>
    """
    return html_content

@router.get("/webrtc/turn-credentials")
async def get_turn_credentials():
    if TURN_SECRET:
        username, password = generate_turn_credentials(TURN_SECRET, REALM)
    elif TURN_SERVER_USER and TURN_SERVER_PW:
        username = TURN_SERVER_USER
        password = TURN_SERVER_PW
    else:
        raise HTTPException(status_code=500, detail="TURN credentials are not set.")
    return {"username": username, "password": password}

@router.get("/webrtc/clients")
async def get_clients():
    clients = pc_manager.get_clients()
    return {"clients": clients}

@router.get("/webrtc/connections/{client_id}")
async def get_connections(client_id: str):
    connections = pc_manager.get_connections(client_id)
    return {"connections": connections}
