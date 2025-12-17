from datetime import datetime

class Transaction2:
    def __init__(self, user_id, action_type, amount, date_trans, note=""):
        self.user_id = user_id         # ID người dùng (Tạm thời hardcode nếu chưa có Login)
        self.action_type = action_type # "NAP" hoặc "RUT"
        self.amount = float(amount)
        self.date_trans = date_trans   # String YYYY-MM-DD
        self.note = note
        self.created_at = datetime.now().isoformat()

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "action_type": self.action_type,
            "amount": self.amount,
            "date_trans": self.date_trans,
            "note": self.note,
            "created_at": self.created_at
        }