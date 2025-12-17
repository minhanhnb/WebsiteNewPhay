from firebase_admin import firestore
from models.T2.transaction import Transaction2

class TransactionRepository2:
    def __init__(self):
        self.db = firestore.client()
        self.collection = self.db.collection("transactions")

    def add_transaction(self, trans: Transaction2):
        try:
            # Auto-generate ID
            doc_ref = self.collection.document()
            doc_ref.set(trans.to_dict())
            return True
        except Exception as e:
            print(f"Repo Error: {e}")
            return False

    def get_transactions_by_user(self, user_id):
            # Lấy tất cả giao dịch của user, sắp xếp theo ngày giảm dần
        docs = self.collection.where("user_id", "==", user_id)\
                                  .order_by("date_trans", direction=firestore.Query.DESCENDING)\
                                  .stream()
            
        results = []
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id  # <--- QUAN TRỌNG: Gắn ID để frontend biết mà xóa
            results.append(data)
        return results
        
    def get_transaction_by_id(self, trans_id):
        try:
            doc = self.collection.document(trans_id).get()
            if doc.exists:
                # Trả về data kèm ID để tiện xử lý
                data = doc.to_dict()
                data['id'] = doc.id 
                return data
            return None
        except Exception as e:
            print(f"Repo Error: {e}")
            return None

    def delete_transaction(self, trans_id):
        try:
            self.collection.document(trans_id).delete()
            return True
        except Exception as e:
            print(f"Repo Delete Error: {e}")
            return False
        

    def get_net_amount_by_date(self, date_str):
        """
        Tính tổng tiền ròng trong ngày: Tổng Nạp - Tổng Rút
        """
        # Query lấy tất cả giao dịch trong ngày đó
        docs = self.collection.where('date_trans', '==', date_str).stream()
        
        net_amount = 0.0
        count = 0
        
        for doc in docs:
            data = doc.to_dict()
            amount = float(data.get('amount', 0))
            action = data.get('action_type', 'NAP') # Mặc định là NAP nếu thiếu field
            
            if action == 'NAP':
                net_amount += amount
            elif action == 'RUT':
                net_amount -= amount
            count += 1
            
        return net_amount, count