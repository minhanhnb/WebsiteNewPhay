from flask import Blueprint, render_template
from repository.cd_repo import CDRepository

from services.T2.transaction_service import TransactionService2
from services.T2.system_service import SystemService2 
from controller.T2.transaction_controller import TransactionController2
from repository.T2.transaction_repo import TransactionRepository2
from repository.T2.finsight_repo import FinsightRepository2
from repository.T2.bank_repo import BankRepository2
from repository.T2.drawer_repo import DrawerRepository


ttt2_bp = Blueprint("ttt2", __name__)

# 1. Init Repositories 
cd_repo = CDRepository()

trans2_repo = TransactionRepository2()
finsight2_repo = FinsightRepository2()
bank2_repo = BankRepository2()
drawer_repo = DrawerRepository()


# 2. Init SystemService (Logic cốt lõi: Tiền, Hàng, Giá)
system2_service = SystemService2(drawer_repo,finsight2_repo, trans2_repo, cd_repo, bank2_repo)

# 3. Init TransactionService (Logic Dashboard: Gọi sang SystemService)

service2 = TransactionService2(trans2_repo, system2_service) 

# 4. Init Controller
controller2 = TransactionController2(service2)


# --- ROUTES ---


@ttt2_bp.route("/ttt2/api/transact", methods=["POST"])
def api_transact():
    print("Đang chạy được hệ thống 2")
    return controller2.submit_transaction()

@ttt2_bp.route("/ttt2/api/transact/<trans_id>", methods=["DELETE"])
def api_delete_trans(trans_id):
    return controller2.delete_transaction(trans_id)