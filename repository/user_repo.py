from firebase_admin import firestore
from models.user import User
from datetime import datetime
from repository.base_repo import BaseRepository

class UserRepository(BaseRepository):
    def __init__(self):
        super().__init__('users')

    def get_by_id(self, user_id):
        doc = self.collection.document(user_id).get()
        if doc.exists:
            data = doc.to_dict()
            return User(
                user_id=data.get('user_id'),
                balance=data.get('balance', 0),
                total_interest_earned=data.get('total_interest_earned', 0),
                last_updated=data.get('last_updated'),
                # Lấy netOff từ DB lên
                net_off=data.get('netOff', 0) 
            )
        return None
    
    def get_user_wallet(self, user_id):
        user = self.get_by_id(user_id)
        if user:
            return user.to_dict()
        return {"balance": 0}

    def update_balance(self, user_id, amount_delta):
        """
        Cập nhật: Cộng cả Balance và NetOff
        """
        doc_ref = self.collection.document(user_id)
        try:
            # CASE 1: User đã tồn tại -> Update (Cộng dồn)
            # Thử update, nếu doc không tồn tại sẽ nhảy xuống except
            doc_ref.update({
                "balance": firestore.Increment(amount_delta),
                "netOff": firestore.Increment(amount_delta), 
                "last_updated": firestore.SERVER_TIMESTAMP
            })
            return True
        except Exception as e:
            # CASE 2: User chưa tồn tại (Lần đầu tiên nạp tiền) -> Tạo mới (SET)
            print(f"User mới, đang khởi tạo... {e}")
            
            new_user = User(
                user_id=user_id, 
                balance=amount_delta,
                
                # --- QUAN TRỌNG: Lần đầu nạp bao nhiêu thì NetOff bấy nhiêu ---
                net_off=amount_delta 
            )
            
            doc_ref.set(new_user.to_dict())
            return True

    def reset_net_off(self, user_id):
        """
        Reset netOff về 0 sau khi 'Đi tiền'
        """
        try:
            self.collection.document(user_id).update({
                "netOff": 0,
                "last_updated": firestore.SERVER_TIMESTAMP
            })
            return True
        except Exception as e:
            print(f"Error resetting netOff: {e}")
            return False