from firebase_admin import firestore
from models.CD import CD

class CDRepository:
    def __init__(self):
        self.db = firestore.client()
        self.collection = self.db.collection("cds")
    def add_cd(self, cd: CD):
        try:
            print("== BẮT ĐẦU REPO ==")
            print("Payload vào model:", cd.to_dict())

            # 1. Lấy mã đối chiếu
            maDoiChieu = cd.thongTinChung.get("maDoiChieu")
            print("Step 1 - maDoiChieu:", maDoiChieu)

            if not maDoiChieu:
                print("Step 1 ERROR - maDoiChieu rỗng")
                raise ValueError("maDoiChieu is required")

            # 2. Tạo document reference
            doc_ref = self.collection.document(maDoiChieu)
            print("Step 2 - Document reference created")

            # 3. Check exists
            exists = doc_ref.get().exists
            print("Step 3 - Exists:", exists)

            if exists:
                print("Step 3 STOP - CD đã tồn tại")
                return {
                    "id": maDoiChieu,
                    "status": "exists",
                    "message": "CD đã tồn tại, không thể tạo mới."
                }

            # 4. Lưu Firestore
            print("Step 4 - Thực hiện doc_ref.set")
            doc_ref.set(cd.to_dict())
            print("Step 4 FINISH - Đã set thành công")

            return {
                "id": maDoiChieu,
                "status": "created",
                "message": "Tạo CD thành công."
            }

        except Exception as e:
            print("ERROR TRONG REPO:", str(e))
            return {"status": "error", "message": str(e)}

    def get_all_cd(self):
        print("Repo: get_all_cd")
        cds = []
        docs = self.collection.stream()

        for doc in docs:
            cds.append(doc.to_dict())

        return cds
   

    def decrease_stock(self, cd_id, quantity):
        """Trừ kho khi User mua"""
        doc_ref = self.collection.document(cd_id)
        doc_ref.update({
            "thongTinChung.CDKhaDung": firestore.Increment(-quantity)
        })

    def increase_stock(self, ma_doi_chieu, quantity):
        """
        [MỚI] Cộng kho khi User bán lại (Nhập kho)
        """
        doc_ref = self.collection.document(ma_doi_chieu)
        doc_ref.update({
            "thongTinChung.CDKhaDung": firestore.Increment(quantity)
        })

    def get_cd_by_id(self, maDoiChieu):
        try:
            doc = self.collection.document(maDoiChieu).get()
            if doc.exists:
                return doc.to_dict()
            return None
        except Exception as e:
            print("Repo error:", e)
            return None
        

    def update_cd_price(self, maDoiChieu, giaBanMoi, ngayCapNhat):
        """
        Cập nhật riêng trường giá bán
        """
        try:
            doc_ref = self.collection.document(maDoiChieu)
            # Dùng set với merge=True để chỉ update trường cần thiết
            # Cấu trúc lưu: thongTinGia -> giaBanHomNay
            doc_ref.set({
                "thongTinGia": {
                    "giaBanHomNay": giaBanMoi,
                }
            }, merge=True)
            return True
        except Exception as e:
            print(f"Repo Error Update Price {maDoiChieu}: {e}")
            return False
        

    def get_sellable_cds(self):
        """
        Lấy danh sách CD có thể bán (Số lượng khả dụng > 0 và Có giá bán hôm nay)
        """
        # Lưu ý: Firestore query filter nested fields
        # Giả định structure: thongTinChung.CDKhaDung > 0
        # Tuy nhiên để chắc chắn, ta fetch all rồi filter python cho an toàn logic phức tạp
        docs = self.collection.stream()
        results = []
        for doc in docs:
            data = doc.to_dict()
            c1 = data.get("thongTinChung", {})
            c4 = data.get("thongTinGia", {}) or {} # Handle case None
            
            # Logic Filter: 
            # 1. Phải có mã đối chiếu
            # 2. Số lượng khả dụng > 0 (Nếu null thì dùng soLuong gốc)
            # 3. Phải có giá bán hôm nay
            sl_kha_dung = c1.get("CDKhaDung")
            if sl_kha_dung is None: 
                sl_kha_dung = float(c1.get("soLuong", 0))
            
            gia_ban = float(c4.get("giaBanHomNay", 0))

            if sl_kha_dung > 0 and gia_ban > 0:
                # Attach ID và real stock để dễ xử lý
                data['system_id'] = doc.id
                data['real_stock'] = sl_kha_dung
                data['current_price'] = gia_ban
                results.append(data)
        
        return results

    def decrease_stock(self, cd_id, quantity):
        """Trừ kho CD (Atomic)"""
        doc_ref = self.collection.document(cd_id)
        # Lưu ý: Cấu trúc data của bạn là thongTinChung.CDKhaDung
        doc_ref.update({
            "thongTinChung.CDKhaDung": firestore.Increment(-quantity)
        })