from flask import Blueprint, render_template
from repository.transaction_repo import TransactionRepository
from repository.finsight_repo import FinsightRepository
from repository.cd_repo import CDRepository
from repository.bank_repo import BankRepository

from services.transaction_service import TransactionService
from services.system_service import SystemService
from controller.transaction_controller import TransactionController

ttt_bp = Blueprint("ttt", __name__)

# 1. Init Repositories (Không còn UserRepository)
trans_repo = TransactionRepository()
finsight_repo = FinsightRepository()
cd_repo = CDRepository()
bank_repo = BankRepository()

# 2. Init SystemService (Logic cốt lõi: Tiền, Hàng, Giá)
system_service = SystemService(finsight_repo, trans_repo, cd_repo, bank_repo)

# 3. Init TransactionService (Logic Dashboard: Gọi sang SystemService)
service = TransactionService(trans_repo, system_service) 

# 4. Init Controller
controller = TransactionController(service)

# --- ROUTES ---
@ttt_bp.route("/ttt")
def ttt_dashboard():
    return render_template("ttt_dashboard.html")

@ttt_bp.route("/ttt/api/dashboard", methods=["GET"])
def api_dashboard():
    return controller.get_dashboard_data()

@ttt_bp.route("/ttt/api/transact", methods=["POST"])
def api_transact():
    return controller.submit_transaction()

@ttt_bp.route("/ttt/api/transact/<trans_id>", methods=["DELETE"])
def api_delete_trans(trans_id):
    return controller.delete_transaction(trans_id)