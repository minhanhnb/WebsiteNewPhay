from flask import Blueprint, render_template
# 1. Import Dependencies
from repository.user_repo import UserRepository
from repository.bank_repo import BankRepository
from repository.finsight_repo import FinsightRepository
from repository.transaction_repo import TransactionRepository
from repository.cd_repo import CDRepository # <--- Import Mới

from repository.config_repo import ConfigRepository
from services.system_service import SystemService
from controller.system_controller import SystemController


from services.config_service import ConfigService

system_bp = Blueprint("system_bp", __name__)

config_repo = ConfigRepository()
transaction_repo = TransactionRepository()
user_repo = UserRepository()
bank_repo = BankRepository()
finsight_repo = FinsightRepository()
cd_repo = CDRepository() # <--- Init Mới

config_service = ConfigService(config_repo)


service = SystemService(finsight_repo, transaction_repo, cd_repo, bank_repo, config_service)
controller = SystemController(service)


# --- ROUTES DEFINITIONS ---

@system_bp.route("/system")
def system_dashboard():
    """
    Route này chịu trách nhiệm trả về View (HTML).
    Controller không cần can thiệp vào việc này.
    """
    return render_template("dashboard.html")

@system_bp.route("/system/api/overview", methods=["GET"])
def api_system_overview():
    """
    Route này gọi Controller để xử lý logic API và trả về JSON.
    """
    return controller.get_overview()



@system_bp.route("/system/api/settle", methods=["POST"])
def api_settle_cash():
    return controller.settle_cash()


@system_bp.route("/system/api/allocate", methods=["POST"])
def api_allocate_cd():
    return controller.allocate_cd()


@system_bp.route("/system/api/withdraw", methods=["POST"])
def api_withdraw():
    return controller.withdraw_money()


@system_bp.route("/system/api/sync-bank", methods=["POST"])
def api_sync_bank():
    """Gọi Controller để xử lý việc đẩy log giao dịch sang Bank"""
    return controller.sync_bank()


@system_bp.route("/system/api/reset", methods=["POST"])
def api_reset_database():
    return controller.reset_database()


