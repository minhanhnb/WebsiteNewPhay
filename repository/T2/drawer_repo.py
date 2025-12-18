from ..base_repo import BaseRepository
from models.T2.Drawer import Drawer
from firebase_admin import firestore

class DrawerRepository(BaseRepository):
    def __init__(self):
        # BaseRepo init collection gốc (không quan trọng lắm vì ta dùng sub-collections)
        super().__init__('drawer_data')
        self.db = firestore.client()
        self.drawer = self.db.collection('drawer')
        self.log_col = self.db.collection('settlement2_queue')    # Chứa Log chờ Sync

    # --- 1. QUẢN LÝ USER ACCOUNT ---
    def get_user_account(self, user_id):
        doc = self.drawer.document(user_id).get()
        if doc.exists:
            data = doc.to_dict()
            return Drawer(
                user_id=data.get('user_id'),
                cash=data.get('cash', 0),
                profit_today= data.get('profit_today',0)
            )
        # Nếu chưa có -> Trả về User mới (Cash=0)
        return Drawer(user_id=user_id, cash=0, profit_today=0)
    
    def update_user_cash(self, user_id, amount_delta):
        """Cập nhật Cash Remainder của User"""
        doc_ref = self.drawer.document(user_id)
        try:
            doc_ref.update({
                "cash": firestore.Increment(amount_delta),
                "last_updated": firestore.SERVER_TIMESTAMP
            })
        except Exception:
            # Tạo mới nếu chưa tồn tại
            new_user = Drawer(user_id, cash=amount_delta)
            doc_ref.set(new_user.to_dict())

    def update_profit_today(self, user_id, amount_delta):
            """Cập nhật Cash Remainder của User"""
            doc_ref = self.drawer.document(user_id)
            try:
                doc_ref.update({
                    "profit_today": firestore.Increment(amount_delta),
                    "last_updated": firestore.SERVER_TIMESTAMP
                })
            except Exception:
                # Tạo mới nếu chưa tồn tại
                new_user = Drawer(user_id, cash =0,profit_today=amount_delta)
                doc_ref.set(new_user.to_dict())

    



