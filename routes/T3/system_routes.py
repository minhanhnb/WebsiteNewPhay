from flask import Blueprint, render_template
# 1. Import Dependencies
from repository.user_repo import UserRepository
from repository.T3.bank_repo import BankRepository3
from repository.T3.finsight_repo import FinsightRepository3
from repository.T3.transaction_repo import TransactionRepository3
from repository.cd_repo import CDRepository
from repository.T3.drawer_repo import DrawerRepository
from services.T3.system_service import SystemService3
from controller.T3.system_controller import SystemController3

system3_bp = Blueprint("system3_bp", __name__)

transaction_repo = TransactionRepository3()
user_repo = UserRepository()
bank_repo = BankRepository3()
finsight_repo = FinsightRepository3()
drawer_repo = DrawerRepository()
cd_repo = CDRepository() # <--- Init Mới
service = SystemService3(drawer_repo, finsight_repo, transaction_repo, cd_repo, bank_repo)
controller = SystemController3(service)


# --- ROUTES DEFINITIONS ---

@system3_bp.route("/system3")
def system_dashboard():
    """
    Route này chịu trách nhiệm trả về View (HTML).
    Controller không cần can thiệp vào việc này.
    """
    return render_template("T3/dashboard3.html")

@system3_bp.route("/system3/api/overview", methods=["GET"])
def api_system_overview():
    """
    Route này gọi Controller để xử lý logic API và trả về JSON.
    """
    return controller.get_overview()



@system3_bp.route("/system3/api/settle", methods=["POST"])
def api_settle_cash():
    return controller.settle_cash()


@system3_bp.route("/system3/api/allocate", methods=["POST"])
def api_allocate_cd():
    return controller.allocate_cd()

@system3_bp.route("/system3/api/syncDiff", methods=["POST"])
def api_syncDiff():
    return controller.sync_Diff()

@system3_bp.route("/system3/api/withdraw", methods=["POST"])
def api_withdraw():
    return controller.withdraw_money()


@system3_bp.route("/system3/api/sync-bank", methods=["POST"])
def api_sync_bank():
    """Gọi Controller để xử lý việc đẩy log giao dịch sang Bank"""
    return controller.sync_bank()


@system3_bp.route("/system3/api/reset", methods=["POST"])
def api_reset_database():
    return controller.reset_database()


