from flask import Blueprint, render_template
from repository.T2.transaction_repo import TransactionRepository2
from repository.T2.finsight_repo import FinsightRepository2
from repository.cd_repo import CDRepository
from repository.T2.bank_repo import BankRepository2

from services.T2.transaction_service import TransactionService
from services.T2.system_service import SystemService
from controller.T2.transaction_controller import TransactionController

ttt2_bp = Blueprint("ttt2", __name__)

# 1. Init Repositories (Không còn UserRepository)
trans_repo = TransactionRepository2()
finsight_repo = FinsightRepository2()
cd_repo = CDRepository()
bank_repo = BankRepository2()

# 2. Init SystemService (Logic cốt lõi: Tiền, Hàng, Giá)
system_service = SystemService(finsight_repo, trans_repo, cd_repo, bank_repo)

# 3. Init TransactionService (Logic Dashboard: Gọi sang SystemService)
service = TransactionService(trans_repo, system_service) 

# 4. Init Controller
controller = TransactionController(service)

# --- ROUTES ---

@ttt2_bp.route("/ttt/api/dashboard", methods=["GET"])
def api_dashboard():
    return controller.get_dashboard_data()

@ttt2_bp.route("/ttt2/api/transact", methods=["POST"])
def api_transact():
    return controller.submit_transaction()

@ttt2_bp.route("/ttt2/api/transact/<trans_id>", methods=["DELETE"])
def api_delete_trans(trans_id):
    return controller.delete_transaction(trans_id)