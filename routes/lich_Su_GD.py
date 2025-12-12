# routes/lich_su_giao_dich_routes.py
from flask import Blueprint, jsonify
from services.lich_Su_GD_service import get_lich_su_giao_dich

lich_su_bp = Blueprint("lich_su_gd", __name__)

@lich_su_bp.route("/lich-su-giao-dich", methods=["GET"])
def lich_su_giao_dich():
    data = get_lich_su_giao_dich()
    return jsonify(data)
