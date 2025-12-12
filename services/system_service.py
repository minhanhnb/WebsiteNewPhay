from datetime import datetime, date
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
        
    def get_full_overview(self, user_id, view_date_str=None):
        """
        Tổng hợp dữ liệu toàn hệ thống tại thời điểm view_date.
        """
        # 1. Xác định ngày định giá (Valuation Date)
        if view_date_str:
            try:
                target_date = datetime.strptime(view_date_str, "%Y-%m-%d").date()
            except ValueError:
                target_date = date.today()
        else:
            target_date = date.today()

        # 2. LẤY VÍ USER
        user_wallet = self.finsight_repo.get_user_account(user_id)
        
        total_asset_value = 0.0
        enriched_assets = []

        for asset in user_wallet.assets:
            ma_cd = asset.get('maCD')
            so_luong = int(asset.get('soLuong', 0))
            gia_von = float(asset.get('giaVon', 0))
            
            cd_info = self.cd_repo.get_cd_by_id(ma_cd)
            
            current_price = 0
            if cd_info:
                # [UPDATE] Truyền target_date vào hàm tính giá
                current_price = self._calculate_cd_price_dynamic(cd_info, target_date)
            
            if current_price == 0:
                current_price = gia_von

            current_value = current_price * so_luong
            total_asset_value += current_value
            
            asset_view = asset.copy()
            asset_view['current_price'] = current_price
            asset_view['current_value'] = current_value
            enriched_assets.append(asset_view)

        total_net_worth = user_wallet.cash + total_asset_value
        user_data = user_wallet.to_dict()
        user_data['total_net_worth'] = total_net_worth
        user_data['total_asset_value'] = total_asset_value
        user_data['assets'] = enriched_assets

      

        # 2. LẤY QUỸ HỆ THỐNG (FINSIGHT INTERNAL)
        system_fund = self.finsight_repo.get_system_account()

        # 3. LẤY DỮ LIỆU ĐỐI CHIẾU (NHLK / BANK)
        bank_data = self.bank_repo.get_system_bank()

       # 4. LẤY SETTLEMENT QUEUE (PENDING LOGS) ---
        # Để hiển thị lên Dashboard cho Admin xem trước khi bấm Sync
        pending_docs = self.finsight_repo.get_pending_logs()
        queue_list = []
        for doc in pending_docs:
            data = doc.to_dict()
            # Format lại data để trả về FE gọn gàng
            queue_list.append({
                "id": doc.id,
                "type": data.get("type"),
                "amount": data.get("amount", 0),
                "created_at": data.get("created_at") 
            })

        return {
            "user": user_data,
            "finsight": system_fund.to_dict(),
            "bank": bank_data.to_dict(),
            "queue": queue_list,
            "total_balance_estimate": total_net_worth,
            "meta": {
                "server_time": datetime.now().isoformat(),
                # [UPDATE] Trả về ngày định giá để FE hiển thị đúng
                "valuation_date": target_date.isoformat() 
            }
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
        self._log_transaction(user_id, "NAP", amount, date_str, "Nạp vào Finsight Cash")
        
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
        
        self._log_transaction(user_id, "RUT", amount, date_str, f"Rút (Bán {len(assets_to_sell)} CD)")
        return {"status": "success", "message": "Rút tiền & Thanh khoản thành công"}

    def reset_database(self):
        """
        DANGER: Xóa toàn bộ dữ liệu trong các Collection của hệ thống.
        Dùng cho mục đích Reset Test Case.
        """
        db = firestore.client()
        
        # Danh sách các collection cần xóa
        target_collections = [
            'finsight_users',       # Ví User
            'finsight_system',      # Quỹ hệ thống
            'bank',                 # NHLK
            'transactions',         # Lịch sử giao dịch
            'settlement_queue'      # Log chờ Sync
        ]

        deleted_count = 0

        try:
            for coll_name in target_collections:
                coll_ref = db.collection(coll_name)
                # Xóa từng document trong collection (Batch delete để nhanh hơn)
                docs = coll_ref.stream()
                batch = db.batch()
                count = 0
                
                for doc in docs:
                    batch.delete(doc.reference)
                    count += 1
                    deleted_count += 1
                    # Firestore giới hạn batch 500 ops
                    if count >= 400:
                        batch.commit()
                        batch = db.batch()
                        count = 0
                
                if count > 0:
                    batch.commit() # Commit phần còn lại

            # Reset lại User Default và System Account về trạng thái ban đầu (Optional)
            # Nếu muốn sạch trơn thì không cần làm gì thêm.
            
            return {
                "status": "success", 
                "message": f"Hệ thống đã được Reset! Đã xóa {deleted_count} documents."
            }

        except Exception as e:
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

    def _log_transaction(self, uid, action, amt, date, note):
        from models.transaction import Transaction
        self.transaction_repo.add_transaction(Transaction(uid, action, amt, date, note))