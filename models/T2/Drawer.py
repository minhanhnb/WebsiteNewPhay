from datetime import datetime

# 1. Cấu trúc tài khoản USER tại Finsight
class Drawer:
    def __init__(self, user_id, cash=0):
        self.user_id = user_id
        # [FIX] Dùng (cash or 0) để tránh lỗi float(None)
        self.cash = float(cash or 0)  
        self.last_updated = datetime.now().isoformat()

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "cash": self.cash,
            "last_updated": self.last_updated
        }

