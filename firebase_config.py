import firebase_admin
from firebase_admin import credentials, firestore
from config import Config

# Only initialize if not already initialized
if not firebase_admin._apps:
    cred = credentials.Certificate(Config.FIREBASE_CREDENTIALS)
    firebase_admin.initialize_app(cred)

# Firestore client
db = firestore.client()
