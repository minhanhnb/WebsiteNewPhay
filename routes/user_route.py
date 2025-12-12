from flask import Blueprint, render_template, request


user_bp = Blueprint("user_bp", __name__)

@user_bp.route("/user-manage")
def user_manage():
    return render_template("user_manage.html", active_page="user_manage")