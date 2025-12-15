import datetime
from .base_repo import BaseRepository
from models.Finsight import FinsightUser, FinsightSystem
from firebase_admin import firestore
from google.cloud.firestore import FieldFilter, Query
class FinsightRepository(BaseRepository):
    def __init__(self):
        # BaseRepo init collection gốc (không quan trọng lắm vì ta dùng sub-collections)
        super().__init__('finsight_data')
        self.db = firestore.client()
        self.user_col = self.db.collection('finsight_users')     # Chứa User
        self.system_doc = self.db.collection('finsight_system').document('general') # Chứa FS Account
        self.log_col = self.db.collection('settlement_queue')    # Chứa Log chờ Sync

    # --- 1. QUẢN LÝ USER ACCOUNT ---
    def get_user_account(self, user_id):
        doc = self.user_col.document(user_id).get()
        if doc.exists:
            data = doc.to_dict()
            return FinsightUser(
                user_id=data.get('user_id'),
                cash=data.get('cash', 0),
                assets=data.get('assets', [])
            )
        # Nếu chưa có -> Trả về User mới (Cash=0)
        return FinsightUser(user_id=user_id, cash=0, assets=[])

    def update_user_cash(self, user_id, amount_delta):
        """Cập nhật Cash Remainder của User"""
        doc_ref = self.user_col.document(user_id)
        try:
            doc_ref.update({
                "cash": firestore.Increment(amount_delta),
                "last_updated": firestore.SERVER_TIMESTAMP
            })
        except Exception:
            # Tạo mới nếu chưa tồn tại
            new_user = FinsightUser(user_id, cash=amount_delta)
            doc_ref.set(new_user.to_dict())

    def update_user_assets(self, user_id, new_assets_list):
        """Ghi đè danh mục tài sản User"""
        self.user_col.document(user_id).update({
            "assets": new_assets_list,
            "last_updated": firestore.SERVER_TIMESTAMP
        })

    # --- 2. QUẢN LÝ FS ACCOUNT (SYSTEM) ---
    def get_system_account(self):
        doc = self.system_doc.get()
        if doc.exists:
            data = doc.to_dict()
            return FinsightSystem(
                cash=data.get('tienMatFinSight', 0),
                assets_value=data.get('taiSanFinsight', 0)
            )
        return FinsightSystem()

    def update_system_cash(self, amount_delta):
        """Cập nhật tiền mặt của chính Finsight (Doanh thu/Chi phí)"""
        try:
            self.system_doc.update({
                "tienMatFinSight": firestore.Increment(amount_delta),
                "last_updated": firestore.SERVER_TIMESTAMP
            })
        except:
            self.system_doc.set(FinsightSystem(cash=amount_delta).to_dict())

    # --- 3. LOGGING (CHỜ SYNC NHLK) ---
    def add_settlement_log(self, user_id, action_type, amount, details=None):
        self.log_col.add({
            "user_id": user_id,
            "type": action_type,
            "amount": amount,
            "details": details or {},
            "status": "PENDING",
            "created_at": firestore.SERVER_TIMESTAMP
        })

    def get_pending_logs(self):
        return self.log_col.where("status", "==", "PENDING").stream()

    def mark_logs_processed(self, log_ids):
        batch = self.db.batch()
        for log_id in log_ids:
            ref = self.log_col.document(log_id)
            batch.update(ref, {"status": "PROCESSED"})
        batch.commit()

    def get_profit_history(self, user_id, start_date_str, end_date_str):
        try:
            docs = self.db.collection('finsight_users').document(user_id)\
                          .collection('profit_history')\
                          .where(filter=FieldFilter('date', '>=', start_date_str))\
                          .where(filter=FieldFilter('date', '<=', end_date_str))\
                          .stream()
            
            return [d.to_dict() for d in docs]
        except Exception as e:
            print(f"Error getting history: {e}")
            return []
        
    def save_daily_profit(self, user_id, date_str, amount):
        try:
            doc_ref = self.db.collection('finsight_users').document(user_id)\
                             .collection('profit_history').document(date_str)
            
            doc_ref.set({
                "date": date_str,
                "amount": amount,
                # [FIX]: Gọi datetime.datetime.now() thay vì datetime.now()
                "updated_at": datetime.datetime.now(), 
                "note": "Auto-saved via Dashboard View"
            })
            return True
        except Exception as e:
            print(f"Error saving daily profit repo: {e}")
            return False
        
    # 1. Lấy snapshot gần nhất để xác định điểm bắt đầu
    def get_latest_snapshot(self, user_id):
        try:
            # Sắp xếp giảm dần theo date, lấy 1 cái đầu tiên
            docs = self.db.collection('finsight_users').document(user_id)\
                          .collection('daily_snapshots')\
                          .order_by('date', direction=firestore.Query.DESCENDING)\
                          .limit(1).stream()
            
            for doc in docs:
                return doc.to_dict()
            return None
        except Exception as e:
            print(f"Error getting latest snapshot: {e}")
            return None

    # 2. Hàm lưu Batch (Lưu nhiều ngày cùng lúc cho nhanh)
    def save_batch_data(self, user_id, snapshots_data, profits_data):
        """
        snapshots_data: List các dict snapshot cần lưu
        profits_data: List các dict profit cần lưu
        """
        batch = self.db.batch()
        
        # Add Snapshots vào Batch
        for snap in snapshots_data:
            doc_ref = self.db.collection('finsight_users').document(user_id)\
                             .collection('daily_snapshots').document(snap['date'])
            batch.set(doc_ref, snap)
            
        # Add Profits vào Batch
        for prof in profits_data:
            doc_ref = self.db.collection('finsight_users').document(user_id)\
                             .collection('profit_history').document(prof['date'])
            batch.set(doc_ref, prof)
            
        # Commit 1 lần duy nhất
        batch.commit()


    def get_all_transactions(self, user_id, up_to_date_str):
        try:
            docs = self.db.collection('transactions')\
                        .where(filter=FieldFilter('user_id', '==', user_id))\
                        .where(filter=FieldFilter('date', '<=', up_to_date_str))\
                        .order_by('date', direction=Query.ASCENDING)\
                        .stream()
            return [d.to_dict() for d in docs]
        except Exception as e:
            print(f"Error getting transactions: {e}")
            return []