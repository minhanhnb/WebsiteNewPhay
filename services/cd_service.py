from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from flask import jsonify
from repository.cd_repo import CDRepository
from models.CD import CD
from firebase_config import db

class CDService:
    def __init__(self, repository: CDRepository):
        self.repo = repository

    def add_cd(self, payload: dict):
        print("da vao duoc service  hehehe ")

        # ---- Khởi tạo Model ----
        print(payload)
        cd = CD(
            thongTinChung=payload.get("thongTinChung", {}),
            thongTinLaiSuat=payload.get("thongTinLaiSuat", {}),
            thongTinNhapKho=payload.get("thongTinNhapKho", {}),
        )
        maCD = cd.thongTinChung.get("maDoiChieu")


        # ---- Gọi Repository ----
        return self.repo.add_cd(cd)

    def get_all_cd(self):
            print("Service: get_all_cd")
            return self.repo.get_all_cd()

    def get_cd_by_id(self, maDoiChieu):
        cd = self.repo.get_cd_by_id(maDoiChieu)
        if not cd:
            return jsonify({"message": "Không tìm thấy CD"}), 404
        return jsonify(cd), 200

    def calculate_daily_price_batch(self):
        print("=== BẮT ĐẦU JOB TÍNH GIÁ CD ===")
        all_cds = self.repo.get_all_cd()
        today = date.today()
        updated_count = 0
        error_count = 0

        for cd_data in all_cds:
            try:
                # 1. Trích xuất dữ liệu thô
                c1 = cd_data.get("thongTinChung", {})
                c2 = cd_data.get("thongTinLaiSuat", {})
                
                ma_doi_chieu = c1.get("maDoiChieu")
                if not ma_doi_chieu: continue

                # 2. Parse dữ liệu (Helper function ở dưới)
                menh_gia = self._parse_money(c1.get("menhGia"))
                ngay_ph = self._parse_date(c1.get("ngayPhatHanh"))
                ngay_dh = self._parse_date(c1.get("ngayDaoHan"))
                
                # Lãi suất CD (Coupon Rate)
                lai_suat_cd = self._parse_money(c2.get("laiSuat")) / 100
                tan_suat_str = c2.get("tanSuatTraLai", "Cuối kỳ")

                if not menh_gia or not ngay_ph or not ngay_dh:
                    print(f"Skipping {ma_doi_chieu}: Thiếu dữ liệu quan trọng")
                    error_count += 1
                    continue

                # 3. LOGIC TÍNH GIÁ (Porting từ JS)
                # Lãi suất dùng cho công thức Custom (Accumulation)
                # Ở Frontend là User Input. Ở Backend ta dùng chính lãi suất CD hoặc 1 cấu hình chung.
                # Hiện tại tôi dùng lãi suất CD.
                lai_suat_tinh_toan = lai_suat_cd 

                # Bước A: Tính Giá Yield Ngày Đầu (Base Price Day 0)
                # Tìm ngày trả lãi đầu tiên tính từ ngày phát hành
                first_next_coupon = self._get_next_coupon_date(ngay_ph, ngay_dh, tan_suat_str, ngay_ph)
                
                price_base_day_0 = self._calculate_yield_formula(
                    M=menh_gia,
                    r_CD=lai_suat_cd,
                    r_User=lai_suat_tinh_toan, # Dùng lãi suất này để chiết khấu mẫu số
                    next_date=first_next_coupon,
                    curr_date=ngay_ph,
                    issue_date=ngay_ph,
                    maturity_date=ngay_dh,
                    freq_str=tan_suat_str
                )

                # Bước B: Tính Giá Custom Hôm Nay (Linear Accumulation)
                # Công thức: Price = Base + (Base * Rate * DaysPassed / 365)
                days_passed = (today - ngay_ph).days
                
                # Nếu chưa phát hành thì giá bằng mệnh giá hoặc 0
                if days_passed < 0:
                    gia_ban_hom_nay = menh_gia
                else:
                    gia_ban_hom_nay = price_base_day_0 + (price_base_day_0 * lai_suat_tinh_toan * days_passed) / 365

                # Làm tròn
                gia_ban_hom_nay = round(gia_ban_hom_nay, 2)

                # 4. Update vào DB
                self.repo.update_cd_price(ma_doi_chieu, gia_ban_hom_nay, today.isoformat())
                updated_count += 1

            except Exception as e:
                print(f"Lỗi tính giá CD {cd_data.get('thongTinChung', {}).get('maDoiChieu')}: {str(e)}")
                error_count += 1

        return {
            "message": f"Đã đồng bộ giá cho {updated_count} CD. Lỗi: {error_count}",
            "updated": updated_count
        }

    # ================= HELPER FUNCTIONS (Logic Math) =================

    def _calculate_yield_formula(self, M, r_CD, r_User, next_date, curr_date, issue_date, maturity_date, freq_str):
        """
        Tính giá Yield (Chiết khấu dòng tiền).
        Logic y hệt JS: Tử số (Future Value) / Mẫu số (Discount)
        """
        if curr_date >= maturity_date:
            # Đáo hạn: Trả Gốc + Lãi tích lũy toàn bộ
            total_days_cd = (maturity_date - issue_date).days
            total_interest = M * r_CD * (total_days_cd / 365)
            return M + total_interest

        # 1. TÍNH TỬ SỐ (Giá Đáo Hạn / Future Value của kỳ này)
        # Giả định đơn giản hóa giống JS: Case Cuối kỳ là chủ yếu
        s = (freq_str or "").lower()
        
        # Mặc định tính theo kiểu Cuối kỳ (Gốc + Lãi toàn bộ)
        # Nếu là định kỳ, logic này cần chỉnh sửa phức tạp hơn (DCF), 
        # nhưng để khớp với công thức JS hiện tại, ta giữ logic accumulated interest.
        total_days_cd = (maturity_date - issue_date).days
        total_interest = M * r_CD * (total_days_cd / 365)
        future_value = M + total_interest

        # 2. TÍNH MẪU SỐ
        days_to_discount = (next_date - curr_date).days
        if days_to_discount < 0: days_to_discount = 0
        
        denominator = 1 + (r_User * days_to_discount) / 365
        
        return future_value / denominator

    def _get_next_coupon_date(self, start_date, end_date, freq_str, current_date):
        """
        Tìm ngày trả lãi tiếp theo.
        Port từ hàm JS getNextCouponDate
        """
        s = (freq_str or "").lower()
        
        if "cuối kỳ" in s:
            return end_date

        months_to_add = 12
        if "3 tháng" in s or "theo quý" in s: months_to_add = 3
        elif "6 tháng" in s or "bán niên" in s: months_to_add = 6
        elif "1 tháng" in s: months_to_add = 1
        elif "12 tháng" in s or "hàng năm" in s: months_to_add = 12

        d = start_date
        limit = 0
        while d <= current_date and limit < 500:
            # Cộng tháng
            d = d + relativedelta(months=months_to_add)
            
            # Logic "cuối tháng" (EOM) được relativedelta xử lý tự động tốt hơn JS
            # Ví dụ: 31/1 + 1 tháng -> 28/2 hoặc 29/2
            
            if d > end_date:
                return end_date
            limit += 1
        
        return d

    def _parse_money(self, val):
        """Chuyển string '100.000,00' hoặc '100,000' sang float chuẩn"""
        if isinstance(val, (int, float)):
            return float(val)
        if not val:
            return 0.0
        
        s = str(val)
        # Xử lý logic tiền Việt: 100.000.000 (xóa chấm)
        if s.count('.') > 1: 
            s = s.replace('.', '') # Xóa phân cách ngàn
            s = s.replace(',', '.') # Thay phẩy thập phân bằng chấm
        elif ',' in s and '.' in s:
            # Case: 100.000,00 -> xóa chấm, thay phẩy
            s = s.replace('.', '').replace(',', '.')
        elif ',' in s:
            # Case: 8,5 (Lãi suất) hoặc 100,000 (Tiền Mỹ) -> Ưu tiên lãi suất VN 8,5
            s = s.replace(',', '.')
        
        try:
            return float(s)
        except:
            return 0.0

    def _parse_date(self, val):
        """Chuyển 'YYYY-MM-DD' hoặc 'DD/MM/YYYY' sang date object"""
        if isinstance(val, (datetime, date)):
            return val if isinstance(val, date) else val.date()
        
        if not val: return None
        
        # Thử các format phổ biến
        formats = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"]
        for fmt in formats:
            try:
                return datetime.strptime(val, fmt).date()
            except ValueError:
                continue
        return None
