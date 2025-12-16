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
        

    def get_full_overview(self, user_id, view_date_str=None):
        """
        Tổng hợp dữ liệu Dashboard.
        [FIXED] Logic tính lãi ngày: Loại bỏ tài sản mới mua trong ngày khỏi tính toán lãi qua đêm.
        """
        # 1. Xác định ngày định giá (T) và ngày hôm trước (T-1)
        if view_date_str:
            try:
                target_date = datetime.strptime(view_date_str, "%Y-%m-%d").date()
            except ValueError:
                target_date = date.today()
        else:
            target_date = date.today()

        prev_date = target_date - timedelta(days=1)

        # 2. LẤY VÍ USER
        user_wallet = self.finsight_repo.get_user_account(user_id)
        
        total_asset_value = 0.0
        daily_profit_total = 0.0
        enriched_assets = []

        # 3. DUYỆT DANH MỤC
        for asset in user_wallet.assets:
            ma_cd = asset.get('maCD')
            so_luong = int(asset.get('soLuong', 0))
            
            # [NEW] Lấy ngày mua của tài sản để check logic
            # Giả sử DB lưu trường 'created_at' dạng string ISO hoặc date object
            buy_date_raw = asset.get('ngayMua') 
            asset_buy_date = None
            
            if buy_date_raw:
                if isinstance(buy_date_raw, str):
                    # Cắt chuỗi lấy YYYY-MM-DD nếu có giờ phút
                    try:
                        asset_buy_date = datetime.strptime(buy_date_raw[:10], "%Y-%m-%d").date()
                    except:
                        asset_buy_date = target_date # Fallback nếu lỗi date
                elif isinstance(buy_date_raw, (datetime, date)):
                    asset_buy_date = buy_date_raw if isinstance(buy_date_raw, date) else buy_date_raw.date()

            if so_luong <= 0: continue

            cd_info = self.cd_repo.get_cd_by_id(ma_cd)
            if not cd_info: continue
            
            # --- TÍNH GIÁ ---
            price_T = self._calculate_cd_price_dynamic(cd_info, target_date)
            price_Prev = self._calculate_cd_price_dynamic(cd_info, prev_date)
            
            gia_von = float(asset.get('giaVon', 0))
            if price_T == 0: price_T = gia_von
            if price_Prev == 0: price_Prev = gia_von

            current_value = price_T * so_luong
            total_asset_value += current_value

            # --- [LOGIC QUAN TRỌNG ĐÃ SỬA] ---
            # Chỉ tính lãi so với hôm qua NẾU tài sản đã tồn tại từ trước hôm nay.
            # Nếu mới mua hôm nay (Buy Date >= Target Date), lãi ngày = 0 (hoặc chênh lệch giá khớp lệnh vs giá thị trường - ở đây ta coi như bằng 0).
            
            item_daily_profit = 0.0
            
            if asset_buy_date and asset_buy_date >= target_date:
                # Trường hợp mới mua hôm nay -> Chưa có lãi qua đêm
                item_daily_profit = 0.0
            else:
                # Trường hợp đã giữ qua đêm -> Tính chênh lệch giá
                item_daily_profit = (price_T - price_Prev) * so_luong

            daily_profit_total += item_daily_profit
            
            asset_view = asset.copy()
            asset_view.update({
                'current_price': price_T,
                'current_value': current_value,
                'daily_profit': item_daily_profit
            })
            enriched_assets.append(asset_view)

        # 4. TỔNG HỢP (Giữ nguyên)
        total_net_worth = user_wallet.cash + total_asset_value
        
        user_data = user_wallet.to_dict()
        user_data['total_net_worth'] = total_net_worth
        user_data['total_asset_value'] = total_asset_value
        user_data['assets'] = enriched_assets

        system_fund = self.finsight_repo.get_system_account()
        bank_data = self.bank_repo.get_system_bank()
        pending_docs = self.finsight_repo.get_pending_logs()
        processed_inventory = self.get_available_inventory_with_price(view_date_str)
        print(processed_inventory)
        finsight_data = system_fund.to_dict()
        finsight_data['inventory'] = processed_inventory
        print(finsight_data)
        queue_list = [{
            "id": doc.get("id"),
            "type": doc.get("type"),
            "amount": doc.get("amount", 0),
            "created_at": doc.get("created_at"),
            "details": doc.get("details", {}) # Quan trọng: Cần lấy thêm details để hiển thị Asset Name ở Frontend
        } for doc in pending_docs]

        return {
            "user": user_data,
            "performance": {
                "profit_today": daily_profit_total,
                "last_updated": datetime.now().strftime("%H:%M:%S")
            },
            "finsight": finsight_data,
            "bank": bank_data.to_dict(),
            "queue": queue_list,
            "total_balance_estimate": total_net_worth,
            "meta": {
                "server_time": datetime.now().isoformat(),
                "valuation_date": target_date.isoformat(),
                "mode": "FIXED_INTRADAY_PNL" 
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
        self.finsight_repo.add_settlement_log(user_id, "CASH_IN", amount, date_str)
        
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
                user_id, "ALLOCATION_CASH_PAID", total_cost, date_str
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
                date_str,
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
            self.finsight_repo.add_settlement_log(user_id, "CASH_OUT", amount, date_str)
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
        self.finsight_repo.add_settlement_log(user_id, "LIQUIDATE_CD", cash_raised,date_str, {"sold": assets_to_sell})
        self.finsight_repo.add_settlement_log(user_id, "CASH_OUT", amount, date_str)
        
        self._log_transaction(user_id, "RUT", amount, date_str, f"Rút (Bán {len(assets_to_sell)} CD)")
        return {"status": "success", "message": "Rút tiền & Thanh khoản thành công"}
    # --- 5. LẤY KHO FINSIGHT KÈM GIÁ (Dùng cho UI "Tài sản Finsight") ---
    def get_available_inventory_with_price(self, view_date_str=None):
        """
        Lấy danh sách CD từ CD Repo, coi đó là kho hàng khả dụng,
        và tính giá trị thực tế tại ngày xem.
        """
        # 1. Parse ngày xem
        if view_date_str:
            try:
                target_date = datetime.strptime(view_date_str, "%Y-%m-%d").date()
            except ValueError:
                target_date = date.today()
        else:
            target_date = date.today()

        # 2. [THEO YÊU CẦU] Lấy trực tiếp từ CD Repo
        # Hàm này trả về list các dict chứa thongTinChung, thongTinLaiSuat...
        inventory_list = self.cd_repo.get_all_cd()
        
        results = []
        
        for cd in inventory_list:
            # --- TRÍCH XUẤT DỮ LIỆU TỪ CẤU TRÚC CD ---
            # Vì cấu trúc CD thường chia thành các nhóm thông tin, ta cần lấy đúng chỗ
            tt_chung = cd.get('thongTinChung', {})
            tt_nhap_kho = cd.get('thongTinNhapKho', {})
            
            # Ưu tiên lấy mã từ thongTinChung, nếu không có thì thử lấy trực tiếp
            ma_cd = tt_chung.get('maDoiChieu') or cd.get('maCD')
            # Lấy số lượng từ thongTinNhapKho
            try:
                so_luong = int(tt_chung.get('CDKhaDung', 0))
            except:
                so_luong = int(cd.get('CDKhaDung', 0))
            
            # Lấy giá vốn (đơn giá mua vào)
            try:
                gia_von = float(tt_chung.get('menhGia', 0))
            except:
                gia_von = float(cd.get('menhGia', 0))

            # Skip nếu hết hàng hoặc dữ liệu lỗi
            if not ma_cd or so_luong <= 0: 
                continue
            
            # 3. Tận dụng hàm tính giá CÓ SẴN (truyền nguyên cục cd vào)
            price_at_date = self._calculate_cd_price_dynamic(cd, target_date)
            
            # Fallback: Nếu tính ra 0 (vd chưa đến ngày phát hành), dùng giá vốn
            if price_at_date == 0:
                price_at_date = gia_von
            results.append({
                "maCD": ma_cd,
                "soLuong": so_luong,
                "giaTaiNgayXem": price_at_date,
                "khuVuc": "Kho CD (System)" 
            })
            
        return results
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
        logs = self.finsight_repo.get_pending_logs()
        processed_ids = []
        
        # [1] Cash Flow Accumulators (Cộng dồn tiền)
        user_net_cash_flow = 0.0
        finsight_net_cash_flow = 0.0 

        # [2] Asset Changes Map: { 'Mã_CD': Số_lượng_thay_đổi }
        # Ví dụ: {'CD001': 100, 'CD002': -50} (Dương là thêm, Âm là bớt)
        asset_changes_map = {} 

        for doc in logs:
            log = doc.to_dict()
            l_type = log.get('type')
            amt = float(log.get('amount', 0))
            
            # --- A. CASH FLOW LOGIC (Giữ nguyên logic đúng của bạn) ---
            if l_type == 'CASH_IN':
                user_net_cash_flow += amt

            elif l_type == 'CASH_OUT':
                user_net_cash_flow -= amt

            elif l_type == 'ALLOCATION_CASH_PAID':
                user_net_cash_flow -= amt
                finsight_net_cash_flow += amt 
            
            elif l_type == 'LIQUIDATE_CD':
                user_net_cash_flow += amt
                finsight_net_cash_flow -= amt

                # --- [NEW] ASSET LOGIC: BÁN (TRỪ) ---
                # Thay vì append vào list remove, ta trừ thẳng vào Map tổng
                sold_items = log.get('details', {}).get('sold', [])
                for item in sold_items:
                    ma_cd = item.get('maCD')
                    qty = int(item.get('soLuong', 0))
                    # Cộng dồn số âm (Giảm đi)
                    asset_changes_map[ma_cd] = asset_changes_map.get(ma_cd, 0) - qty

            # --- [NEW] ASSET LOGIC: MUA/NHẬN (CỘNG) ---
            elif l_type == 'ALLOCATION_ASSET_DELIVERED':
                assets_delivered = log.get('details', {}).get('assets', [])
                for asset in assets_delivered:
                    ma_cd = asset.get('maCD')
                    qty = int(asset.get('soLuong', 0))
                    # Cộng dồn số dương (Thêm vào)
                    asset_changes_map[ma_cd] = asset_changes_map.get(ma_cd, 0) + qty
            
            processed_ids.append(doc.id)

        if not processed_ids: 
            return {"status": "warning", "message": "Không có gì để Sync"}
        
        # --- THỰC HIỆN GHI VÀO DB (BANK REPO) ---

        # 1. Update Cash (Batch Update)
        if user_net_cash_flow != 0:
            self.bank_repo.update_user_cash(user_net_cash_flow)
        
        if finsight_net_cash_flow != 0:
            self.bank_repo.update_system_cash(finsight_net_cash_flow)

        # 2. [OPTIMIZED] Update Assets Ownership
        # Truyền map thay đổi xuống repo để xử lý logic cộng trừ chuẩn xác
        if asset_changes_map:
            # Bạn cần thêm hàm sync_assets_net_changes vào BankRepo (xem code bên dưới)
            self.bank_repo.sync_assets_net_changes(asset_changes_map) 

        # 3. Đánh dấu đã xử lý
        self.finsight_repo.mark_logs_processed(processed_ids)
        
        return {
            "status": "success", 
            "message": (f"Đã Sync NHLK.\n"
                        f"- User Cash: {user_net_cash_flow:+,.0f}\n"
                        f"- Finsight Cash: {finsight_net_cash_flow:+,.0f}\n"
                        f"- Assets Updated: {len(asset_changes_map)} mã")
        }
    # ... Helper Functions cũ (tính giá, log trans...) giữ nguyên ...
    def _calculate_cd_price_dynamic(self, cd, view_date):
        try:
            # 1. Parse dữ liệu đầu vào
            c1 = cd.get("thongTinChung", {})
            c2 = cd.get("thongTinLaiSuat", {})
            
            # Xử lý mệnh giá (bỏ dấu chấm phân cách ngàn, thay phẩy decimal thành chấm)
            menh_gia_str = str(c1.get("menhGia", 0)).replace('.', '').replace(',', '.')
            menh_gia = float(menh_gia_str)

            def parse_d(d_str):
                try: return datetime.strptime(d_str, "%Y-%m-%d").date()
                except: return None

            ngay_ph = parse_d(c1.get("ngayPhatHanh"))
            ngay_dh = parse_d(c1.get("ngayDaoHan"))
            
            # Xử lý lãi suất (ví dụ 8,5 -> 8.5)
            lai_suat_str = str(c2.get("laiSuat", 0)).replace(',', '.')
            lai_suat_cd = float(lai_suat_str) / 100.0
            
            r_user = USER_INTEREST_RATE / 100.0
            tan_suat = c2.get("tanSuatTraLai", "Cuối kỳ")

            # Validation
            if not ngay_ph or not ngay_dh: return 0.0
            if view_date < ngay_ph: return 0.0  # Chưa phát hành thì giá = 0 (hoặc = giá vốn tuỳ logic)

            # -----------------------------------------------------------
            # [LOGIC MỚI] TÍNH GIÁ THEO KỲ (RESET SAU MỖI LẦN TRẢ LÃI)
            # -----------------------------------------------------------

            # 1. Tìm ngày trả lãi gần nhất trước đó (Last Coupon Date)
            last_coupon = self._get_last_coupon_date(ngay_ph, ngay_dh, tan_suat, view_date)

            # 2. Tính giá gốc (Base Price) tại đầu kỳ này
            # Để tính Base, ta cần Next Coupon của cái Last Coupon đó
            next_coupon_for_base = self._get_next_coupon_date(ngay_ph, ngay_dh, tan_suat, last_coupon)
            
            price_base = self._calculate_yield_formula(
                menh_gia, lai_suat_cd, r_user, 
                next_coupon_for_base, last_coupon, # curr_date ở đây là đầu kỳ (last_coupon)
                ngay_ph, ngay_dh, tan_suat
            )

            # 3. Tính số ngày nắm giữ trong kỳ này
            days_passed = (view_date - last_coupon).days
            
            # 4. Công thức cộng dồn lãi (Custom Price)
            # Giá = Giá Gốc + (Giá Gốc * R_User * Số ngày / 365)
            final_price = price_base + (price_base * r_user * days_passed) / 365.0

            return round(final_price, 2)

        except Exception as e:
            print(f"Error calc price: {e}")
            return 0.0

    def _calculate_yield_formula(self, M, r_CD, r_User, next_date, curr_date, issue_date, maturity_date, freq_str):
        # 1. Xử lý trường hợp Đáo hạn
        if curr_date >= maturity_date:
            # Nếu trả cuối kỳ: Nhận Gốc + Lãi toàn bộ thời gian
            if "cuối kỳ" in (freq_str or "").lower():
                total_days = (maturity_date - issue_date).days
                return M + (M * r_CD * total_days / 365.0)
            else:
                # Nếu trả định kỳ: Nhận Gốc + Lãi của kỳ cuối cùng
                last_date = self._get_last_coupon_date(issue_date, maturity_date, freq_str, maturity_date - timedelta(days=1))
                days_in_period = (maturity_date - last_date).days
                return M + (M * r_CD * days_in_period / 365.0)

        # 2. Tính dòng tiền tương lai (Future Value - Tử số)
        future_value = 0.0
        
        if "cuối kỳ" in (freq_str or "").lower():
            # Cuối kỳ: FV = Gốc + Tổng lãi tích luỹ
            total_days = (maturity_date - issue_date).days
            total_interest = M * r_CD * (total_days / 365.0)
            future_value = M + total_interest
        else:
            # Định kỳ: FV = Gốc + Coupon của kỳ này
            # Cần tính xem kỳ này dài bao nhiêu ngày
            # Note: next_date ở đây chính là ngày trả lãi sắp tới
            last_date = self._get_last_coupon_date(issue_date, maturity_date, freq_str, curr_date)
            days_in_period = (next_date - last_date).days
            coupon_payment = M * r_CD * (days_in_period / 365.0)
            
            future_value = M + coupon_payment

        # 3. Chiết khấu về hiện tại (Mẫu số)
        days_to_discount = (next_date - curr_date).days
        if days_to_discount < 0: days_to_discount = 0
        
        denominator = 1 + (r_User * days_to_discount) / 365.0
        
        return future_value / denominator

    # --- HELPER: TÌM NGÀY TRẢ LÃI KẾ TIẾP ( > CURR ) ---
    def _get_next_coupon_date(self, start, end, freq, curr):
        s = (freq or "").lower()
        if "cuối kỳ" in s: return end
        
        months = 12
        if "3 tháng" in s or "theo quý" in s: months = 3
        elif "6 tháng" in s or "bán niên" in s: months = 6
        elif "1 tháng" in s or "hàng tháng" in s: months = 1
        elif "hàng năm" in s or "1 năm" in s: months = 12
        
        d = start
        limit = 0
        while d <= curr and limit < 500:
            d = d + relativedelta(months=months)
            if d > end: return end
            limit += 1
        return d

    # --- HELPER MỚI: TÌM NGÀY TRẢ LÃI GẦN NHẤT ( <= CURR ) ---
    def _get_last_coupon_date(self, start, end, freq, curr):
        s = (freq or "").lower()
        # Nếu trả cuối kỳ, ngày bắt đầu tính lãi luôn là ngày phát hành
        if "cuối kỳ" in s: return start
        
        months = 12
        if "3 tháng" in s or "theo quý" in s: months = 3
        elif "6 tháng" in s or "bán niên" in s: months = 6
        elif "1 tháng" in s or "hàng tháng" in s: months = 1
        elif "hàng năm" in s or "1 năm" in s: months = 12
        
        d = start
        prev = start
        limit = 0
        
        while d <= curr and limit < 500:
            prev = d # Lưu lại ngày trước khi cộng
            d = d + relativedelta(months=months)
            
            # Nếu cộng xong vượt quá ngày đáo hạn
            if end and d > end:
                break
            limit += 1
            
        return prev

    def _log_transaction(self, uid, action, amt, date, note):
        from models.transaction import Transaction
        self.transaction_repo.add_transaction(Transaction(uid, action, amt, date, note))