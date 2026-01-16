from datetime import datetime

class Drawer:
    # Bỏ tham số profit_today trong init
    def __init__(self, user_id, cash=0, accumulated_profit=0):
        self.user_id = user_id
        self.cash = float(cash or 0)
        self.accumulated_profit = float(accumulated_profit or 0)
        self.last_updated = datetime.now().isoformat()

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "cash": self.cash,
            "accumulated_profit": self.accumulated_profit,
            "last_updated": self.last_updated
        }