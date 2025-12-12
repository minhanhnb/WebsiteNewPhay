from flask import Blueprint, request
from services.Momo_User_Service import  get_all_Cash, insert_Cash_Momo_User

momo_user = Blueprint("momo_user", __name__)

@momo_user.route("/users", methods=["GET"])
def get_cash():
    result = get_all_Cash()
    return result

@momo_user.route("/users/add-cash", methods=["POST"])
def add_cash():
    name = "User A"
    cash = request.form.get("cash")

    if not cash:
        return "Cash are required!", 400

    try:
        cash = float(cash)
    except ValueError:
        return "Cash must be a number!", 400

    result = insert_Cash_Momo_User(name, cash)
    return result  # This goes straight to AJAX response

