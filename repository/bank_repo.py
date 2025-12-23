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
        
    def sync_assets_net_changes(self, asset_changes_map):
        """
        [FIXED & FINAL] Cập nhật hàng loạt tài sản dựa trên map thay đổi số lượng.
        Input: {'CD_CODE_A': 100, 'CD_CODE_B': -20} -> Kết quả: +80
        """
        # 1. TÌM DOCUMENT NGÂN HÀNG (SỬA LỖI STREAM)
        docs_stream = self.collection.limit(1).stream()
        
        target_doc_snapshot = None
        
        # Duyệt qua stream để lấy document đầu tiên
        for doc in docs_stream:
            target_doc_snapshot = doc
            break 
            
        if not target_doc_snapshot:
            print("ERROR: Không tìm thấy System Bank Document nào.")
            return

        # Lấy dữ liệu hiện tại để tính toán
        data = target_doc_snapshot.to_dict()
        current_assets = data.get('taiSanUser', [])
        
        # [QUAN TRỌNG] Lấy reference để update sau này
        doc_ref = target_doc_snapshot.reference 

        # 2. Chuyển List hiện tại sang Dict: {'MA_CD': SoLuong}
        portfolio_map = {}
        for item in current_assets:
            # Xử lý linh hoạt item là dict hay object
            if isinstance(item, dict):
                code = item.get('maCD')
                qty = int(item.get('soLuong', 0))
            else:
                code = getattr(item, 'maCD', '')
                qty = int(getattr(item, 'soLuong', 0))
            
            if code:
                portfolio_map[code] = qty

        # 3. Áp dụng thay đổi (Cộng/Trừ Delta)
        for ma_cd, delta in asset_changes_map.items():
            current_qty = portfolio_map.get(ma_cd, 0)
            new_qty = current_qty + delta
            portfolio_map[ma_cd] = new_qty

        # 4. Tái tạo List để lưu (Chỉ giữ lại tài sản có số lượng > 0)
        final_assets_list = []
        for ma_cd, qty in portfolio_map.items():
            if qty > 0:
                final_assets_list.append({
                    "maCD": ma_cd,
                    "soLuong": qty
                })
            # Nếu qty <= 0 (bán hết), tự động không thêm vào list -> coi như Xóa.

        # 5. Cập nhật vào Database
        doc_ref.update({
            "taiSanUser": final_assets_list
        })
    