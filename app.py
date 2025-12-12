from flask import Flask
from config import Config
from firebase_config import db  # Import db from firebase_config

app = Flask(__name__)
app.config.from_object(Config)

# # Import and register blueprints
from routes.home import home_bp
app.register_blueprint(home_bp)

from routes.cd_routes import cd_bp
app.register_blueprint(cd_bp)

from routes.transaction_routes import ttt_bp
app.register_blueprint(ttt_bp)

from routes.system_routes import system_bp

app.register_blueprint(system_bp)
@app.route("/test")
def test_firebase():
    doc_ref = db.collection("test_collection").document("demo_doc")
    doc_ref.set({"message": "Hello from Flask + Firebase!"})
    doc = doc_ref.get()
    return f"Firebase says: {doc.to_dict().get('message')}"

if __name__ == "__main__":
    app.run(debug=True)
