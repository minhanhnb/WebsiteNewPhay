from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from config import USER_INTEREST_RATE
from firebase_admin import firestore
import math 
from models.T2.transaction import Transaction2


class SystemService2:
    def __init__(self, drawer_repo, finsight_repo, transaction_repo, cd_repo, bank_repo):
        self.drawer_repo = drawer_repo
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
        # 2. LẤY VÍ USER
        user_wallet = self.drawer_repo.get_user_account(user_id)
        user_data = user_wallet.to_dict()
        
        daily_profit_total = 0.0
        

        # 4. TỔNG HỢP (Giữ nguyên)
        total_net_worth = self.calculate_user_CD(user_id, target_date.isoformat())

        db_profit_date = user_data.get('last_profit_date')
        if db_profit_date != target_date:
            user_data['profit_today'] = 0.0
        
        # User Data giờ đã có thêm accumulated_profit từ to_dict() của Drawer
        user_data['cash'] = round(user_data.get('cash', 0), 2)
        user_data['cash'] = round(user_data.get('cash', 0), 2)

        user_fund = self.finsight_repo.get_user_account(user_id)
        system_fund = self.finsight_repo.get_system_account()
        bank_data = self.bank_repo.get_system_bank()
        pending_docs = self.finsight_repo.get_pending_logs()
        processed_inventory = self.get_available_inventory_with_price(view_date_str)

        finsight_data = system_fund.to_dict()
        finsight_data['user'] = user_fund.to_dict()
        finsight_data['inventory'] = processed_inventory
        print(finsight_data)
        queue_list =[]
        for doc in pending_docs: 
            data = doc.to_dict() if hasattr(doc, 'to_dict') else doc
            item = {
            "id": data.get("id") if data.get("id") else getattr(doc, 'id', None),
            "type": data.get("type") if data.get("type") else getattr(doc, 'type', None),
            "amount": data.get("amount") if data.get("amount") else getattr(doc, 'amount', None),
            "created_at": data.get("created_at") if data.get("created_at") else getattr(doc, 'created_at', None),
            "details": data.get("details") if data.get("details") else getattr(doc, 'details', None),
        } 
            queue_list.append(item)


        raw_transactions = self.transaction_repo.get_transactions_by_user(user_id)
    
        # 3. Format lại history để Frontend dễ dùng (Clean Data)
        history_data = []
        for doc in raw_transactions:
            # Sử dụng logic lấy ID an toàn chúng ta đã bàn
            data = doc.to_dict() if hasattr(doc, 'to_dict') else doc
            history_data.append({
                "id": doc.id if hasattr(doc, 'id') else data.get('id'),
                "date_trans": data.get("date_trans"),
                "action_type": data.get("action_type") or data.get("action"),
                "amount": data.get("amount", 0),
                "status": data.get("status")
            })

        return {
            "user": user_data,
            "history": history_data, 
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

    # --- 2. NẠP TIỀN VÀO NGĂN TỦ---
    def process_deposit(self, user_id, amount, date_str):
        # 1. User: Tăng Cash Remainder
        self.drawer_repo.update_user_cash(user_id, amount)

        # 2. Log lịch sử giao dịch
        self._log_transaction(user_id, "NAP", amount, date_str, "Nạp vào Ngăn tủ")
        
        return {"status": "success", "message": "Nạp tiền thành công (Đã vào Cash Remainder)"}



   

    # =========================================================================
    # [MODULE] SYNC ENGINE - ĐỒNG BỘ VỚI DRAWER (LOGIC RIÊNG BIỆT)
    # =========================================================================

    def sync_wallet_state_with_drawer(self, user_id, date_str=None):
        if not date_str: date_str = date.today().isoformat()
        
        print(date_str)
        # 1. Lấy dữ liệu cơ sở
        drawer_account = self.drawer_repo.get_user_account(user_id) 
        drawer_cash = drawer_account.cash
        print("Cash ngăn tủ", drawer_cash)

        current_net_worth = self.calculate_user_net_worth(user_id, date_str)
        diff =drawer_cash - current_net_worth
        print("net worth finsight", current_net_worth)
        
        result = {"diff": diff, "actions": []}
        print("Chênh lệch", diff)

        try:
            # CASE 1: USER NẠP TIỀN (Drawer tăng nhanh hơn Finsight)
            if diff > 0:
                self._sync_inject_funds(user_id, diff, date_str)
                result["case"] = "USER_DEPOSIT"
                result["actions"].append(f"Injected & Allocated: {diff}")
                return {**result, "status": "success"}

            # XỬ LÝ KHI DIFF < 0 (Drawer thấp hơn hoặc Finsight tăng nhanh hơn do lãi)
            elif diff < 0:
                amount_abs = abs(diff)
                print("Chạy được vào diff < 0")
                # Kiểm tra lịch sử giao dịch rút tiền trong ngày (Query Repo)
                # Giả sử repo có hàm trả về list hoặc count giao dịch rút
                has_withdrawal = self.transaction_repo.has_action_in_day(user_id, "RUT", date_str)
                print("Đã chạy và has withdrawal")
                print(has_withdrawal)

                if not has_withdrawal:
                    # CASE 2: PHÁT SINH LÃI (Networth tăng do CD tăng giá, Drawer chưa cập nhật)
                    # Chúng ta bơm lãi ngược lại cho Tủ để khớp Networth
                    self.drawer_repo.update_user_cash(user_id, amount_abs)

                    self._log_transaction(user_id, "TIENLAI", amount_abs, date_str, f"Tiền lãi ")
                    #self.drawer_repo.update_profit_today(user_id, amount_abs)
                    self.drawer_repo.record_profit(user_id, amount_abs, date_str)
                    print("đang trong not has")
                    result["case"] = "DAILY_PROFIT_SYNC"
                    result["actions"].append(f"Payout Interest to Drawer: {amount_abs}")
                    return {**result, "status": "success"}
                
                else:
                    # CASE 3: USER RÚT TIỀN (Drawer đã giảm tiền, Finsight cần giảm theo)
                    print("Case 3: User rút tiền")
                    self._sync_drain_funds(user_id, amount_abs, date_str)
                    
                    result["case"] = "USER_WITHDRAWAL"
                    result["actions"].append(f"Drained Finsight Assets: {amount_abs}")
                    return {**result, "status": "success"}

            else:
                result["case"] = "NO_CHANGE"
                result["actions"].append("No action needed.")
                return {**result, "status": "success"}

        except Exception as e:
            return {"status": "error", "message": str(e)}

    # HÀM 1: INJECT (NẠP ĐỒNG BỘ + TỰ ĐỘNG MUA)
 
    def _sync_inject_funds(self, user_id, amount, date_str):
        """
        Bơm tiền vào Cash và lập tức gọi phân bổ mua CD.
        Log Type: SYNC_IN
        """
        try :
            print("Đang bơm cash")
            # 1. Bơm Cash
            self.finsight_repo.update_user_cash(user_id, amount)
            self.finsight_repo.add_settlement_log(user_id, "CASH_IN", amount, date_str)
            
            return self._sync_auto_allocate(user_id, date_str)
        except Exception as e:
            print(f"Error in _sync_inject_funds: {e}")
            raise e
        
    
    def _sync_auto_allocate(self, user_id, date_str):
        """
        Logic phân bổ dành riêng cho Sync. 
        Khác hàm gốc ở chỗ: Không return message dài dòng, ưu tiên mua hết tiền.
        """
        try : 
            print("Đang phân bổ")
            allocation_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            user_acc = self.finsight_repo.get_user_account(user_id)
            available_cash = user_acc.cash

            if available_cash <= 1000: 
                return {"status": "warning", "message": "Cash Remainder dưới 1,000 VND."}

            # Lấy danh sách CD (Logic chọn hàng vẫn giống cũ)
            available_cds = self.cd_repo.get_sellable_cds()
            processed_cds = []
            for cd in available_cds:
                p = self._calculate_cd_price_dynamic(cd, allocation_date)
                if p > 0:
                    cd['current_price'] = p
                    processed_cds.append(cd)
            processed_cds.sort(key=lambda x: x['current_price'], reverse=True)

            shopping_cart = []
            asset_map = {asset['maCD']: asset for asset in user_acc.assets}
            total_cost = 0
            db_record_list = []
            remaining_cash = available_cash
            print("Tiền còn lại", remaining_cash)
            for cd in processed_cds:
                if remaining_cash <= 0: break
                price = cd['current_price']
                stock = cd['real_stock']
                cd_id = cd['thongTinChung']['maDoiChieu']
                
                qty = min(int(remaining_cash // price), stock)
                if qty > 0:
                    cost = qty * price
                    shopping_cart.append({"maCD": cd_id, "soLuong": qty})
                    
                    new_asset_record = {
                        "maCD": cd_id, "soLuong": qty, 
                        "giaVon": price, "ngayMua": date_str
                    }
                    db_record_list.append(new_asset_record)
                    
                    if cd_id in asset_map:
                        existing = asset_map[cd_id]
                        existing['soLuong'] = int(existing['soLuong']) + qty
                    else:
                        asset_map[cd_id] = new_asset_record
                    
                    remaining_cash -= cost
                    total_cost += cost

            if total_cost > 0:
                updated_assets = list(asset_map.values())
                print("Chạy được vào execute DB")
                # Execute DB Updates
                self.finsight_repo.update_user_cash(user_id, -total_cost)
                self.finsight_repo.update_system_cash(total_cost)
                self.finsight_repo.update_user_assets(user_id, updated_assets)
                
                for item in shopping_cart:
                    self.cd_repo.decrease_stock(item['maCD'], item['soLuong'])

                # Log riêng cho Sync
                self.finsight_repo.add_settlement_log(
                    user_id, "ALLOCATION_ASSET_DELIVERED", total_cost, date_str, {"assets": db_record_list}
                )
                return {
                    "status": "success",
                    "message": f"Đã mua {len(shopping_cart)} mã CD, tổng chi {total_cost:,.0f}"
                }
            
            return {"status": "warning", "message": "Không có CD phù hợp để mua hoặc hết tiền mặt."}
        except Exception as e:
            print(f"Error in _sync_auto_allocate: {e}")
            return {"status": "error", "message": str(e)}
    # HÀM 2: DRAIN (RÚT ĐỒNG BỘ + TỰ ĐỘNG BÁN)

    def _sync_drain_funds(self, user_id, amount, date_str):
        try : 
            """
            Rút tiền để khớp với Drawer.
            Logic: Trừ Cash -> Thiếu thì bán CD.
            Log Type: SYNC_CASH_OUT / SYNC_LIQUIDATE
            """
            print("Đang rút tiền")
            trans_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            user_acc = self.finsight_repo.get_user_account(user_id)
            current_cash = user_acc.cash
            
            # 1. Nếu đủ Cash -> Trừ Cash luôn
            if current_cash >= amount:
                self.finsight_repo.update_user_cash(user_id, -amount)
                self.finsight_repo.add_settlement_log(user_id, "SYNC_CASH_OUT", amount, date_str)
                return

            # 2. Nếu thiếu Cash -> Phải bán CD
            shortage = amount - current_cash
            
            # [Strategy: Ưu tiên bán CD nào?]
            # Ở đây tôi giữ logic cũ: Duyệt qua list assets.
            # Nếu muốn tối ưu (ví dụ bán cái lãi thấp nhất trước), hãy sort user_acc.assets ở đây.
            
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
                shortage -= revenue # Giảm lượng tiền còn thiếu
                
                assets_to_sell.append({"maCD": ma_cd, "soLuong": qty})
                
                if so_luong - qty > 0:
                    new_as = asset.copy()
                    new_as['soLuong'] = so_luong - qty
                    remaining_assets.append(new_as)
            
            # Thực hiện update DB
            # Net change của Cash = (Tiền bán được) - (Tiền cần rút)
            # Vd: Cần rút 100. Cash có 20. Thiếu 80. Bán CD được 85.
            # Cash mới = 20 + 85 - 100 = 5.
            net_cash_change = cash_raised - amount

            for item in assets_to_sell:
                self.cd_repo.increase_stock(item['maCD'], item['soLuong'])

            self.finsight_repo.update_user_assets(user_id, remaining_assets)
            self.finsight_repo.update_user_cash(user_id, net_cash_change)
            self.finsight_repo.update_system_cash(-cash_raised) # Hệ thống bỏ tiền ra mua lại

            # Log Sync
            if assets_to_sell:
                self.finsight_repo.add_settlement_log(
                    user_id, "LIQUIDATE_CD", cash_raised, date_str, {"sold": assets_to_sell}
                )
            
            # Vẫn log Cash Out dòng tiền tổng
            self.finsight_repo.add_settlement_log(user_id, "CASH_OUT", amount, date_str)
            return {"status": "success", "message": "Rút tiền & Thanh khoản thành công"}
        except Exception as e:
            return {"status": "error", "message": str(e)}


    # --- 4. RÚT TIỀN (Trừ Cash -> Thiếu thì Bán CD cho FS) ---
    def process_withdrawal(self, user_id, amount, date_str):
        amount = float(amount)
        user_acc = self.drawer_repo.get_user_account(user_id)
        current_cash = user_acc.cash
        print("Đang vào hệ thống 2 để rút tiền")
        # A. Đủ Cash
        if current_cash >= amount:
            self.drawer_repo.update_user_cash(user_id, -amount)
            self._log_transaction(user_id, "RUT", amount, date_str, "Rút")
            return {"status": "success", "message": "Rút tiền thành công"}

        
        self.drawer_repo.update_user_cash(user_id, amount)
        self._log_transaction(user_id, "RUT", amount, date_str, f"Rút ")
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
            print("Mã CD finsight là", ma_cd)
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
            print("giá", price_at_date)
            results.append({
                "maCD": ma_cd,
                "soLuong": so_luong,
                "giaTaiNgayXem": price_at_date,
                "khuVuc": "Kho CD (System)" 
            })
            print(results)
            
        return results
    def reset_database(self):
        print("Đang xóa")
        """
        DANGER: Xóa toàn bộ dữ liệu trong các Collection của hệ thống.
        Dùng cho mục đích Reset Test Case.
        """
        db = firestore.client()
        
        # Danh sách các collection cần xóa
        target_collections = [
            'finsight2_users',       # Ví User
            'finsight2_system',      # Quỹ hệ thống
            'bank2',                 # NHLK
            'transactions2',         # Lịch sử giao dịch
            'settlement2_queue',     # Log chờ Sync
            'drawer',
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
        print("Đang vào sync bank")
        logs = self.finsight_repo.get_pending_logs()
        processed_ids = []
        
        # [1] Cash Flow Accumulators (Cộng dồn tiền)
        user_net_cash_flow = 0.0
        finsight_net_cash_flow = 0.0 

        # [2] Asset Changes Map: { 'Mã_CD': Số_lượng_thay_đổi }
        # Ví dụ: {'CD001': 100, 'CD002': -50} (Dương là thêm, Âm là bớt)
        asset_changes_map = {} 

        for doc in logs:
            log = doc.to_dict() if hasattr(doc, 'to_dict') else doc
            l_type = log.get('type')
            amt = float(log.get('amount', 0))
            print("vào được vòng lặp")
            # --- A. CASH FLOW LOGIC (Giữ nguyên logic đúng của bạn) ---
            if l_type == 'CASH_IN':
                user_net_cash_flow += amt

            elif l_type == 'CASH_OUT':
                user_net_cash_flow -= amt

            
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

                user_net_cash_flow -= amt
                finsight_net_cash_flow += amt 
                
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
        self.transaction_repo.add_transaction(Transaction2(uid, action, amt, date, note))

    def calculate_user_CD(self, user_id, view_date_str=None):
        # 1. Parse ngày xem
        if view_date_str:
            try:
                target_date = datetime.strptime(view_date_str, "%Y-%m-%d").date()
            except ValueError:
                target_date = date.today()
        else:
            target_date = date.today()
        # 2. Lấy User Account
        user_acc = self.finsight_repo.get_user_account(user_id)
        total_net_worth = 0 
        for asset in user_acc.assets:
            ma_cd = asset.get('maCD')
            so_luong = int(asset.get('soLuong', 0))
            cd_info = self.cd_repo.get_cd_by_id(ma_cd)
            price = self._calculate_cd_price_dynamic(cd_info, target_date)
            total_net_worth += so_luong * price
        return round(total_net_worth, 2)
    