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

@cd_bp.route("/cd/sync-daily-price", methods=["POST"])
def sync_daily_price_route():
    return controller.sync_daily_price()
# @cd_manage_bp.route("/cd-manage/add-cd", methods=["POST"])
# def add_cd():
#     data = request.form  # Lấy dữ liệu từ form
#     # Nếu gửi JSON thì dùng: data = request.json
#     if not data:
#         return "No data provided", 400

#     result = add_CD_service(
#         data.get("maCD"),
#         data.get("ngayPhatHanh"),
#         data.get("uuTien"),
#         int(data.get("soLuong", 0)),
#         int(data.get("CDKhaDung", 0)),
#         float(data.get("laiSuat", 0)),
#         data.get("ngayDaoHan"),
#         float(data.get("giaSoCap", 0)),
#     )

#     return result

# @cd_manage_bp.route("/cd-manage/get-cds", methods=["GET"])
# def get_cds():
#     result = get_all_CD()
#     return result 


# @cd_manage_bp.route("/cd-manage/sync-today", methods=["POST"])
# def sync_today():
#     result = sync_today_service()
#     return result
