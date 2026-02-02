from flask import Blueprint, render_template
# 1. Import Dependencies
from repository.user_repo import UserRepository
from repository.T2.bank_repo import BankRepository2
from repository.T2.finsight_repo import FinsightRepository2
from repository.T2.transaction_repo import TransactionRepository2
from repository.cd_repo import CDRepository
from repository.T2.drawer_repo import DrawerRepository
from services.T2.system_service import SystemService2
from controller.T2.system_controller import SystemController2

system2_bp = Blueprint("system2_bp", __name__)

transaction_repo = TransactionRepository2()
user_repo = UserRepository()
bank_repo = BankRepository2()
finsight_repo = FinsightRepository2()
drawer_repo = DrawerRepository()
cd_repo = CDRepository() # <--- Init Mới
service = SystemService2(drawer_repo, finsight_repo, transaction_repo, cd_repo, bank_repo)
controller = SystemController2(service)


# --- ROUTES DEFINITIONS ---

@system2_bp.route("/system2")
def system_dashboard():
    """
    Route này chịu trách nhiệm trả về View (HTML).
    Controller không cần can thiệp vào việc này.
    """
    return render_template("T2/dashboard2.html")

@system2_bp.route("/system2/api/overview", methods=["GET"])
def api_system_overview():
    """
    Route này gọi Controller để xử lý logic API và trả về JSON.
    """
    return controller.get_overview()



@system2_bp.route("/system2/api/settle", methods=["POST"])
def api_settle_cash():
    return controller.settle_cash()


@system2_bp.route("/system2/api/allocate", methods=["POST"])
def api_allocate_cd():
    return controller.allocate_cd()

@system2_bp.route("/system2/api/syncDiff", methods=["POST"])
def api_syncDiff():
    return controller.sync_Diff()

# --- ROUTES DEFINITIONS ---

@system2_bp.route("/system2/api/sync-all", methods=["POST"])
def api_sync_all():
    """
    Hợp nhất syncDiff và syncBank vào một luồng duy nhất.
    """
    return controller.sync_diff_and_bank() 
@system2_bp.route("/system2/api/withdraw", methods=["POST"])
def api_withdraw():
    return controller.withdraw_money()


@system2_bp.route("/system2/api/sync-bank", methods=["POST"])
def api_sync_bank():
    """Gọi Controller để xử lý việc đẩy log giao dịch sang Bank"""
    return controller.sync_bank()


@system2_bp.route("/system2/api/reset", methods=["POST"])
def api_reset_database():
    return controller.reset_database()


