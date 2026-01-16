from ..base_repo import BaseRepository
from models.T3.Finsight import FinsightUser3, FinsightSystem3
from firebase_admin import firestore

class FinsightRepository3(BaseRepository):
    def __init__(self):
        # BaseRepo init collection gốc (không quan trọng lắm vì ta dùng sub-collections)
        super().__init__('finsight_data')
        self.db = firestore.client()
        self.user_col = self.db.collection('finsight3_users')     # Chứa User
        self.system_doc = self.db.collection('finsight3_system').document('general') # Chứa FS Account
        self.log_col = self.db.collection('settlement3_queue')    # Chứa Log chờ Sync

    # --- 1. QUẢN LÝ USER ACCOUNT ---
    def get_user_account(self, user_id):
        doc = self.user_col.document(user_id).get()
        if doc.exists:
            data = doc.to_dict()
            return FinsightUser3(
                user_id=data.get('user_id'),
                cash=data.get('cash', 0),
                assets=data.get('assets', [])
            )
        # Nếu chưa có -> Trả về User mới (Cash=0)
        return FinsightUser3(user_id=user_id, cash=0, assets=[])

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
            new_user = FinsightUser3(user_id, cash=amount_delta)
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
            return FinsightSystem3(
                cash=data.get('tienMatFinSight', 0),
                assets_value=data.get('taiSanFinsight', 0)
            )
        return FinsightSystem3()

    def update_system_cash(self, amount_delta):
        """Cập nhật tiền mặt của chính Finsight (Doanh thu/Chi phí)"""
        try:
            self.system_doc.update({
                "tienMatFinSight": firestore.Increment(amount_delta),
                "last_updated": firestore.SERVER_TIMESTAMP
            })
        except:
            self.system_doc.set(FinsightSystem3(cash=amount_delta).to_dict())

    # --- 3. LOGGING (CHỜ SYNC NHLK) ---
    def add_settlement_log(self, user_id, action_type, amount, date, details=None):
        self.log_col.add({
            "user_id": user_id,
            "type": action_type,
            "amount": amount,
            "details": details or {},
            "status": "PENDING",
            "created_at": date
        })

    def get_pending_logs(self):
    # Luôn trả về dữ liệu thô (Snapshots) để tầng Service có quyền truy cập .id và .to_dict()
        return self.log_col.where('status', '==', 'PENDING').get()
    

    def mark_logs_processed(self, log_ids):
        batch = self.db.batch()
        for log_id in log_ids:
            ref = self.log_col.document(log_id)
            batch.update(ref, {"status": "PROCESSED"})
        batch.commit()