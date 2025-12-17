from ..base_repo import BaseRepository
from models.T2.Finsight import FinsightUser2, FinsightSystem2
from firebase_admin import firestore

class FinsightRepository2(BaseRepository):
    def __init__(self):
        # BaseRepo init collection gốc (không quan trọng lắm vì ta dùng sub-collections)
        super().__init__('finsight_data')
        self.db = firestore.client()
        self.user_col = self.db.collection('finsight2_users')     # Chứa User
        self.system_doc = self.db.collection('finsight2_system').document('general') # Chứa FS Account
        self.log_col = self.db.collection('settlement2_queue')    # Chứa Log chờ Sync

    # --- 1. QUẢN LÝ USER ACCOUNT ---
    def get_user_account(self, user_id):
        doc = self.user_col.document(user_id).get()
        if doc.exists:
            data = doc.to_dict()
            return FinsightUser2(
                user_id=data.get('user_id'),
                cash=data.get('cash', 0),
                assets=data.get('assets', [])
            )
        # Nếu chưa có -> Trả về User mới (Cash=0)
        return FinsightUser2(user_id=user_id, cash=0, assets=[])

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
            new_user = FinsightUser2(user_id, cash=amount_delta)
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
            return FinsightSystem2(
                cash=data.get('tienMatFinSight', 0),
                assets_value=data.get('taiSanFinsight', 0)
            )
        return FinsightSystem2()

    def update_system_cash(self, amount_delta):
        """Cập nhật tiền mặt của chính Finsight (Doanh thu/Chi phí)"""
        try:
            self.system_doc.update({
                "tienMatFinSight": firestore.Increment(amount_delta),
                "last_updated": firestore.SERVER_TIMESTAMP
            })
        except:
            self.system_doc.set(FinsightSystem2(cash=amount_delta).to_dict())

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
        """
        Lấy danh sách logs trạng thái PENDING.
        Hàm được viết lại để an toàn với cả DocumentSnapshot (Firestore chuẩn) và Dict (Mocking).
        """
        try:
            # 1. Lấy stream dữ liệu từ Firestore
            docs = self.log_col.where("status", "==", "PENDING").stream()
            
            results = []
            for doc in docs:
                data = {}
                doc_id = "unknown_id"

                # Cách 1: Kiểm tra nếu là DocumentSnapshot chuẩn (có method to_dict)
                if hasattr(doc, 'to_dict'):
                    data = doc.to_dict()
                    doc_id = doc.id
                
                # Cách 2: Kiểm tra nếu là Dictionary (thường gặp khi dùng Mock hoặc một số wrapper)
                elif isinstance(doc, dict):
                    data = doc
                    # Cố gắng tìm ID trong dict
                    doc_id = data.get('id') or data.get('_id') or 'unknown_id'
                
                # Bỏ qua nếu không phải cả 2 loại trên
                else:
                    continue

                # Gán ID vào data để Frontend sử dụng
                data['id'] = doc_id
                results.append(data)
                
            return results

        except Exception as e:
            print(f"Error getting pending logs: {str(e)}")
            return []