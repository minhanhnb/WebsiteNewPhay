
# def rut_tien_TTT(name,cash) : 
#     """
#     User rút tiền ở TTT 
#     1. Kiểm tra Net-Off, nếu NetOff khả dụng thì rút ra từ NetOff 
#     2. NetOff không đủ thì phát sinh lệnh rút tiền từ tài khoản tiền mặt tại TTT và tại Bank (rút từ bank về trước)
#     3. Nếu NetOff + Tiền mặt không đủ thì gửi lệnh đi bán CD tại bank, sau khi bán thì tiền CD sẽ vào lại tài khoản tiền mặt Bank 
#     + tài khoản tiền mặt Momo 
#     Các hàm sử dụng trong hàm này : 
#     get_NetOff(name), get_all_Cash(name),  - Hàm này tại TTT
#     withdraw_Cash_Momo(user,name) , withdraw_NetOff(cash,name) - Hàm này tại TTT 
#     insert_Cash(name,cash) - đây làm hàm tăng tiền vào ví Momo
#     Cần viết hàm : 
#     withdraw_User_cash tại Bank 
#     """
import inspect
from models.TTT import TTT
from models.Bank import Bank
from services.Momo_User_Service import insert_Cash_Momo_User
from services.lich_Su_GD_service import log_giao_dich_ban_cd, log_giao_dich_nap, log_giao_dich_rut
from services.bank_service import ban_CD, get_cash_user, withdraw_User_cash_bank
from services.TTT_service import get_all_Cash, get_netOff, insert_Cash, insert_Cash_TTT, insert_Cash_TTT_test, withdraw_Cash_Momo, withdraw_NetOff


def withdrawCash(name, cash):
    """
    User rút tiền ở TTT

    1. Kiểm tra Net-Off → nếu đủ thì rút từ NetOff
    2. Nếu NetOff không đủ → rút hết NetOff, còn thiếu thì rút từ tiền mặt tại Bank trước, sau đó tiền mặt tại TTT
    3. Nếu vẫn không đủ → xử lý mục 3 (bán CD) sau

    Các hàm cần:
        get_NetOff(name)                # Lấy số NetOff khả dụng tại TTT
        get_all_Cash(name)              # Lấy số tiền mặt tại TTT
        withdraw_NetOff(amount, name)   # Trừ tiền NetOff tại TTT
        withdraw_Cash_Momo(amount, name)# Trừ tiền mặt tại TTT
        withdraw_User_cash_bank(amount, name) # Trừ tiền mặt tại Bank
        insert_Cash(name, cash)         # Cộng tiền vào ví Momo
    """
    # 1. Lấy số dư NetOff
    print (name)
    netoff_avail = get_netOff(name)

    cash_TTT = get_all_Cash(name)  # Tiền mặt tại TTT
    cash_bank = get_cash_user(name)  # Tiền mặt tại Bank (cần hàm get_bank_cash)

    print(f"[INFO] NetOff khả dụng: {netoff_avail}, Tiền mặt TTT: {cash_TTT}, Tiền mặt Bank: {cash_bank}")

    # 1. Nếu NetOff đủ
    if netoff_avail >= cash:
        withdraw_NetOff(cash, name)
        #insert_Cash(name, cash)  # Cộng vào ví Momo
        withdraw_Cash_Momo(cash, name)
        insert_Cash_Momo_User(name,cash)
        log_giao_dich_rut(name, cash)
  
        print(f"[DONE] Rút {cash} từ NetOff thành công")
        return True

    # 2. Nếu NetOff không đủ → rút hết NetOff, còn lại lấy từ tiền mặt Bank và TTT
    so_tien_thieu = cash - netoff_avail

    if netoff_avail > 0:
        withdraw_NetOff(netoff_avail, name)
        # insert_Cash(name, netoff_avail)
        print(f"[PARTIAL] Đã rút {netoff_avail} từ NetOff")

    # Sau đó rút tiền mặt từ Bank và TTT 
    if cash_bank >= so_tien_thieu:
        withdraw_Cash_Momo(cash, name)
        withdraw_User_cash_bank(so_tien_thieu, name)  # Hàm cần viết ở Bank
       # insert_Cash(name, so_tien_thieu)
        insert_Cash_Momo_User(name,cash)
        log_giao_dich_rut(name, cash)
        print(f"[DONE] Rút {so_tien_thieu} từ Bank thành công")
        return True
    
    # 3. Nếu vẫn không đủ → xử lý bán CD
    print(f"[ERROR] Không đủ tiền để rút {cash}. NetOff: {netoff_avail}, Tiền mặt TTT: {cash_TTT}, Tiền mặt Bank: {cash_bank}")
    # 3. Nếu vẫn không đủ → xử lý bán CD
    tong_tien_hien_co = netoff_avail + cash_bank
    so_tien_con_thieu = cash - tong_tien_hien_co

    print(f"[INFO] Không đủ tiền mặt + netoff, cần bán CD để bù: {so_tien_con_thieu}")

    # Gọi hàm bán CD để thu về tiền mặt
    cd_ban_log, so_tien_thu_duoc = ban_CD(name, so_tien_con_thieu)

    if so_tien_thu_duoc < so_tien_con_thieu:
        print(f"[FAIL] Bán CD không đủ để bù số tiền còn thiếu {so_tien_con_thieu}")
        return f"❌ Không đủ tài sản để rút {cash}"

    print(so_tien_thu_duoc)
    # Sau khi bán CD → cộng tiền đó vào cashBank và TTT
    Bank.insert_Cash_UserAccount(so_tien_thu_duoc)


    TTT.insert_Cash_Momo_TT(cash_TTT, so_tien_thu_duoc,name)  # Cộng vào TTT



    # Sau đó trừ nốt phần NetOff như case 1
    #Luc nay netOff có thể là số âm 
    print(f"[FINAL] Đã trừ NetOff phần còn lại: {netoff_avail}")
    withdraw_NetOff(netoff_avail, name)
    
    # Update lại cash TTT từ cashBank
    
    withdraw_User_cash_bank(cash, name)

    withdraw_Cash_Momo(cash, name)
    insert_Cash_Momo_User(name, cash)

    # Ghi log giao dịch rút và bán CD
    log_giao_dich_rut(name, cash)
    log_giao_dich_ban_cd(name, so_tien_thu_duoc, cd_ban_log)

    return True

        
    
