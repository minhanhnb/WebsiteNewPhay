from datetime import date, timedelta
from datetime import datetime
from services.lich_Su_GD_service import log_giao_dich_nap
from services.cd_service import get_cd_info
from models.TTT import TTT
from services.Momo_User_Service import withdraw_Cash

#LẤY THÔNG TIN TÚI THẦN TÀI CỦA USER
def get_all_information(name):
    """Lấy tất cả thông tin của người dùng từ TTT
    """
    #Bước 1 : Cập nhật lịch sử Túi: 
    update_tui_lich_su_service(name)
    #Bước 2 : Cập nhật lại lợi nhuận trong ngày 
    return TTT.get_info(name)


#NẠP TIỀN VÀO TÚI THẦN TÀI TỪ VÍ MOMO
#TRƯỚC KHI BẤM SYNC THÌ TIỀN NÀY Ở NET-OFF
def insert_Cash(name, cash):
    """
    Khi thêm cash vào TTT, sẽ đồng thời trừ số tiền này
    từ ví của user (MomoUser).
    Số tiền này sẽ tạm thời được để ở Net Off và chờ Sync
    """
    
    # Bước 1: Rút tiền khỏi ví user (MomoUser)
    withdraw_result = withdraw_Cash(name, cash)
    # Bước 2: Cộng cash vào TTT NET OFF VÀ TTT
    insert_Cash_TTT(cash,name)

    ttt_result = TTT.insertNetOff(name, cash)
    log_giao_dich_nap(name, cash)
    

    return {
        "ttt_update": ttt_result,
        "momo_withdraw": withdraw_result
    }


#LẤY TOÀN BỘ TIỀN MẶT HIỆN CÓ TRONG TÚI THẦN TÀI
def get_all_Cash(name):
    return TTT.get_all_cash(name)

#LẤY NET-OFF ĐANG CÓ TRONG TÚI THẦN TÀI
def get_netOff(name):
    return TTT.get_netoff_by_name(name)

#XÓA NET-OFF SAU KHI SYNC THÀNH CÔNG
def clear_netOff(name):
    return TTT.reset_netoff_by_name(name)


#NẠP TIỀN VÀO TÚI THẦN TÀI, 
def insert_Cash_TTT(cash,name):
    name = "User A"
    return TTT.insert_Cash_Momo(cash, name)


#TESTIN 
def insert_Cash_TTT_test(cash,name):
    print("Tên user là", name)
    print("cash nhận được vào TTT", cash)
    return TTT.insert_Cash_Momo(cash, name)

#RÚT TIỀN TỪ TÀI KHOẢN TIỀN MẶT MOMO TẠI TÚI THẦN TÀI
def withdraw_Cash_Momo(cash, name): 
    name = "User A"
    return TTT.withdraw_Cash_Momo(cash, name)

#RÚT TIỀN TỪ NETOFF TẠI TÚI THẦN TÀI 
def withdraw_NetOff(cash, name): 
    name = "User A"
    return TTT.withdraw_Cash_NetOff(cash, name)


def add_CD_to_TTT(maCD, soLuong, gia, laiSuat):
    """
    Thêm CD vào TTT, sẽ cập nhật số lượng CD trong Firestore
    """
    return TTT.add_CD(maCD, soLuong, gia, laiSuat, name="User A", ngayMua= date.today().strftime("%y-%m-%d")  )

def get_CD_info(name): 
    result = TTT.get_user_cd_list(name)
    return result

