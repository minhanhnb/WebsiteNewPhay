from repository.config_repo import ConfigRepository
from functools import lru_cache
from datetime import date, datetime, timedelta

class ConfigService:
    def __init__(self, repo: ConfigRepository):
        self.repo = repo
        self._cached_rate = None
        self._cache_expiry = None

    def create_interest_config(self, payload):
        rate = float(payload.get("rate"))
        # Chuyển string 'YYYY-MM-DD' từ UI sang datetime object
        effective_date = datetime.strptime(payload.get("effective_date"), "%Y-%m-%d")
        return self.repo.add_config(rate, effective_date)

    def get_current_rate(self):
        """
        Tối ưu: Cache lãi suất trong vòng 10 phút hoặc theo phiên làm việc 
        để tránh query DB liên tục trong vòng lặp tính giá CD.
        """
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Simple In-memory cache
        if self._cached_rate and self._cache_expiry == today:
            return self._cached_rate

        config = self.repo.get_latest_effective_rate(today)
        if config:
            self._cached_rate = config['rate']
            self._cache_expiry = today
            return self._cached_rate
        
        return 0.0 # Default nếu chưa có config
    

    def get_formatted_history(self):
        raw_data = self.repo.get_interest_history()
        # Format lại dữ liệu để UI dễ hiển thị
        for item in raw_data:
            if item.get('effective_date'):
                item['effective_date_str'] = item['effective_date'].strftime("%d/%m/%Y")
            if item.get('created_at'):
                item['created_at_str'] = item['created_at'].strftime("%H:%M %d/%m")
        return raw_data
    
    def get_rate_segments(self, start_date, end_date):
        """Xử lý dữ liệu từ Repo thành các phân đoạn [từ ngày - đến ngày - lãi suất]"""
        configs = self.repo.get_rates_in_range(start_date, end_date)
        if not configs:
            return []

        segments = []
        for i in range(len(configs)):
            conf = configs[i]
            # Ngày bắt đầu thực tế của đoạn này
            seg_start = max(conf['effective_date'].date(), start_date)
            
            # Ngày kết thúc của đoạn này (là ngày trước của config tiếp theo, hoặc là end_date)
            if i + 1 < len(configs):
                seg_end = min(configs[i+1]['effective_date'].date() - timedelta(days=1), end_date)
            else:
                seg_end = end_date
            
            if seg_end >= seg_start:
                segments.append({
                    "rate": conf['rate'] / 100.0,
                    "days": (seg_end - seg_start).days,
                    "is_start_of_period": seg_start == start_date
                })
        return segments