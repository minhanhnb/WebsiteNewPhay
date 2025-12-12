import os
import json
import firebase_admin
from firebase_admin import credentials, firestore

# Lấy JSON từ Environment Variable
firebase_json = os.getenv("FIREBASE_JSON")

if firebase_json is None:
    raise Exception("FIREBASE_JSON environment variable is missing.")

# Chuyển từ string → dict
cred_dict = json.loads(firebase_json)

# Tạo credential từ dict (không dùng file)
cred = credentials.Certificate(cred_dict)

# Init firebase admin
try:
    firebase_admin.initialize_app(cred)
except ValueError:
    # Đã init rồi → bỏ qua
    pass

db = firestore.client()
