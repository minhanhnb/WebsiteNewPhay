from datetime import datetime
from repository.T3.transaction_repo import TransactionRepository3
from services.T3.system_service import SystemService3

class TransactionService3:
    def __init__(self, trans_repo: TransactionRepository3, system_service: SystemService3):
        self.trans_repo = trans_repo
        self.system_service = system_service # Dùng service này để thao tác tiền Finsight

    def add_transaction(self, payload):
        user_id = payload.get("user_id", "user_default")
        action = payload.get("action_type") 
        amount = float(payload.get("amount", 0))
        date_trans = payload.get("date_trans")
        
        if amount <= 0:
            return {"status": "error", "message": "Số tiền phải lớn hơn 0"}

        try:
            # GỌI SYSTEM SERVICE ĐỂ XỬ LÝ LOGIC TIỀN
            if action == "NAP":
                # Nạp vào Tủ
                return self.system_service.process_deposit(user_id, amount, date_trans)
            
            elif action == "RUT":
                # Rút tiền từ tủ
                return self.system_service.process_withdrawal(user_id, amount, date_trans)
            
            else:
                return {"status": "error", "message": "Hành động không hợp lệ"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def delete_transaction(self, trans_id):
        """
        Xóa giao dịch và Hoàn tiền (Revert) vào ví Finsight
        """
        # 1. Lấy thông tin giao dịch cũ
        trans = self.trans_repo.get_transaction_by_id(trans_id)
        if not trans:
            return {"status": "error", "message": "Giao dịch không tồn tại!"}

        user_id = trans.get("user_id")
        action = trans.get("action_type")
        amount = float(trans.get("amount", 0))

        # 3. Logic Hoàn tiền (Chỉ revert Cash, không revert thao tác bán CD vì phức tạp)
        revert_amount = 0
        if action == "NAP":
            revert_amount = -amount # Xóa Nạp = Trừ tiền ra
        elif action == "RUT":
            revert_amount = amount  # Xóa Rút = Cộng tiền lại

        try:
            # Update trực tiếp vào Finsight Repo (Truy cập qua system_service)
            self.system_service.finsight_repo.update_user_cash(user_id, revert_amount)
            
            # Xóa log Transaction
            self.trans_repo.delete_transaction(trans_id)
            
            return {"status": "success", "message": "Đã xóa giao dịch và cập nhật lại số dư Finsight."}
        except Exception as e:
            return {"status": "error", "message": f"Lỗi xử lý: {str(e)}"}