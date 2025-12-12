import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class Config:
    SECRET_KEY = "secret_key_demo"
    DEBUG = True
    FIREBASE_CREDENTIALS = os.path.join(BASE_DIR, "secret_key", "firebase_key.json")


USER_INTEREST_RATE = 4.0