def calculate_cd_interest_for_user_service(name):
    """
    Tính lợi nhuận (tiền lãi) thực tế cho từng CD mà user đang giữ
    """
    cd_list = TTT.get_user_cd_list(name)
    results = []

  

    for cd_item in cd_list:
        maCD = cd_item.get("maCD")
        ngayMua = cd_item.get("ngayMua")
        giaMua = cd_item.get("giaMua")  # giá mua ban đầu
        soLuong = cd_item.get("soLuong", 0)

        # Lấy thông tin CD hiện tại từ kho CD
        cd_data = get_cd_info(maCD)
        print(cd_data)
        if not cd_data:
            continue

        market_value_now = cd_data.get("marketValueTKO")
        if market_value_now is None or giaMua is None:
            continue

        try:
            tien_lai = (market_value_now - giaMua) * soLuong
        except Exception:
            tien_lai = 0
        print("Tiền lãi:", tien_lai)

        lai_suat_percent = cd_data.get("laiSuat")

        results.append({
            "maCD": maCD,
            "ngayMua": ngayMua,
            "giaMua": round(giaMua, 2),
            "giaHienTai": round(market_value_now, 3),
            "soLuong": soLuong,
            "laiSuat": round(lai_suat_percent, 2),
            "tienLai": round(tien_lai, 3)
        })
    print(results)

    return results

def predict_cd_interest_service(name, target_date):
    ttt_data = TTT.get_info(name)
    if not ttt_data:
        return []

    cd_list = ttt_data.get("CDHienCo", [])
    results = []

    # Chuyển target_date về dạng datetime
    target_dt = datetime.strptime(target_date, "%Y-%m-%d").date()
    today = datetime.today().date()
    days_diff = (target_dt - today).days

    for cd_item in cd_list:
        maCD = cd_item.get("maCD")
        ngayMua = cd_item.get("ngayMua")
        giaMua = cd_item.get("giaMua")
        soLuong = cd_item.get("soLuong", 0)

        cd_data = get_cd_info(maCD)
        if not cd_data:
            continue

        market_now = cd_data.get("marketValueTKO")
        laiSuat = cd_data.get("laiSuat", 6)  # %/năm

        # Dự đoán giá trị trong tương lai
        giaFuture = market_now * (1 + laiSuat/100 * (days_diff / 365))
        tienLaiFuture = (giaFuture - giaMua) * soLuong
        laiSuatFuture = ((giaFuture - giaMua) / giaMua) * 100
        

        results.append({
            "maCD": maCD,
            "ngayMua": ngayMua,
            "giaMua": round(giaMua, 2),
            "soLuong": soLuong,
            "giaFuture": round(giaFuture, 2),
            "tienLaiFuture": round(tienLaiFuture, 2),
            "laiSuatFuture": round(laiSuatFuture, 2)
        })

    return results


