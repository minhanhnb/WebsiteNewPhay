import datetime
import math
from services.lich_Su_GD_service import log_giao_dich_mua_cd, log_giao_dich_nap
from models.Bank import Bank
from services.TTT_service import  get_CD_info, get_netOff, clear_netOff, get_all_Cash, reduce_TTT_Asset_service
# from services.Momo_User_Service import withdraw_Cash
from services.TTT_service import add_CD_to_TTT, withdraw_Cash_Momo
from services.cd_service import buy_CD, get_all_CD, get_today_market_valueTKO, increase_CD_Stock, sync_today_service
def insert_Cash_Momo(name):
    """
    Khi thêm cash vào bank, cần fetch tiền netoff
    Xóa tiền netoff sau đó
    sẽ thêm vào momo tài khoản tại bank trước, 
    sau đó sẽ chuyển sang tài khoản user sau
    """

    #Bước 1 : Lấy netoff 
    cash = get_netOff(name)
    #Bước 2 : Xóa netoff 
    clear_netOff(name)
    # Bước 2: Nạp tiền vào tài khoản Momo tại Bank
    momo_result = Bank.insert_Cash_MomoAccount_All(cash)
    return momo_result

def insert_Cash_User(cash):
    """
    Khi thêm ,vào momo tài khoản tại bank trước, 
    sau đó sẽ chuyển sang tài khoản user sau
    sau khi thêm user thì sẽ quyết định đi mua CD hay không, sau đó ghi lại lịch sử giao dịch 
    """
    name = "User A"
    # Bước 1: Trừ tiền vào tài khoản Momo tại Bank
    momo_result = Bank.reset_momo_cash(name)
   
    # Bước 2: Cộng cash vào tài khoản user
    user_result = Bank.insert_Cash_UserAccount(cash)
    #Bước 3 : Kiểm tra số dư có đủ mua CD hay không và cập nhật các thứ cần thiết
    new_cash = get_all_Cash(name)
    auto_buy_result = None
    if new_cash >=  100000 : 
        print(f"Auto buying CDs with cash: {new_cash}")
        auto_buy_result = auto_buy_CD_optimized(cash = new_cash) 
        print(f"Auto buy result: {auto_buy_result}")
        tien = auto_buy_result.get("tien_da_mua")
        purchased = auto_buy_result.get("purchased")
        log_giao_dich_mua_cd(name, tien , purchased)


    return {
        "Đã update ": user_result,
        "Đã update" : momo_result,
        "Kết quả mua CD": auto_buy_result
    }




def get_all_info():
    return Bank.get_all_info()

def get_cash_user(name) : 
    return Bank.get_cash(name) 


def increase_User_Asset(maCD, soLuong, giaMua, laiSuat): 
    """
    Thêm CD vào Bank Asset, sẽ cập nhật số lượng CD trong Firestore
    """
    return Bank.increase_User_Asset(maCD, soLuong, giaMua, laiSuat,name="User A", ngayMua= datetime.date.today().strftime("%y-%m-%d") )


def withdraw_User_cash_bank(cash,name): 
    name = "User A"
    return Bank.withdraw_Cash_User(cash, name)


