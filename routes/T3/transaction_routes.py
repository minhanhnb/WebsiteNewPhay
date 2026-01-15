

from flask import Blueprint, render_template
from repository.cd_repo import CDRepository

from services.T3.transaction_service import TransactionService3
from services.T3.system_service import SystemService3 
from controller.T3.transaction_controller import TransactionController3
from repository.T3.transaction_repo import TransactionRepository3
from repository.T3.finsight_repo import FinsightRepository3
from repository.T3.bank_repo import BankRepository3
from repository.T3.drawer_repo import DrawerRepository


ttt3_bp = Blueprint("ttt3", __name__)

# 1. Init Repositories 
cd_repo = CDRepository()

trans3_repo = TransactionRepository3()
finsight3_repo = FinsightRepository3()
bank3_repo = BankRepository3()
drawer_repo = DrawerRepository()


# 3. Init SystemService (Logic cốt lõi: Tiền, Hàng, Giá)
system3_service = SystemService3(drawer_repo,finsight3_repo, trans3_repo, cd_repo, bank3_repo)

# 3. Init TransactionService (Logic Dashboard: Gọi sang SystemService)

service3 = TransactionService3(trans3_repo, system3_service) 

# 4. Init Controller
controller3 = TransactionController3(service3)


# --- ROUTES ---


@ttt3_bp.route("/ttt3/api/transact", methods=["POST"])
def api_transact():
    print("Đang chạy được hệ thống 3")
    return controller3.submit_transaction()

@ttt3_bp.route("/ttt3/api/transact/<trans_id>", methods=["DELETE"])
def api_delete_trans(trans_id):
    return controller3.delete_transaction(trans_id)