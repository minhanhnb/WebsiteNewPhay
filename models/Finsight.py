from datetime import datetime

# 1. Cấu trúc tài khoản USER tại Finsight
class FinsightUser:
    def __init__(self, user_id, cash=0, assets=None):
        self.user_id = user_id
        # [FIX] Dùng (cash or 0) để tránh lỗi float(None)
        self.cash = float(cash or 0)  
        self.assets = assets if isinstance(assets, list) else []
        self.last_updated = datetime.now().isoformat()

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "cash": self.cash,
            "assets": self.assets,
            "last_updated": self.last_updated
        }

# 2. Cấu trúc tài khoản HỆ THỐNG
class FinsightSystem:
    def __init__(self, cash=0, assets_value=0):
        # [FIX] Dùng (val or 0)
        self.cash = float(cash or 0)
        self.assets_value = float(assets_value or 0)
        self.last_updated = datetime.now().isoformat()

    def to_dict(self):
        return {
            "tienMatFinSight": self.cash,
            "taiSanFinsight": self.assets_value,
            "last_updated": self.last_updated
        }