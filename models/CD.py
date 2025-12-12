from datetime import date
import datetime
from firebase_config import db  # Import directly from firebase_config
from firebase_admin import firestore
class CD:
    def __init__(
        self,
        thongTinChung: dict,
        thongTinLaiSuat: dict,
        thongTinNhapKho: dict,
        thongtinGia : dict =None,
    ):
        # --- Thông tin chung ---
        self.thongTinChung = {
            "maDoiChieu": thongTinChung.get("maDoiChieu"),
            "TCPH": thongTinChung.get("toChuc"),
            "ngayPhatHanh": thongTinChung.get("ngayPhatHanh"),
            "ngayDaoHan": thongTinChung.get("ngayDaoHan"),
            "menhGia": thongTinChung.get("menhGia"),
            "soLuong": thongTinChung.get("soLuong"),
            "CDKhaDung": thongTinChung.get("CDKhaDung"),
            "ngayTHQuyen": thongTinChung.get("ngayTHQuyen"),
            "loaiLaiSuat": thongTinChung.get("loaiLaiSuat"),
            "ghiChu": thongTinChung.get("ghiChu"),


        }

        # --- Thông tin lãi suất ---
        self.thongTinLaiSuat = {
            "laiSuat": thongTinLaiSuat.get("laiSuat"),
            "quyUocNgay": thongTinLaiSuat.get("quyUoc"),
            "tanSuatTraLai": thongTinLaiSuat.get("tanSuatTraLai"),

        }

        # --- Thông tin nhập kho ---
        self.thongTinNhapKho = {
            "dirtyPrice": thongTinNhapKho.get("dirtyPrice"),
            "ngayThucHien": thongTinNhapKho.get("ngayTH"),
            "ngayThucTe": thongTinNhapKho.get("ngayTT"),

            "cleanPrice": None,
            "soLuongNhapKho": thongTinNhapKho.get("soLuongCD"),
        }
        self.thongtinGia = {
            "giaBanHomNay": None,
        } or {}
    def to_dict(self):
        return {
            "thongTinChung": self.thongTinChung,
            "thongTinLaiSuat": self.thongTinLaiSuat,
            "thongTinNhapKho": self.thongTinNhapKho,
            "thongTinGia": self.thongtinGia,
        }

    
    @staticmethod
    def get_all_CD():
        CD_ref = db.collection("cds").stream()
        return [doc.to_dict() for doc in CD_ref]
    
    @staticmethod
    def add_cd(cd_obj):
        cd_ref = db.collection("cds").document(cd_obj.maCD)
        cd_ref.set(cd_obj.to_dict())
        return f"CD {cd_obj.maCD} added successfully."
    
    # @staticmethod
    # def update_CD(maCD, data: dict):
    #     """Update 1 CD trong Firestore theo lệnh SYNC TODAY."""
    #     db.collection("cds").document(maCD).update(data)

    # @staticmethod 
    # def buy_CD(maCD, soLuong):
    #     """Bán CD theo mã và số lượng."""
    #     current_SL = db.collection("cds").document(maCD).get().to_dict().get("soLuong", 0)
    #     new_SL = current_SL - soLuong
    #     db.collection("cds").document(maCD).update({
    #         "CDKhaDung": new_SL
    #     })
    #     print("Đã bán CD:", maCD, "Số lượng:", soLuong, "Còn lại:", new_SL)

    # @staticmethod 
    # def get_CD_info(maCD): 
    #     cd_doc = db.collection("cds").document(maCD).get()
    #     return cd_doc.to_dict() if cd_doc.exists else None
    
    # @staticmethod
    # def get_today_market_valueTKO(maCD):
    #     # Lấy ngày hôm nay dạng YY-MM-DD
    #     today_str =date.today().strftime("%Y-%m-%d")
    #     print("Today:", today_str)
    #     # Truy vấn Firestore
    #     docs = db.collection("cds")\
    #         .where("maCD", "==", maCD)\
    #         .where("ngayCapNhat", "==", today_str)\
    #         .limit(1)\
    #         .get()        

    #     if docs:
    #         doc = docs[0]
    #         data = doc.to_dict()
    #         return float(data.get("marketValueTKO", 0))
    #     else:
    #         raise ValueError(f"Không tìm thấy giá cho CD {maCD} vào ngày {today_str}")
        
    # def update_CD_stock_model(maCD, soLuong, is_increase=True):
    #     doc_ref = db.collection("CD").document(maCD)
    #     doc = doc_ref.get()
        
    #     if not doc.exists:
    #         return False

    #     current_data = doc.to_dict()
    #     current_quantity = current_data.get("CDKhaDung", 0)
    #     new_quantity = current_quantity + soLuong if is_increase else current_quantity - soLuong

    #     if new_quantity <= 0:
    #         doc_ref.delete()
    #     else:
    #         doc_ref.update({"CDKhaDung": new_quantity})
        
    #     return True

