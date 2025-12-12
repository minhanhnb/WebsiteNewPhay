# services/lich_su_giao_dich_service.py
from models.lich_Su_GD import LichSuGiaoDich
# 1. Giao dịch nạp tiền
def log_giao_dich_nap(name, so_tien):
    ghi_chu = f"Nạp {so_tien} vào TTT"
    LichSuGiaoDich.insert(name, "NAP", so_tien, ghi_chu)

# 2. Giao dịch mua CD
def log_giao_dich_mua_cd(name, so_tien, danh_sach_mua_cd):
    """
    danh_sach_mua_cd: list các chuỗi mô tả giao dịch mua CD
    Ví dụ: ['Đã mua CD mã ABC giá 102', 'Đã mua CD mã XYZ giá 108']
    """
    ghi_chu = f"Mua CD {danh_sach_mua_cd}"
    LichSuGiaoDich.insert(name, "MUA_CD", so_tien, ghi_chu, danh_sach_mua_cd)

# 3. Giao dịch rút tiền
def log_giao_dich_rut(name, so_tien):
    ghi_chu = f"Rút {so_tien} từ TTT"
    LichSuGiaoDich.insert(name, "RUT", so_tien, ghi_chu)

# 4. Giao dịch bán CD
def log_giao_dich_ban_cd(name, so_tien, danh_sach_ban_cd):
    """
    danh_sach_ban_cd: list các chuỗi mô tả giao dịch bán CD
    Ví dụ: ['Đã bán CD mã ABC thu về 105', 'Không thể bán CD XYZ do chưa đáo hạn']
    """
    ghi_chu = f"Bán CD tổng giá trị {so_tien}"
    LichSuGiaoDich.insert(name, "BAN_CD", so_tien, ghi_chu, danh_sach_ban_cd)


def get_lich_su_giao_dich():
    return LichSuGiaoDich.get_all()
