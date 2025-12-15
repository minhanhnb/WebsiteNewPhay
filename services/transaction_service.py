from datetime import datetime
from repository.transaction_repo import TransactionRepository
from services.system_service import SystemService

class TransactionService:
    def __init__(self, trans_repo: TransactionRepository, system_service: SystemService):
        self.trans_repo = trans_repo
        self.system_service = system_service # Dùng service này để thao tác tiền Finsight

    def get_user_dashboard(self, user_id="user_default", target_date_str=None):
        # 1. Xử lý ngày xem
        if not target_date_str:
            target_date_str = datetime.now().strftime("%Y-%m-%d")

        # 2. TÍNH TỔNG BALANCE (NET WORTH) TỪ FINSIGHT
        # Hàm này đã cộng: Cash (trong DB) + Giá trị Asset (Tính theo giá ngày target_date)
        total_balance = self.system_service.calculate_user_net_worth(user_id, target_date_str)

        # 3. Lấy lịch sử giao dịch
        all_transactions = self.trans_repo.get_transactions_by_user(user_id)
        
        # Filter: Chỉ lấy giao dịch <= ngày đang xem
       
        
        # Sort: Mới nhất lên đầu
        # Sửa "date_trans" thành "date"
        # Thêm logic .get("date", "") để nếu lỡ dữ liệu cũ không có date cũng không bị crash (trả về chuỗi rỗng)
        history_display = [
            t for t in all_transactions 
            if t.get("date", t.get("date_trans", "")) <= target_date_str
        ]

        return {
            "balance": total_balance, # UI hiển thị số này là Tổng Tài Sản
            "interest_rate": 4.0,     # Có thể lấy từ config
            "history": history_display,
            "view_date": target_date_str,
            # Các trường phụ nếu UI cần (để trống hoặc tính toán nếu muốn)
            "interest_today": 0,
            "interest_month": 0
        }

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
                # Nạp thẳng vào Finsight Cash
                return self.system_service.process_deposit(user_id, amount, date_trans)
            
            elif action == "RUT":
                # Rút tiền (Smart Withdrawal: Cash -> Bán CD)
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

        # 2. Logic Hoàn tiền (Chỉ revert Cash, không revert thao tác bán CD vì phức tạp)
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