import secrets
from database import Database

db = Database()

def generate_room_token(room_id: int, user_id: str, uuid: str) -> str:
    token = f"lc_{secrets.token_urlsafe(64)}"
    query = "INSERT INTO room_tokens (token, room_id, user_id, uuid) VALUES (%s, %s, %s, %s)"
    db.execute_insert(query, (token, room_id, user_id, uuid))
    return token

def generate_room_id(max_member: int, name: str, type: int) -> int:
    room_id = int(secrets.randbits(60))  # Generiere eine 18-stellige Zahl
    query = "INSERT INTO rooms (room_id, max_member, name, type) VALUES (%s, %s, %s, %s)"
    db.execute_insert(query, (room_id, max_member, name, type))
    return room_id

def check_room_token(token: str, room_id: int) -> bool:
    query = "SELECT COUNT(*) as count FROM room_tokens WHERE token = %s AND room_id = %s"
    result = db.execute_query(query, (token, room_id))
    return result[0]['count'] > 0


