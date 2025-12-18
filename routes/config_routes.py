from flask import Blueprint, request, jsonify
from services.config_service import ConfigService
from repository.config_repo import ConfigRepository

config_bp = Blueprint('config_bp', __name__)
config_service = ConfigService(ConfigRepository())

@config_bp.route('/api/config/interest-rate', methods=['POST'])
def config_interest_rate():
    try:
        data = request.json
        config_id = config_service.create_interest_config(data)
        return jsonify({"message": "Cập nhật thành công", "id": config_id}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400