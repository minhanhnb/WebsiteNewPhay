from datetime import datetime

class Drawer:
    def __init__(self, user_id, cash=0, profit_today=0, accumulated_profit=0, last_profit_date=None):
        self.user_id = user_id
        self.cash = float(cash or 0)
        self.profit_today = float(profit_today or 0)
        self.accumulated_profit = float(accumulated_profit or 0) # [NEW] Lãi tích lũy
        # [NEW] Lưu ngày cập nhật lãi gần nhất (YYYY-MM-DD) để check reset
        self.last_profit_date = last_profit_date or datetime.now().strftime("%Y-%m-%d") 
        self.last_updated = datetime.now().isoformat()

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "cash": self.cash,
            "profit_today": self.profit_today,
            "accumulated_profit": self.accumulated_profit,
            "last_profit_date": self.last_profit_date,
            "last_updated": self.last_updated
        }