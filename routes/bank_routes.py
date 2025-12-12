
from flask import Blueprint, jsonify, request
from services.bank_service import insert_Cash_Momo, insert_Cash_User, get_all_info
bank_bp = Blueprint("bank", __name__)
@bank_bp.route("/bank/sync-netoff", methods=["POST"])
def sync_netoff():
    name = "User A"
    result = insert_Cash_Momo(name)
    return jsonify(result)

@bank_bp.route("/bank/update-user-cash", methods=["POST"])
def insertUserCash():
    data = request.get_json() or {}
    cash = data.get("cash")  # ✅ Lấy cash từ request body

    if cash is None:
        return jsonify({"error": "Missing 'cash'"}), 400

    result = insert_Cash_User(cash)
    return jsonify({"status": result})

@bank_bp.route("/bank", methods=["GET"])
def get_cash():
    result = get_all_info()
    return result

