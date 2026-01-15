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
                profit_today=data.get('profit_today', 0),
                accumulated_profit=data.get('accumulated_profit', 0), # [NEW]
                last_profit_date=data.get('last_profit_date') # [NEW]
            )
        return Drawer(user_id=user_id, cash=0)

    # [REFACTOR] Hàm này xử lý logic Reset ngày mới + Cộng dồn tích lũy
    def record_profit(self, user_id, profit_amount, date_str):
        doc_ref = self.drawer.document(user_id)
        
        # Chúng ta cần Transaction để đảm bảo tính nhất quán khi check ngày
        @firestore.transactional
        def update_in_transaction(transaction, ref):
            snapshot = transaction.get(ref)
            if not snapshot.exists:
                # Nếu chưa có user, tạo mới
                new_drawer = Drawer(
                    user_id=user_id, 
                    cash=profit_amount, # Lãi thường bơm vào cash luôn (tùy logic bạn)
                    profit_today=profit_amount, 
                    accumulated_profit=profit_amount,
                    last_profit_date=date_str
                )
                transaction.set(ref, new_drawer.to_dict())
            else:
                data = snapshot.to_dict()
                current_profit_date = data.get('last_profit_date')
                
                updates = {
                    "accumulated_profit": firestore.Increment(profit_amount), # Luôn cộng
                    "last_profit_date": date_str,
                    "last_updated": firestore.SERVER_TIMESTAMP
                }

                # LOGIC RESET NGÀY
                if current_profit_date == date_str:
                    # Cùng ngày -> Cộng tiếp
                    updates["profit_today"] = firestore.Increment(profit_amount)
                else:
                    # Khác ngày -> Reset về chính số tiền lãi mới phát sinh
                    updates["profit_today"] = profit_amount 

                transaction.update(ref, updates)

        update_in_transaction(self.db.transaction(), doc_ref)
    
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

    



