from datetime import datetime

class User:
    def __init__(self, user_id, balance=0, total_interest_earned=0, last_updated=None, net_off=0):
        self.user_id = user_id
        self.balance = float(balance)
        self.total_interest_earned = float(total_interest_earned)
        
        # --- QUAN TRỌNG: Gán giá trị net_off được truyền vào ---
        self.net_off = float(net_off) 
        
        if last_updated:
            self.last_updated = last_updated
        else:
            self.last_updated = datetime.now().isoformat()

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "balance": self.balance,
            "total_interest_earned": self.total_interest_earned,
            "last_updated": self.last_updated,
            
            # --- QUAN TRỌNG: Phải có key này để lưu xuống DB ---
            "netOff": self.net_off 
        }