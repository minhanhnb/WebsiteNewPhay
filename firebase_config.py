import os, json, firebase_admin
from firebase_admin import credentials, firestore

firebase_json = os.getenv("FIREBASE_JSON")

if firebase_json:  
    # Chạy production → Render
    cred_dict = json.loads(firebase_json)
    cred = credentials.Certificate(cred_dict)
else:
    # Chạy local → đọc từ file thật
    cred = credentials.Certificate("secret_key/firebase_key.json")

try:
    firebase_admin.initialize_app(cred)
except ValueError:
    pass

db = firestore.client()