def calculate_user_interest_rate_service(name):
    """
    Tính toán lãi suất và lợi nhuận cho user:
    - % lãi suất trong ngày (%/năm, chưa trừ phí MOMO)
    - % lãi suất thực nhận (%/năm, sau khi trừ phí MOMO)
    - Tiền lãi thực nhận hôm nay dựa trên tổng tài sản hôm qua
    - Chi phí MOMO thu (%) sẽ là phí trên 4% tiền lãi suất trong năm nhận
    Đồng thời update vào DB.
    """
    ttt_data = get_all_information(name)
    print(ttt_data)
    if not ttt_data:
        return {"error": f"User {name} không tồn tại trong TTT"}

    cd_list = ttt_data.get("CDHienCo", [])
   
    lich_su = ttt_data.get("lichSuTui", []) or []

    print(cd_list)
  
    tong_gia_mua_CD_cung_LS = 0
    tien_loi_CD = 0

    for cd in cd_list:
        try:
            ma_CD = cd.get("maCD")
            print(ma_CD)
            cd_data = get_cd_info(ma_CD)
            print(cd_data)
            market_value_now = float(cd_data.get("marketValueTKO") or 0)
            gia_mua = float(cd.get("giaMua", 0) or 0)
            so_luong = int(cd.get("soLuong", 0) or 0)
            lai_suat = float(cd.get("laiSuat", 0) or 0)
            

            tong_gia_mua_CD_cung_LS += (gia_mua * so_luong * lai_suat) / 100
            tien_loi_moi_CD = (market_value_now - gia_mua) * so_luong
            tien_loi_CD += tien_loi_moi_CD
        except Exception as e:
            print("Lỗi khi tính giá CD:", e)
            continue

    print("Tổng giá mua CD cùng lãi suất:", tong_gia_mua_CD_cung_LS)
    print("Tổng  tiền lãi suất:", tien_loi_CD)


    # Xác định ngày hôm qua
    ngay_hqua = (date.today() - timedelta(days=1)).strftime("%y-%m-%d")
    print(ngay_hqua )
    # Tìm tổng tài sản ngày hôm qua trong lịch sử
    tong_tai_san_hqua = 0
    for record in lich_su:
        if record.get("ngay") == ngay_hqua:
            tong_tai_san_hqua = float(record.get("tongTaiSan", 0))
            print("tai san ne")
            print(tong_tai_san_hqua)
            break

    # Nếu không tìm thấy hôm qua => dừng
    if tong_tai_san_hqua == 0:
        TTT.update_lai_suat_thuc_nhan(
        name,
        lai_suat_thuc_nhan = 0,
        lai_thuc_nhan = 0, 
       )

        return {
            "phanTramLaiSuatNgay": 0,
            "laiUserNhan": 0,
            "phanTramMomo": 0,
            "tienLaiUserNhan": 0,
            "tienLaiMomoNhan": 0
        }
        # % lãi suất trong ngày (%/năm, chưa trừ phí MOMO)

    phan_tram_lai_suat_ngay = (
            tong_gia_mua_CD_cung_LS / tong_tai_san_hqua * 100
        )
    print(phan_tram_lai_suat_ngay)



    # Tính phí quản lý MOMO
    if phan_tram_lai_suat_ngay > 4:
        phan_tram_momo = phan_tram_lai_suat_ngay - 4
        lai_suat_user_nhan = phan_tram_lai_suat_ngay - phan_tram_momo
        tien_lai_Momo_nhan =(( (100*phan_tram_momo)/phan_tram_lai_suat_ngay) * tien_loi_CD)/100
    else:
        phan_tram_momo = 0
        lai_suat_user_nhan = phan_tram_lai_suat_ngay
        tien_lai_Momo_nhan = 0

    # Tiền lãi thực nhận hôm nay cho user
    tien_lai_user = tien_loi_CD - tien_lai_Momo_nhan

    # Update DB
    TTT.update_lai_suat_thuc_nhan(
        name,
        lai_suat_user_nhan,
        tien_lai_user
    )

    return {
        "phanTramLaiSuatNgay": round(phan_tram_lai_suat_ngay, 6),
        "laiUserNhan": round(lai_suat_user_nhan, 6),
        "phanTramMomo": round(phan_tram_momo, 6),
        "tienLaiUserNhan": round(tien_lai_user, 6),
        "tienLaiMomoNhan": round(tien_lai_Momo_nhan, 6)
    }


def reduce_TTT_Asset_service(name, maCD, ngayMua, soLuong):
    return TTT.reduce_CD_in_TTT_model(name, maCD, soLuong, ngayMua)



#CẬP NHẬT BIẾN ĐỘNG SỐ DƯ
def update_tui_lich_su_service(name):
    """
    Cập nhật lịch sử biến động túi thần tài cho user:
    - Tính tổng tài sản hiện tại (tiền mặt + giá trị CD)
    - Ghi lại vào field `lichSuTui` trong Firestore
    """
    ttt_data = TTT.get_info(name)
    if not ttt_data:
        return {"error": f"User {name} không tồn tại trong TTT"}

    # Lấy tiền mặt
    tien_mat = float(ttt_data.get("tienMatHienCo", 0))

    # Lấy danh sách CD hiện có
    cd_list = ttt_data.get("CDHienCo", [])
    tong_gia_tri_cd = 0

    for cd in cd_list:
        gia_mua = float(cd.get("giaMua", 0))
        so_luong = int(cd.get("soLuong", 0))
        tong_gia_tri_cd += gia_mua * so_luong

    # Tổng tài sản hiện tại
    tong_tai_san = tien_mat + tong_gia_tri_cd

    # Ghi vào lịch sử túi
    TTT.update_lich_su_tui(
        name=name,
        tong_tai_san=round(tong_tai_san, 2),
    )

    return {
        "status": "ok",
        "tongTaiSan": round(tong_tai_san, 2),
    }