def auto_buy_CD_optimized(cash):
    # Bước 1: sync today
    sync_today_service()

    # Bước 2: Lấy danh sách CD còn hàng, giá >= 100k
    cds = get_all_CD()
    cd_list = [
        {
            "gia": float(cd["marketValueTKO"]),
            "laiSuat": float(cd.get("laiSuat", 0)),
            "maCD": cd["maCD"],
            "stock": int(cd.get("CDKhaDung", 0)),
            "uuTien": int(cd.get("uuTien", 0))
        }
        for cd in cds
        if float(cd["marketValueTKO"]) >= 100000 and int(cd.get("CDKhaDung", 0)) > 0
    ]

    # Nếu không có CD phù hợp
    if not cd_list:
        return {"purchased": [], "cash_con_lai": cash}

    # Bước 3: Sắp xếp theo uuTien ↓, sau đó giá ↓
   # cd_list.sort(key=lambda x: (x["uuTien"], x["gia"]), reverse=False)
    cd_list.sort(key=lambda x: (x["uuTien"], -x["gia"]))


    purchased_summary = []

    # Bước 4: Mua lần lượt từ ưu tiên cao & giá cao
    for cd in cd_list:
        if cash < cd["gia"]:
            continue  # Không đủ tiền mua 1 CD này
        max_can_buy = int(cash // cd["gia"])
        soLuong_mua = min(cd["stock"], max_can_buy)

        if soLuong_mua > 0:
            purchased_summary.append({
                "maCD": cd["maCD"],
                "soLuong": soLuong_mua,
                "gia": cd["gia"],
                "laiSuat": cd["laiSuat"] # Lấy lãi suất nếu có

            })
            cash -= soLuong_mua * cd["gia"]

    # Bước 5: Update DB nếu có mua
    for item in purchased_summary:
        buy_CD(item["maCD"], item["soLuong"])  # giảm tồn kho CD
        add_CD_to_TTT(item["maCD"], item["soLuong"], item["gia"], item["laiSuat"])  # thêm vào TTT
        increase_User_Asset(item["maCD"], item["soLuong"], item["gia"], item["laiSuat"])  # tăng tài sản user

    # Bước 6: Update lại cash của user
    Bank.update_cash(name="User A", new_cash=cash)
    withdraw_Cash_Momo(
        cash=sum(i["gia"] * i["soLuong"] for i in purchased_summary),
        name="User A"
    )
    tien_mua_CD = sum(i["gia"] * i["soLuong"] for i in purchased_summary)

    return {
        "purchased": purchased_summary,
        "cash_con_lai": round(cash, 2), 
        "tien_da_mua" : tien_mua_CD
    }


# def ban_CD(name, so_tien_con_thieu):
#     # Bước 1: Đồng bộ ngày hiện tại
#     sync_today_service()

#     # Bước 2: Lấy danh sách CD của người dùng
#     ds_cd_user = get_CD_info(name)
#     if not ds_cd_user:
#         return [], 0  # Không có CD nào

#     # Bước 3: Lấy giá trị thị trường hôm nay
#     cd_values = []
#     for item in ds_cd_user:
#         maCD = item["maCD"]
#         soLuong = item["soLuong"]
#         gia_ban = get_today_market_valueTKO(maCD)
#         ngay_mua = item["ngayMua"]

#         if gia_ban is None or gia_ban <= 0:
#             continue
        
#         tien_nhan = soLuong * gia_ban
#         cd_values.append({
#             "maCD": maCD,
#             "soLuong": soLuong,
#             "gia_ban": gia_ban,
#             "tien_nhan": tien_nhan,
#             "ngay_mua" : ngay_mua
#         })

#     # Bước 4: Sắp xếp theo giá trị tăng dần
#     cd_values.sort(key=lambda x: x["tien_nhan"])

#     # Bước 5: Tìm CD nhỏ nhất đủ bù đắp
#     for cd in cd_values:
#         if cd["tien_nhan"] >= so_tien_con_thieu:
#             maCD = cd["maCD"]
#             soLuong = cd["soLuong"]
#             gia_ban = cd["gia_ban"]
#             tien_nhan = cd["tien_nhan"]
#             ngayMua = cd["ngay_mua"]

#             # Cập nhật hệ thống
#             increase_CD_Stock(maCD, soLuong)     # tăng lại tồn kho
#             reduce_TTT_Asset_service("User A",maCD, ngayMua, soLuong)    # xóa khỏi TTT
#             reduce_User_Asset_service("User A", maCD,ngayMua, soLuong)     # giảm tài sản user

#             # Trả kết quả
#             cd_ban_log = [{
#                 "maCD": maCD,
#                 "soLuong": soLuong,
#                 "gia_ban": gia_ban,
#                 "tien_nhan": round(tien_nhan, 2)
#             }]
#             return cd_ban_log, round(tien_nhan, 2)

#     # Nếu không tìm thấy CD đủ bù đắp
#     return [], 0

def ban_CD(name, so_tien_con_thieu):
    """
    Bán CD theo từng lô nhỏ nhất cho tới khi đủ số tiền yêu cầu.
    Trả về: (ds_cd_da_ban, tong_tien_thu_duoc)
    Mỗi phần tử ds_cd_da_ban: {"maCD", "soLuong", "gia_ban", "tien_nhan"}
    """
    sync_today_service()

    ds_cd_user = get_CD_info(name)
    if not ds_cd_user:
        return [], 0.0

    # Chuẩn hoá các lô (lot) hợp lệ
    lots = []
    for it in ds_cd_user:
        ma = it["maCD"]
        qty = int(it.get("soLuong", 0))
        price = get_today_market_valueTKO(ma)
        ngay_mua = it.get("ngayMua")
        if qty <= 0 or not price or price <= 0:
            continue
        lots.append({
            "maCD": ma,
            "soLuong": qty,
            "gia_ban": price,
            "ngay_mua": ngay_mua,
            "tien_nhan_toan_bo": qty * price
        })

    if not lots:
        return [], 0.0

    # Sắp xếp: bán lô có tổng giá trị nhỏ trước (chiến lược gốc của bạn)
    lots.sort(key=lambda x: (x["tien_nhan_toan_bo"], x.get("ngay_mua") or ""))

    sold = []
    total_collected = 0.0
    need = float(so_tien_con_thieu)

    for lot in lots:
        if need <= 0:
            break

        unit_price = lot["gia_ban"]
        available = lot["soLuong"]

        # Số lượng nguyên nhỏ nhất cần bán để cover `need`
        qty_needed = math.ceil(need / unit_price)
        qty_to_sell = min(qty_needed, available)
        if qty_to_sell <= 0:
            continue

        money = qty_to_sell * unit_price

        # Cập nhật hệ thống (dùng name thay vì "User A")
        increase_CD_Stock(lot["maCD"], qty_to_sell)
        reduce_TTT_Asset_service(name, lot["maCD"], lot["ngay_mua"], qty_to_sell)
        reduce_User_Asset_service(name, lot["maCD"], lot["ngay_mua"], qty_to_sell)

        sold.append({
            "maCD": lot["maCD"],
            "soLuong": qty_to_sell,
            "gia_ban": unit_price,
            "tien_nhan": round(money, 2)
        })

        total_collected += money
        need -= money
    print("Tổng tiền nhận được", total_collected)

    return sold, round(total_collected, 2)
def reduce_User_Asset_service(user_name, maCD, ngayMua, soLuong):
    return Bank.update_user_asset_model(user_name, maCD, ngayMua, soLuong, is_increase=False)
