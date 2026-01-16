from firebase_admin import firestore
from google.cloud.firestore import FieldFilter, Query

class TransactionRepository:
    def __init__(self):
        self.db = firestore.client()
        self.collection = self.db.collection('transactions')

    # --- 1. LẤY DANH SÁCH HIỂN THỊ (UI) ---
    def get_transactions_by_user(self, user_id):
        """
        Lấy lịch sử giao dịch để hiển thị Frontend.
        Sắp xếp: Mới nhất lên đầu (DESCENDING).
        """
        try:
            # [FIX] Dùng thống nhất field 'date'
            docs = self.collection.where(filter=FieldFilter("user_id", "==", user_id))\
                                  .order_by("date", direction=Query.DESCENDING)\
                                  .stream()
            
            results = []
            for doc in docs:
                # doc là DocumentSnapshot -> gọi .to_dict() là ĐÚNG
                data = doc.to_dict()
                data['id'] = doc.id  # Gắn ID để frontend xử lý xóa/sửa
                results.append(data)
            return results
            
        except Exception as e:
            print(f"Repo Error (get_transactions_by_user): {e}")
            return []

    # --- 2. LẤY CHI TIẾT 1 GIAO DỊCH ---
    def get_transaction_by_id(self, trans_id):
        try:
            doc = self.collection.document(trans_id).get()
            if doc.exists:
                data = doc.to_dict()
                data['id'] = doc.id 
                return data
            return None
        except Exception as e:
            print(f"Repo Error (get_transaction_by_id): {e}")
            return None

    # --- 3. LẤY DỮ LIỆU CHO REPLAY (Time Machine) ---
    def get_all_transactions(self, user_id, up_to_date_str):
        """
        Lấy toàn bộ giao dịch để tính toán lại số dư.
        Sắp xếp: Cũ nhất lên đầu (ASCENDING).
        """
        try:
            docs = self.collection.where(filter=FieldFilter('user_id', '==', user_id))\
                                  .where(filter=FieldFilter('date', '<=', up_to_date_str))\
                                  .order_by('date', direction=Query.ASCENDING)\
                                  .stream()
            
            results = []
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                results.append(data)
            return results
            
        except Exception as e:
            print(f"Repo Error (get_all_transactions): {e}")
            return []

    # --- 4. THÊM GIAO DỊCH MỚI ---
    def add_transaction(self, data):
        """
        Thêm transaction mới. Hỗ trợ cả Dict và Object Model.
        """
        try:
            # Nếu data là Object có hàm to_dict() (VD: Transaction Model)
            if hasattr(data, 'to_dict'):
                return self.collection.add(data.to_dict())
            
            # Nếu data đã là Dict (do hàm _log_transaction gửi sang)
            return self.collection.add(data)
            
        except Exception as e:
            print(f"Repo Error (add_transaction): {e}")
            return None

    def delete_transaction(self, trans_id):
        try:
            self.collection.document(trans_id).delete()
            return True
        except Exception as e:
            print(f"Repo Delete Error: {e}")
            return False