from flask import Flask, jsonify, request
import os, json
import firebase_admin
from firebase_admin import credentials
from config import Config
from firebase_config import db  # Import db from firebase_config

app = Flask(__name__)

# # Import and register blueprints
from routes.home import home_bp
app.register_blueprint(home_bp)

from routes.cd_routes import cd_bp
app.register_blueprint(cd_bp)

from routes.transaction_routes import ttt_bp
app.register_blueprint(ttt_bp)

from routes.system_routes import system_bp

app.register_blueprint(system_bp)
# Khởi tạo Firebase 1 lần khi app khởi động
firebase_json = os.environ.get('FIREBASE_JSON')
if firebase_json:
    cred_dict = json.loads(firebase_json)
    cred = credentials.Certificate(cred_dict)
    try:
        firebase_admin.initialize_app(cred)
    except ValueError:
        # đã init trước đó thì bỏ qua
        pass
@app.route("/test")
def test_firebase():
    doc_ref = db.collection("test_collection").document("demo_doc")
    doc_ref.set({"message": "Hello from Flask + Firebase!"})
    doc = doc_ref.get()
    return f"Firebase says: {doc.to_dict().get('message')}"

if __name__ == "__main__":
    app.run(debug=True)
