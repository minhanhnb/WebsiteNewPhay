from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from config import USER_INTEREST_RATE
from firebase_admin import firestore
import math 

class SystemService:
    def __init__(self, finsight_repo, transaction_repo, cd_repo, bank_repo):
        self.finsight_repo = finsight_repo
        self.transaction_repo = transaction_repo
        self.cd_repo = cd_repo
        self.bank_repo = bank_repo
        
    # def get_full_overview(self, user_id, view_date_str=None):
    #     """
    #     Tổng hợp dữ liệu toàn hệ thống tại thời điểm view_date.
    #     """
    #     # 1. Xác định ngày định giá (Valuation Date)
    #     if view_date_str:
    #         try:
    #             target_date = datetime.strptime(view_date_str, "%Y-%m-%d").date()
    #         except ValueError:
    #             target_date = date.today()
    #     else:
    #         target_date = date.today()

    #     # 2. LẤY VÍ USER
    #     user_wallet = self.finsight_repo.get_user_account(user_id)
        
    #     total_asset_value = 0.0
    #     enriched_assets = []

    #     for asset in user_wallet.assets:
    #         ma_cd = asset.get('maCD')
    #         so_luong = int(asset.get('soLuong', 0))
    #         gia_von = float(asset.get('giaVon', 0))
            
    #         cd_info = self.cd_repo.get_cd_by_id(ma_cd)
            
    #         current_price = 0
    #         if cd_info:
    #             # [UPDATE] Truyền target_date vào hàm tính giá
    #             current_price = self._calculate_cd_price_dynamic(cd_info, target_date)
            
    #         if current_price == 0:
    #             current_price = gia_von

    #         current_value = current_price * so_luong
    #         total_asset_value += current_value
            
    #         asset_view = asset.copy()
    #         asset_view['current_price'] = current_price
    #         asset_view['current_value'] = current_value
    #         enriched_assets.append(asset_view)

    #     total_net_worth = user_wallet.cash + total_asset_value
    #     user_data = user_wallet.to_dict()
    #     user_data['total_net_worth'] = total_net_worth
    #     user_data['total_asset_value'] = total_asset_value
    #     user_data['assets'] = enriched_assets

      

    #     # 2. LẤY QUỸ HỆ THỐNG (FINSIGHT INTERNAL)
    #     system_fund = self.finsight_repo.get_system_account()

    #     # 3. LẤY DỮ LIỆU ĐỐI CHIẾU (NHLK / BANK)
    #     bank_data = self.bank_repo.get_system_bank()

    #    # 4. LẤY SETTLEMENT QUEUE (PENDING LOGS) ---
    #     # Để hiển thị lên Dashboard cho Admin xem trước khi bấm Sync
    #     pending_docs = self.finsight_repo.get_pending_logs()
    #     queue_list = []
    #     for doc in pending_docs:
    #         data = doc.to_dict()
    #         # Format lại data để trả về FE gọn gàng
    #         queue_list.append({
    #             "id": doc.id,
    #             "type": data.get("type"),
    #             "amount": data.get("amount", 0),
    #             "created_at": data.get("created_at") 
    #         })

    #     performance_data = self.get_user_performance(user_id, view_date_str)
    #     return {
    #         "user": user_data,
    #         "finsight": system_fund.to_dict(),
    #         "bank": bank_data.to_dict(),
    #         "queue": queue_list,
    #         "total_balance_estimate": total_net_worth,
    #         "performance": {
    #             "profit_today": performance_data['daily_profit'],
    #             "profit_month": performance_data['monthly_profit'],
    #             "last_updated": performance_data['last_updated']
    #         },
    #         "meta": {
    #             "server_time": datetime.now().isoformat(),
    #             # [UPDATE] Trả về ngày định giá để FE hiển thị đúng
    #             "valuation_date": target_date.isoformat() 
    #         }
    #     }
    def get_full_overview(self, user_id, view_date_str=None):
        """
        [REPLAY MODE - SIMPLIFIED] 
        Tính toán tài sản và lợi nhuận NGÀY (Daily Profit) dựa trên Transaction Log.
        Đã loại bỏ logic tính lãi tháng để tối ưu hiệu năng.
        """
        # 1. Xác định mốc thời gian
        if view_date_str:
            try:
                target_date = datetime.strptime(view_date_str, "%Y-%m-%d").date()
            except ValueError:
                target_date = date.today()
        else:
            target_date = date.today()

        # Chỉ cần ngày hôm qua để so sánh giá và tính lãi ngày
        prev_date = target_date - timedelta(days=1)

        # 2. Lấy TOÀN BỘ Transaction Log của User đến ngày View
        all_txs = self.transaction_repo.get_all_transactions(user_id, target_date.isoformat())

        # 3. Cắt lát dữ liệu (Slicing Transaction List)
        # - List cho ngày View (T) -> Để tính Net Worth hiện tại
        txs_T = all_txs 
        # - List cho ngày hôm qua (T-1) -> Để biết đêm qua user nắm giữ gì (tính lãi ngày)
        txs_Prev = [t for t in all_txs if t['date'] <= prev_date.isoformat()]

        # 4. Tái tạo trạng thái (Reconstruct)
        port_T = self._reconstruct_portfolio(txs_T)
        port_Prev = self._reconstruct_portfolio(txs_Prev)

        # 5. Tính giá trị tài sản tại ngày View (T) và Daily Profit
        total_asset_value_T = 0.0
        daily_profit = 0.0
        enriched_assets = []

        # Duyệt qua các CD user đang có tại ngày T
        for ma_cd, qty_T in port_T['assets'].items():
            if qty_T <= 0: continue

            cd_info = self.cd_repo.get_cd_by_id(ma_cd)
            if not cd_info: continue

            # A. Giá trị hiện tại (Market Value)
            price_T = self._calculate_cd_price_dynamic(cd_info, target_date)
            val_T = price_T * qty_T
            total_asset_value_T += val_T

            # B. Tính lãi ngày (Dựa trên số lượng của NGÀY HÔM QUA)
            # Logic: Lãi chỉ sinh ra từ những CD đã nắm giữ qua đêm.
            # Công thức: (Giá T - Giá T-1) * Số lượng nắm giữ tại T-1
            qty_Prev = port_Prev['assets'].get(ma_cd, 0)
            
            if qty_Prev > 0:
                price_Prev = self._calculate_cd_price_dynamic(cd_info, prev_date)
                # Chỉ tính chênh lệch khi cả 2 ngày đều có giá (đã phát hành)
                if price_T > 0 and price_Prev > 0:
                    daily_profit += (price_T - price_Prev) * qty_Prev

            enriched_assets.append({
                "maCD": ma_cd,
                "soLuong": qty_T,
                "current_price": price_T,
                "current_value": val_T
            })

        net_worth_T = port_T['cash'] + total_asset_value_T

        # 6. Lấy dữ liệu phụ trợ (System Fund, Bank, Queue) - Giữ nguyên
        system_fund = self.finsight_repo.get_system_account()
        bank_data = self.bank_repo.get_system_bank()
        pending_docs = self.finsight_repo.get_pending_logs()
        queue_list = []
        for doc in pending_docs:
             d = doc.to_dict()
             queue_list.append({
                "id": doc.id, "type": d.get("type"),
                "amount": d.get("amount", 0), "created_at": d.get("created_at")
             })

        return {
            "user": {
                "uid": user_id,
                "cash": port_T['cash'],          # Cash tính lại từ log
                "assets": enriched_assets,       # Assets tính lại từ log
                "total_net_worth": net_worth_T,
                "total_asset_value": total_asset_value_T
            },
            "performance": {
                "profit_today": daily_profit,
                "last_updated": datetime.now().strftime("%H:%M:%S")
            },
            "meta": {
                "server_time": datetime.now().isoformat(),
                "valuation_date": target_date.isoformat(),
                "mode": "REPLAY_SIMPLE" 
            },
            "finsight": system_fund.to_dict(),
            "bank": bank_data.to_dict(),
            "queue": queue_list,
            "total_balance_estimate": net_worth_T
        }
   
    # --- 1. TÍNH TỔNG TÀI SẢN (Dùng cho UI TTT Dashboard) ---
    def calculate_user_net_worth(self, user_id, date_str=None):
        if date_str:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        else:
            target_date = date.today()

        # Lấy trực tiếp từ Finsight Users
        user_acc = self.finsight_repo.get_user_account(user_id)
        
        # Balance = Tiền mặt + Giá trị Tài sản
        total_val = user_acc.cash
        
        for asset in user_acc.assets:
            ma_cd = asset.get('maCD')
            so_luong = int(asset.get('soLuong', 0))
            cd_info = self.cd_repo.get_cd_by_id(ma_cd)
            if cd_info:
                price = self._calculate_cd_price_dynamic(cd_info, target_date)
                total_val += price * so_luong
        
        return total_val

    # --- 2. NẠP TIỀN ---
    def process_deposit(self, user_id, amount, date_str):
        # 1. User: Tăng Cash Remainder
        self.finsight_repo.update_user_cash(user_id, amount)
        
        # 2. Log System (Chờ Sync)
        self.finsight_repo.add_settlement_log(user_id, "CASH_IN", amount)
        
        # 3. Log History

        self._log_transaction_async(user_id, "NAP", amount, date_str, "Nạp vào TTT")
        
        return {"status": "success", "message": "Nạp tiền thành công (Đã vào Cash Remainder)"}

    # --- 3. PHÂN BỔ (MUA CD TỪ FINSIGHT) ---
    def process_asset_allocation(self, user_id, date_str=None):
        try: 
            if date_str:
                allocation_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            else:
                allocation_date = date.today()
                date_str = allocation_date.isoformat()

            # Lấy tiền từ Finsight User Account
            user_acc = self.finsight_repo.get_user_account(user_id)
            available_cash = user_acc.cash

            if available_cash <= 0:
                return {"status": "error", "message": "Cash Remainder bằng 0."}

            available_cds = self.cd_repo.get_sellable_cds()
            processed_cds = []
            for cd in available_cds:
                p = self._calculate_cd_price_dynamic(cd, allocation_date)
                if p > 0:
                    cd['current_price'] = p
                    processed_cds.append(cd)
            processed_cds.sort(key=lambda x: x['current_price'], reverse=True)

            shopping_cart = []
            current_assets = list(user_acc.assets)
            total_cost = 0
            db_record_list = [] 
            remaining_cash = available_cash
            
            # --- LOGIC MỚI: Tối ưu danh sách tài sản hiện có ---
            # Chuyển list assets sang dict để tra cứu nhanh { "Mã_CD": asset_object }
            asset_map = { asset['maCD']: asset for asset in current_assets }

            for cd in processed_cds:
                if remaining_cash <= 0: break
                
                price = cd['current_price']
                stock = cd['real_stock']
                cd_id = cd['thongTinChung']['maDoiChieu']
                
                qty = min(int(remaining_cash // price), stock)
                
                if qty > 0:
                    cost = qty * price
                    shopping_cart.append({"maCD": cd_id, "soLuong": qty})
                    
                    # Object chi tiết của lần giao dịch này
                    new_asset_record = {
                        "maCD": cd_id, 
                        "soLuong": qty, 
                        "giaVon": price, 
                        "ngayMua": date_str
                    }
                    db_record_list.append(new_asset_record)
                    
                    # --- CẬP NHẬT DANH MỤC TÀI SẢN (GOM NHÓM) ---
                    if cd_id in asset_map:
                        # Nếu đã có -> Cộng dồn số lượng
                        # Lưu ý: Giá vốn trung bình (Average Cost) là logic phức tạp hơn.
                        # Ở đây ta giữ nguyên giá vốn của lô cũ hoặc cập nhật theo logic FIFO/LIFO.
                        # Để đơn giản: Chỉ cộng số lượng.
                        existing_asset = asset_map[cd_id]
                        existing_asset['soLuong'] = int(existing_asset['soLuong']) + qty
                        
                        # (Optional) Cập nhật ngày mua mới nhất
                        existing_asset['ngayMua'] = date_str 
                    else:
                        # Nếu chưa có -> Thêm mới vào map
                        asset_map[cd_id] = new_asset_record
                    
                    remaining_cash -= cost
                    total_cost += cost

            if not shopping_cart:
                return {"status": "warning", "message": "Không mua được CD nào."}

            # Chuyển lại Map thành List để lưu vào DB
            updated_assets_list = list(asset_map.values())

            # 1. User Account: Deduct cash
            self.finsight_repo.update_user_cash(user_id, -total_cost) 
            # 2. FS Account: Add cash (Revenue)
            self.finsight_repo.update_system_cash(total_cost)
            # 3. Log 1: Ghi nhận tiền đã được trả
            self.finsight_repo.add_settlement_log(
                user_id, "ALLOCATION_CASH_PAID", total_cost
            )

            # =======================================================
            # PHA 2: ASSET ALLOCATION (T+n) - Chuyển giao Tài sản
            # =======================================================

            # 1. User Account: Update danh sách tài sản (thêm CD mới)
            self.finsight_repo.update_user_assets(user_id, updated_assets_list)            
            # 2. CD Inventory: Giảm số lượng CD trong kho
            for item in shopping_cart:
                 self.cd_repo.decrease_stock(item['maCD'], item['soLuong'])

            # 3. Log 2: Ghi nhận tài sản đã được giao
            self.finsight_repo.add_settlement_log(
                user_id, 
                "ALLOCATION_ASSET_DELIVERED", 
                total_cost, 
                {"assets": db_record_list} # Lưu chi tiết asset đã giao
            )
            self._log_transaction_async(
                user_id, 
                "ALLOCATION", 
                total_cost, 
                date_str, 
                f"Phân bổ {len(shopping_cart)} loại CD", 
                details={"assets": shopping_cart} # Cần lưu cái này để tính lại được số lượng
            )

            return {
                "status": "success",
                "message": f"Phân bổ thành công! Tiền đã trừ, tài sản chờ đồng bộ Bank.",
                "details": shopping_cart
            }

        except Exception as e:
            # ... (Xử lý lỗi) ...
            return {"status": "error", "message": str(e)}


    # --- 4. RÚT TIỀN (Trừ Cash -> Thiếu thì Bán CD cho FS) ---
    def process_withdrawal(self, user_id, amount, date_str):
        trans_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else date.today()
        amount = float(amount)
        
        user_acc = self.finsight_repo.get_user_account(user_id)
        current_cash = user_acc.cash
        print("Bán CD ngày", date_str)
        
        # A. Đủ Cash
        if current_cash >= amount:
            self.finsight_repo.update_user_cash(user_id, -amount)
            self.finsight_repo.add_settlement_log(user_id, "CASH_OUT", amount)
            self._log_transaction(user_id, "RUT", amount, date_str, "Rút từ Cash Remainder")
            return {"status": "success", "message": "Rút tiền thành công"}

        # B. Thiếu Cash -> Bán CD
        shortage = amount - current_cash
        assets_to_sell = []
        remaining_assets = []
        cash_raised = 0
        
        for asset in user_acc.assets:
            if shortage <= 0:
                remaining_assets.append(asset)
                continue
            
            ma_cd = asset.get('maCD')
            so_luong = int(asset.get('soLuong'))
            cd_info = self.cd_repo.get_cd_by_id(ma_cd)
            
            price = self._calculate_cd_price_dynamic(cd_info, trans_date)
            qty = min(math.ceil(shortage / price), so_luong)
            
            revenue = qty * price
            cash_raised += revenue
            shortage -= revenue
            
            assets_to_sell.append({"maCD": ma_cd, "soLuong": qty})
            
            if so_luong - qty > 0:
                new_as = asset.copy()
                new_as['soLuong'] = so_luong - qty
                remaining_assets.append(new_as)

        if (current_cash + cash_raised) < amount:
            return {"status": "error", "message": "Tổng tài sản không đủ."}

        # EXECUTE
        # 1. Trả kho CD
        for item in assets_to_sell:
            self.cd_repo.increase_stock(item['maCD'], item['soLuong'])

        # 2. User Account: Asset Giảm, Cash Tăng (tạm thời), sau đó Cash Giảm (do Rút)
        # Net Cash Change = Tiền bán được - Số tiền rút
        net_change = cash_raised - amount
        
        self.finsight_repo.update_user_assets(user_id, remaining_assets)
        self.finsight_repo.update_user_cash(user_id, net_change)

        # 3. FS Account: Tiền mặt Giảm (Do phải bỏ tiền mua lại CD)
        self.finsight_repo.update_system_cash(-cash_raised)

        # 4. Log Sync
        self.finsight_repo.add_settlement_log(user_id, "LIQUIDATE_CD", cash_raised, {"sold": assets_to_sell})
        self.finsight_repo.add_settlement_log(user_id, "CASH_OUT", amount)
        
        self._log_transaction_async(
                user_id,
                "LIQUIDATE_CD", # Tương đương SELL
                cash_raised,
                date_str,
                "Bán CD để rút tiền",
                details={"sold": assets_to_sell} # Lưu list đã bán để trừ khi Replay
            )
        self._log_transaction_async(
            user_id, "RUT", amount, date_str, "Rút tiền mặt"
        )
        return {"status": "success", "message": "Rút tiền & Thanh khoản thành công"}


    def reset_database(self):
            """
            DANGER: Xóa TOÀN BỘ dữ liệu (Bao gồm cả Sub-collections lịch sử).
            Dùng cho mục đích Reset Test Case.
            """
            db = firestore.client()
            batch = db.batch()
            count = 0
            deleted_count = 0

            # Hàm helper nội bộ để commit khi batch đầy (Limit 500 ops)
            def commit_if_needed():
                nonlocal count, batch
                if count >= 400:
                    batch.commit()
                    batch = db.batch()
                    count = 0

            try:
                # --- 1. XỬ LÝ FINSIGHT_USERS (Phức tạp nhất vì có Sub-collections) ---
                users = db.collection('finsight_users').stream()
                
                for user in users:
                    # A. Xóa Sub-collection: profit_history
                    profits = user.reference.collection('profit_history').stream()
                    for p in profits:
                        batch.delete(p.reference)
                        count += 1
                        deleted_count += 1
                        commit_if_needed()

                    # B. Xóa Sub-collection: daily_snapshots
                    snaps = user.reference.collection('daily_snapshots').stream()
                    for s in snaps:
                        batch.delete(s.reference)
                        count += 1
                        deleted_count += 1
                        commit_if_needed()

                    # C. Xóa User Document chính
                    batch.delete(user.reference)
                    count += 1
                    deleted_count += 1
                    commit_if_needed()

                # --- 2. XỬ LÝ CÁC COLLECTION CẤP CAO KHÁC ---
                target_collections = [
                    'finsight_system',      # Quỹ hệ thống
                    'bank',                 # NHLK
                    'transactions',         # Lịch sử giao dịch
                    'settlement_queue'      # Log chờ Sync
                ]

                for coll_name in target_collections:
                    coll_ref = db.collection(coll_name)
                    docs = coll_ref.stream()
                    
                    for doc in docs:
                        batch.delete(doc.reference)
                        count += 1
                        deleted_count += 1
                        commit_if_needed()
                
                # Commit những gì còn sót lại trong batch cuối
                if count > 0:
                    batch.commit()

                return {
                    "status": "success", 
                    "message": f"Hệ thống đã được RESET sạch sẽ! Đã xóa {deleted_count} items (bao gồm cả Profit & Snapshots)."
                }

            except Exception as e:
                print(f"Reset Error: {e}")
                return {"status": "error", "message": str(e)}
    def sync_batch_to_bank(self):
        logs = self.finsight_repo.get_pending_logs() #
        processed_ids = []
        
        # [NEW] Tách biệt dòng tiền của 2 đối tượng để đối soát
        user_net_cash_flow = 0.0
        finsight_net_cash_flow = 0.0 

        cd_objects_to_add = []      
        cd_objects_to_remove = []   
        
        for doc in logs:
            log = doc.to_dict()
            l_type = log.get('type')
            amt = float(log.get('amount', 0))
            
            # --- 1. CASH FLOW LOGIC ---
            if l_type == 'CASH_IN':
                # Nạp tiền: Tiền vào User (Từ nguồn ngoài), Finsight không đổi
                user_net_cash_flow += amt

            elif l_type == 'CASH_OUT':
                # Rút tiền: Tiền ra khỏi User, Finsight không đổi
                user_net_cash_flow -= amt

            elif l_type == 'ALLOCATION_CASH_PAID':
                # [REQ] Mua CD: User TRẢ tiền (-), Finsight NHẬN tiền (+)
                user_net_cash_flow -= amt
                finsight_net_cash_flow += amt 
            
            elif l_type == 'LIQUIDATE_CD':
                # [AUTO] Bán CD (Rút vốn): User NHẬN tiền (+), Finsight TRẢ tiền (-)
                # (Logic này đi kèm với việc update User Cash khi thanh khoản)
                user_net_cash_flow += amt
                finsight_net_cash_flow -= amt

                # Xử lý Asset của việc bán (Remove khỏi ví User)
                sold_items = log.get('details', {}).get('sold', [])
                for item in sold_items:
                    cd_objects_to_remove.append(item)

            # --- 2. ASSET TRANSFER LOGIC ---
            elif l_type == 'ALLOCATION_ASSET_DELIVERED':
                # Nhận CD về ví
                assets_delivered = log.get('details', {}).get('assets', [])
                for asset in assets_delivered:
                    cd_objects_to_add.append(asset) 
            
            processed_ids.append(doc.id)

        if not processed_ids: 
            return {"status": "warning", "message": "Không có gì để Sync"}
        
        # --- THỰC HIỆN GHI VÀO DB (BANK REPO) ---

        # 1. Update User Cash
        if user_net_cash_flow != 0:
            self.bank_repo.update_user_cash(user_net_cash_flow) #
        
        # 2. [NEW] Update Finsight System Cash (Đối ứng)
        # Bạn cần đảm bảo BankRepo đã có hàm update_system_cash
        if finsight_net_cash_flow != 0:
            self.bank_repo.update_system_cash(finsight_net_cash_flow)

        # 3. Update Assets Ownership
        if cd_objects_to_add or cd_objects_to_remove:
            self.bank_repo.sync_assets_ownership(cd_objects_to_add, cd_objects_to_remove) #

        # 4. Đánh dấu đã xử lý
        self.finsight_repo.mark_logs_processed(processed_ids) #
        
        return {
            "status": "success", 
            "message": (f"Đã Sync NHLK.\n"
                        f"- User Cash: {user_net_cash_flow:+,.0f}\n"
                        f"- Finsight Cash: {finsight_net_cash_flow:+,.0f}\n"
                        f"- Assets: +{len(cd_objects_to_add)} / -{len(cd_objects_to_remove)}")
        }
    # ... Helper Functions cũ (tính giá, log trans...) giữ nguyên ...
    def _calculate_cd_price_dynamic(self, cd, date):
        # (Copy y nguyên hàm cũ)
        try:
            c1 = cd.get("thongTinChung", {})
            c2 = cd.get("thongTinLaiSuat", {})
            menh_gia = float(str(c1.get("menhGia", 0)).replace('.', '').replace(',', '.'))
            def parse_d(d_str):
                try: return datetime.strptime(d_str, "%Y-%m-%d").date()
                except: return None
            ngay_ph = parse_d(c1.get("ngayPhatHanh"))
            ngay_dh = parse_d(c1.get("ngayDaoHan"))
            lai_suat_cd = float(str(c2.get("laiSuat", 0)).replace(',', '.')) / 100
            r_user = USER_INTEREST_RATE / 100.0
            tan_suat = c2.get("tanSuatTraLai", "Cuối kỳ")
            if not ngay_ph or not ngay_dh or date < ngay_ph: return 0.0 
            first_next = self._get_next_coupon_date(ngay_ph, ngay_dh, tan_suat, ngay_ph)
            base = self._calculate_yield_formula(menh_gia, lai_suat_cd, r_user, first_next, ngay_ph, ngay_ph, ngay_dh)
            days = (date - ngay_ph).days
            return round(base + (base * r_user * days) / 365, 2)
        except: return 0.0

    def _calculate_yield_formula(self, M, r_CD, r_User, next_date, curr_date, issue_date, maturity_date):
        if curr_date >= maturity_date: return M + (M * r_CD * (maturity_date - issue_date).days / 365)
        fv = M + (M * r_CD * (maturity_date - issue_date).days / 365)
        days = max(0, (next_date - curr_date).days)
        return fv / (1 + (r_User * days) / 365)

    def _get_next_coupon_date(self, start, end, freq, curr):
        s = (freq or "").lower()
        if "cuối kỳ" in s: return end
        months = 12
        if "3 tháng" in s: months = 3
        elif "6 tháng" in s: months = 6
        elif "1 tháng" in s: months = 1
        d = start
        while d <= curr:
            d = d + relativedelta(months=months)
            if d > end: return end
        return d

    # Thêm tham số details
    # [UPDATE] Thêm tham số details=None
    def _log_transaction_async(self, uid, action, amt, date, note, details=None):
        """
        Wrapper để chạy hàm ghi log trong Thread riêng.
        Giúp API return ngay lập tức (Non-blocking).
        """
        def task():
            try:
                # Gọi hàm log cũ (nhưng giờ chạy ngầm)
                self._log_transaction(uid, action, amt, date, note, details)
            except Exception as e:
                print(f"[ASYNC LOG ERROR] {e}") # Nên dùng logging system chuẩn hơn print

        # Submit task vào pool -> Chạy ngay lập tức ở background
        self.log_executor.submit(task)
    def _log_transaction(self, uid, action, amt, date, note, details=None):
        txn_data = {
            "user_id": uid,
            "type": action,
            "amount": float(amt), 
            "date": date,
            "note": note,
            "created_at": datetime.now()
        }
        if details:
            txn_data['details'] = details # Lưu JSON details (quan trọng cho Replay)

        self.transaction_repo.add_transaction(txn_data)
    # --- 1. TÍNH HIỆU SUẤT ĐẦU TƯ (PROFIT) ---
    def get_user_performance(self, user_id, view_date_str=None):
        """
        Tính toán hiệu suất đầu tư (P&L).
        [TEST MODE]: Tự động lưu (Chốt lời) ngay khi gọi hàm.
        """
        # 1. Xử lý ngày tháng (Target Date)
        if view_date_str:
            try:
                target_date = datetime.strptime(view_date_str, "%Y-%m-%d").date()
            except ValueError:
                target_date = date.today()
        else:
            target_date = date.today()
            
        today_str = target_date.isoformat()
        yesterday = target_date - timedelta(days=1)
        
        # 2. --- TÍNH LÃI NGÀY (DAILY PROFIT) ---
        user_acc = self.finsight_repo.get_user_account(user_id)
        current_assets = user_acc.assets
        
        daily_profit = 0.0
        
        for asset in current_assets:
            ma_cd = asset.get('maCD')
            so_luong = int(asset.get('soLuong', 0))
            
            cd_info = self.cd_repo.get_cd_by_id(ma_cd)
            
            if cd_info:
                # Tính chênh lệch giá: (Hôm nay - Hôm qua)
                price_today = self._calculate_cd_price_dynamic(cd_info, target_date)
                price_yesterday = self._calculate_cd_price_dynamic(cd_info, yesterday)
                
                diff = price_today - price_yesterday
                
                # Chỉ tính khi có lợi nhuận (Hoặc cả lỗ nếu muốn)
                daily_profit += (diff * so_luong)

        # 3. --- [QUAN TRỌNG] LƯU NGAY VÀO DB (CHỐT SỔ LUÔN) ---
        # Vì là môi trường Test, ta coi lần xem cuối cùng là lần chốt sổ chuẩn nhất.
        try:
            self.finsight_repo.save_daily_profit(user_id, today_str, daily_profit)
        except Exception as e:
            print(f"Lỗi khi auto-save profit: {e}")

        # 4. --- TÍNH TỔNG LÃI THÁNG (MONTHLY PROFIT) ---
        start_of_month = target_date.replace(day=1).isoformat()
        
        # Lấy lịch sử từ đầu tháng đến HÔM QUA (để tránh cộng trùng hôm nay vừa lưu)
        # Hoặc: Lấy hết đến hôm nay và cộng lại (Simple & Safe)
        past_profits = self.finsight_repo.get_profit_history(user_id, start_of_month, today_str)
        
        # Cộng tổng (Vì bước 3 đã lưu hôm nay vào DB rồi, nên query sẽ có cả hôm nay)
        monthly_profit = sum(p['amount'] for p in past_profits)

        return {
            "daily_profit": daily_profit,
            "monthly_profit": monthly_profit,
            "last_updated": datetime.now().strftime("%H:%M:%S") # Để hiện lên UI cho ngầu
        }
    

    def ensure_data_consistency(self, user_id):
        """
        [FIXED] Thuật toán Back-fill thông minh:
        Chỉ tính toán tài sản nếu ngày xem >= ngày mua tài sản đó.
        """
        today = date.today()
        
        # 1. Lấy trạng thái hiện tại
        user_acc = self.finsight_repo.get_user_account(user_id)
        current_assets = user_acc.assets
        current_cash = user_acc.cash
        
        # 2. Tìm ngày snapshot cuối cùng
        last_snap = self.finsight_repo.get_latest_snapshot(user_id)
        
        if last_snap:
            try:
                last_date = datetime.strptime(last_snap['date'], "%Y-%m-%d").date()
                start_date = last_date + timedelta(days=1)
            except:
                start_date = today.replace(day=1)
        else:
            # Nếu user mới -> Bắt đầu từ ngày đầu tiên mua tài sản (để tránh loop vô ích từ đầu tháng)
            # Hoặc mặc định đầu tháng này
            start_date = today.replace(day=1)

        if start_date > today: return

        # 3. Vòng lặp tính toán bù
        snapshots_to_save = []
        profits_to_save = []
        
        iter_date = start_date
        
        while iter_date <= today:
            iter_date_str = iter_date.isoformat()
            yesterday = iter_date - timedelta(days=1)
            
            daily_total_asset_value = 0
            daily_profit = 0
            snapshot_assets_detail = []
            
            for asset in current_assets:
                ma_cd = asset.get('maCD')
                so_luong_goc = int(asset.get('soLuong', 0))
                
                # [QUAN TRỌNG] Logic check Ngày Mua
                ngay_mua_str = asset.get('ngayMua') # Cần đảm bảo lúc mua có lưu trường này
                
                # Nếu asset không có ngày mua (dữ liệu cũ), ta tạm chấp nhận tính luôn
                # Nếu có ngày mua, phải check: iter_date >= ngay_mua mới được tính
                if ngay_mua_str:
                    try:
                        ngay_mua = datetime.strptime(ngay_mua_str, "%Y-%m-%d").date()
                        if iter_date < ngay_mua:
                            continue # Chưa mua tại thời điểm này -> Bỏ qua
                    except:
                        pass # Lỗi parse ngày thì bỏ qua check, tính như bình thường

                cd_info = self.cd_repo.get_cd_by_id(ma_cd)
                if cd_info:
                    p_curr = self._calculate_cd_price_dynamic(cd_info, iter_date)
                    p_prev = self._calculate_cd_price_dynamic(cd_info, yesterday)
                    
                    # 1. Snapshot Value
                    daily_total_asset_value += (p_curr * so_luong_goc)
                    
                    snapshot_assets_detail.append({
                        "maCD": ma_cd,
                        "soLuong": so_luong_goc,
                        "price": p_curr,
                        "value": p_curr * so_luong_goc
                    })
                    
                    # 2. Daily Profit (Chỉ tính nếu hôm qua cũng đã có CD này)
                    # Logic: Nếu hôm qua < ngày mua -> Profit = 0 (vì mới mua hôm nay)
                    is_held_yesterday = True
                    if ngay_mua_str:
                         ngay_mua = datetime.strptime(ngay_mua_str, "%Y-%m-%d").date()
                         if yesterday < ngay_mua:
                             is_held_yesterday = False
                    
                    if is_held_yesterday and p_curr > 0 and p_prev > 0:
                        daily_profit += ((p_curr - p_prev) * so_luong_goc)

            # Lưu Snapshot
            snapshots_to_save.append({
                "date": iter_date_str,
                "user_id": user_id,
                "cash": current_cash, 
                "total_asset_value": daily_total_asset_value,
                "total_net_worth": current_cash + daily_total_asset_value,
                "assets": snapshot_assets_detail,
                "created_at": datetime.now()
            })
            
            # Lưu Profit
            profits_to_save.append({
                "date": iter_date_str,
                "amount": daily_profit,
                "updated_at": datetime.now(),
                "note": "Back-filled via Smart Logic"
            })

            iter_date += timedelta(days=1)
            
        if snapshots_to_save:
            self.finsight_repo.save_batch_data(user_id, snapshots_to_save, profits_to_save)

    def _reconstruct_portfolio(self, transactions):
        portfolio = {"cash": 0.0, "assets": {}}

        for tx in transactions:
            t_type = tx.get('type')     
            amount = float(tx.get('amount', 0))
            details = tx.get('details', {}) or {}

            # 1. CASH FLOW
            if t_type in ['NAP', 'CASH_IN', 'LIQUIDATE_CD', 'SELL']:
                portfolio['cash'] += amount
            elif t_type in ['RUT', 'CASH_OUT', 'ALLOCATION', 'BUY']:
                portfolio['cash'] -= amount

            # 2. ASSET FLOW
            # [FIX] Logic xử lý ALLOCATION (Mua)
            if t_type in ['ALLOCATION', 'BUY']:
                # details = {"assets": [{"maCD": "A", "soLuong": 10}]}
                items = details.get('assets', [])
                for item in items:
                    ma = item.get('maCD')
                    qty = int(item.get('soLuong', 0))
                    portfolio['assets'][ma] = portfolio['assets'].get(ma, 0) + qty

            # [FIX] Logic xử lý LIQUIDATE_CD (Bán)
            elif t_type in ['LIQUIDATE_CD', 'SELL']:
                # details = {"sold": [{"maCD": "A", "soLuong": 5}]}
                items = details.get('sold', []) 
                # Lưu ý: check key 'sold' hoặc 'assets' tùy lúc log
                if not items: items = details.get('assets', []) 

                for item in items:
                    ma = item.get('maCD')
                    qty = int(item.get('soLuong', 0))
                    curr = portfolio['assets'].get(ma, 0)
                    portfolio['assets'][ma] = max(0, curr - qty)

        return portfolio