from .base_repo import BaseRepository
from models.Bank import Bank
from firebase_admin import firestore # Cần import cái này để dùng Increment
class BankRepository(BaseRepository):
    def __init__(self):
        super().__init__('bank')

    def get_system_bank(self):
        data = self._get_first()
        if data:
            return Bank(**data) # Unpack dict to object
        return Bank() # Return empty default object
    
    def update_user_cash(self, amount):
        """Hàm cũ: Cập nhật tiền mặt khi Nạp/Rút"""
        self._update_bank_field("tienMatUser", amount)

    def update_system_cash(self, amount):
        """
        Cập nhật tiền mặt của Finsight tại Ngân hàng Lưu ký (NHLK).
        Dùng cho nghiệp vụ: Nhận tiền bán CD từ User hoặc Trả tiền mua lại CD.
        """
       
        self._update_bank_field("tienMatFinsight", amount)


    def sync_transaction_nhlk(self, total_cost, cd_ids_list):
        """
        Đồng bộ giao dịch mua bán sang NHLK:
        - Tiền: Chuyển từ User -> Finsight
        - Tài sản: Chuyển từ Finsight -> User
        """
        docs = self.collection.limit(1).stream()
        doc_ref = None
        for doc in docs:
            doc_ref = doc.reference
            break
        
        if doc_ref:
            doc_ref.update({
                # 1. CHUYỂN TIỀN
                "tienMatUser": firestore.Increment(-total_cost),     # Tiền User giảm
                "tienMatFinsight": firestore.Increment(total_cost),  # Tiền Finsight tăng
                
                # 2. CHUYỂN TÀI SẢN
                # User nhận danh sách mã CD
                "taiSanUser": firestore.ArrayUnion(cd_ids_list),
                
             
            })

    def sync_assets_ownership(self, assets_to_add, assets_to_remove):
            """
            [FIXED] Cập nhật sở hữu tài sản User (taiSanUser) tại NHLK.
            Thực hiện tuần tự: Thêm trước -> Xóa sau (hoặc ngược lại) để tránh ghi đè key.
            """
            docs = self.collection.limit(1).stream()
            
            for doc in docs:
                # BƯỚC 1: Xử lý thêm tài sản (Mua)
                if assets_to_add:
                    doc.reference.update({
                        "taiSanUser": firestore.ArrayUnion(assets_to_add)
                    })
                
                # BƯỚC 2: Xử lý xóa tài sản (Bán/Rút)
                if assets_to_remove:
                    doc.reference.update({
                        "taiSanUser": firestore.ArrayRemove(assets_to_remove)
                    })
                
                # Chỉ cần update cho document đầu tiên tìm thấy (Singleton)
                return
    def _update_bank_field(self, field, value):
        """Helper update atomic"""
        docs = self.collection.limit(1).stream()
        doc_ref = None
        for doc in docs:
            doc_ref = doc.reference
            break
        
        if doc_ref:
            doc_ref.update({ field: firestore.Increment(value) })
        else:
            # Init nếu chưa có
            self.collection.add({ field: value })

    def sync_sell_transaction_nhlk(self, total_revenue, cd_ids_list):
        """
        [MỚI] Đồng bộ khi User BÁN (Rút tiền):
        - Tiền chảy ngược từ Finsight -> User
        - Tài sản User giảm, Tài sản Finsight tăng
        """
        docs = self.collection.limit(1).stream()
        for doc in docs:
            doc.reference.update({
                "tienMatUser": firestore.Increment(total_revenue),
                "tienMatFinsight": firestore.Increment(-total_revenue),
                "taiSanUser": firestore.ArrayRemove(cd_ids_list),
                "taiSanFinsight": firestore.Increment(total_revenue)
            })
            return

    def _update_field(self, field, value):
        docs = self.collection.limit(1).stream()
        for doc in docs:
            doc.reference.update({field: firestore.Increment(value)})
            return
        

    