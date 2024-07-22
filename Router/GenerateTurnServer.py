import base64
import hmac
import hashlib
import time

def generate_turn_credentials(secret, realm):
    username = str(int(time.time()) + 3600)  # Gültigkeit für 1 Stunde
    username_bytes = username.encode('utf-8')
    secret_bytes = secret.encode('utf-8')
    hmac_sha1 = hmac.new(secret_bytes, username_bytes, hashlib.sha1)
    password = base64.b64encode(hmac_sha1.digest()).decode('utf-8')
    return username, password

# Beispiel
secret = "sqya85wttpiisH1gpmkQwHuzwLqbZVavdbpw0eZXoJ9TWpOQZc"
realm = "kanonen-studio.de"
username, password = generate_turn_credentials(secret, realm)
print(f"Username: {username}, Password: {password}")