# def sync_today_service():
#     cds = CD.get_all_CD()
#     today = date.today()
#     updated_count = 0

#     for cd in cds:
#         try:
           

#             giaSoCap = float(cd.get("giaSoCap", 0))
#             laiSuat = float(cd.get("laiSuat", 0))
#             ngayDaoHan = cd.get("ngayDaoHan")
#             if isinstance(ngayDaoHan, str):
#                 ngayDaoHan = datetime.strptime(ngayDaoHan, "%Y-%m-%d").date()
#             giaTriDaoHan = cd.get("giaTriDaoHan") 
#             ngayPhatHanh = cd.get("ngayPhatHanh")
#             if isinstance(ngayPhatHanh, str):
#                 ngayPhatHanh = datetime.strptime(ngayPhatHanh, "%Y-%m-%d").date()

           
#                 # Market value lãi suất kho
#             marketValueLSKho = giaTriDaoHan / (1 + laiSuat / 100) ** ((ngayDaoHan - date.today()).days / 365) if laiSuat else giaSoCap

#             # Market value TKO
#             marketValueTKO = giaSoCap + giaSoCap * laiSuat / 100 * (date.today() - ngayPhatHanh).days / 365 if laiSuat else giaSoCap
#             soNgayConLai = (ngayDaoHan - today).days

#             # Gọi model để update
#             CD.update_CD(cd["maCD"], {
               
#                 "marketValueLSKho": round(marketValueLSKho, 2),
#                 "marketValueTKO": round(marketValueTKO, 2),
#                 "soNgayConLai": soNgayConLai,
#                 "ngayCapNhat": today.isoformat()
#             })
#             updated_count += 1

#         except Exception as e:
#             print(f"❌ Error updating CD {cd.get('maCD')}: {e}")

#     return f"✅ Sync thành công {updated_count} CD."

# def buy_CD(maCD, soLuong): 
#     result = CD.buy_CD(maCD, soLuong)
#     return result


# def get_today_market_valueTKO(maCD):
#     today_str = datetime.today().strftime("%Y-%m-%d")  # dạng "2025-08-07"

#     cd_price = CD.get_today_market_valueTKO(maCD)

#     if cd_price is not None:
#         return float(cd_price)
#     else:
#         raise ValueError(f"Không tìm thấy giá marketValueTKO cho CD {maCD} vào ngày {today_str}")


# def get_cd_info(maCD): 
#     result = CD.get_CD_info(maCD)
#     return result

# def increase_CD_Stock(maCD, soLuong):
#     return CD.update_CD_stock_model(maCD, soLuong, is_increase=True)
