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
        """Lấy danh sách CD khả dụng để bán"""
        docs = self.collection.stream()
        results = []
        for doc in docs:
            data = doc.to_dict()
            c1 = data.get("thongTinChung", {})
            c4 = data.get("thongTinGia", {}) or {} # Đề phòng c4 là None
            
            # [FIX] Xử lý an toàn cho Số lượng
            sl_kha_dung = c1.get("CDKhaDung")
            if sl_kha_dung is None: 
                # Nếu soLuong cũng None thì về 0
                sl_kha_dung = float(c1.get("soLuong") or 0)
            else:
                sl_kha_dung = float(sl_kha_dung)
            
            # Chỉ lấy hàng còn trong kho
            if sl_kha_dung > 0:
                data['system_id'] = doc.id
                data['real_stock'] = sl_kha_dung
                
                # [FIX] Xử lý an toàn cho Giá bán
                # Nếu giaBanHomNay là None -> float(None) sẽ lỗi -> dùng (val or 0)
                try:
                    price = float(c4.get("giaBanHomNay") or 0)
                except:
                    price = 0

                data['current_price'] = price
                results.append(data)
        
        return results

    def decrease_stock(self, cd_id, quantity):
        doc_ref = self.collection.document(cd_id)
        doc_ref.update({
            "thongTinChung.CDKhaDung": firestore.Increment(-quantity)
        })

    def increase_stock(self, ma_doi_chieu, quantity):
        doc_ref = self.collection.document(ma_doi_chieu)
        doc_ref.update({
            "thongTinChung.CDKhaDung": firestore.Increment(quantity)
        })

    def get_cd_by_id(self, ma_doi_chieu):
        doc = self.collection.document(ma_doi_chieu).get()
        return doc.to_dict() if doc.exists else None
    
    def delete_asset(self, asset_id):
        try:
            # Xóa document khỏi Firestore
            self.db.collection('cds').document(asset_id).delete()
            return True, "Xóa tài sản thành công."
        except Exception as e:
            raise Exception(f"Lỗi database: {e}")