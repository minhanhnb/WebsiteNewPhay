from flask import Blueprint, render_template
from repository.cd_repo import CDRepository

#hệ thống 1
from repository.transaction_repo import TransactionRepository
from repository.finsight_repo import FinsightRepository
from repository.bank_repo import BankRepository
from services.transaction_service import TransactionService
from services.system_service import SystemService
from controller.transaction_controller import TransactionController

#hệ thống 2
# from services.T2.transaction_service import TransactionService2
# from services.T2.system_service import SystemService2 
# from controller.T2.transaction_controller import TransactionController2
# from repository.T2.transaction_repo import TransactionRepository2
# from repository.T2.finsight_repo import FinsightRepository2
# from repository.T2.bank_repo import BankRepository2


ttt_bp = Blueprint("ttt", __name__)

# 1. Init Repositories 
cd_repo = CDRepository()

trans_repo = TransactionRepository()
finsight_repo = FinsightRepository()
bank_repo = BankRepository()

# trans2_repo = TransactionRepository2()
# finsight2_repo = FinsightRepository2()
# bank2_repo = BankRepository2()


# 2. Init SystemService (Logic cốt lõi: Tiền, Hàng, Giá)
system_service = SystemService(finsight_repo, trans_repo, cd_repo, bank_repo)
# system2_service = SystemService2(finsight2_repo, trans2_repo, cd_repo, bank2_repo)

# 3. Init TransactionService (Logic Dashboard: Gọi sang SystemService)
service = TransactionService(trans_repo, system_service) 
# service2 = TransactionService2(trans2_repo, system2_service) 

# 4. Init Controller
controller = TransactionController(service)
# controller2 = TransactionController2(service2)


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