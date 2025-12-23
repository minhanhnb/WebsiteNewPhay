from flask import Blueprint, render_template, request
from repository.cd_repo import CDRepository
from controller.cd_controller import CDController
from services.cd_service import CDService

cd_bp = Blueprint("cd", __name__)
repo = CDRepository()
service = CDService(repo)
controller = CDController(service)

@cd_bp.route("/cd/add", methods=["POST"])
def add_cd_route():
    return controller.add_cd()

@cd_bp.route("/cd")
def cd_manage():
    return render_template("cd_manage.html", active_page="cd_manage")

@cd_bp.route("/cd/all", methods=["GET"])
def get_all():
    return controller.get_all_cd()

@cd_bp.route("/cd/<maDoiChieu>", methods=["GET"])
def get_by_id(maDoiChieu):
    return controller.get_cd_detail(maDoiChieu)

@cd_bp.route("/cd/manage/<maDoiChieu>", methods=["GET"])
def render_detail_page(maDoiChieu):
    return render_template("cd_detail.html", maDoiChieu=maDoiChieu)

@cd_bp.route("/cd/delete/<maDoiChieu>", methods=["DELETE"])
def delete_asset(maDoiChieu):
    return controller.handle_delete_asset(maDoiChieu)