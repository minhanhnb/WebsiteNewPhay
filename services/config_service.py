from repository.config_repo import ConfigRepository
from functools import lru_cache
from datetime import date, datetime

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