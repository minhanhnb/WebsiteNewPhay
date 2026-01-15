from datetime import datetime

# 1. Cấu trúc tài khoản USER tại Finsight
class Drawer3:
    def __init__(self, user_id, cash=0, profit_today= 0):
        self.user_id = user_id
        # [FIX] Dùng (cash or 0) để tránh lỗi float(None)
        self.cash = float(cash or 0)  
        self.profit_today = float(profit_today or 0)
        self.last_updated = datetime.now().isoformat()

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "cash": self.cash,
            "profit_today" : self.profit_today,
            "last_updated": self.last_updated
        }

