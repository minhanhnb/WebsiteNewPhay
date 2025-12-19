from firebase_config import db
from datetime import date, datetime, time

class ConfigRepository:
    def __init__(self):
        self.collection = db.collection("interest_rate_configs")

    def add_config(self, rate: float, effective_date: datetime):
        doc_ref = self.collection.document()
        data = {
            "rate": rate,
            "effective_date": effective_date,
            "created_at": datetime.now()
        }
        doc_ref.set(data)
        return doc_ref.id

    def get_latest_effective_rate(self, target_date: datetime):
        # Query: Lấy bản ghi có ngày áp dụng <= ngày mục tiêu, sắp xếp giảm dần theo ngày áp dụng
        query = self.collection.where("effective_date", "<=", target_date) \
                               .order_by("effective_date", direction="DESCENDING") \
                               .limit(1)
        docs = query.stream()
        for doc in docs:
            return doc.to_dict()
        return None
    
    def get_interest_history(self, limit=5):
        # Truy vấn Firestore lấy lịch sử giảm dần theo ngày áp dụng
        docs = db.collection("interest_rate_configs") \
                 .order_by("effective_date", direction="DESCENDING") \
                 .limit(limit).stream()
        return [doc.to_dict() for doc in docs]
    
    def get_rates_in_range(self, start_date, end_date):
        """Lấy tất cả config có ngày áp dụng nằm trong hoặc trước khoảng thời gian cần tính"""
        # Lấy các bản ghi có effective_date <= end_date để tìm rate cũ và rate mới
        if isinstance(start_date, date) and not isinstance(start_date, datetime):
            start_date = datetime.combine(start_date, time.min)
        if isinstance(end_date, date) and not isinstance(end_date, datetime):
            end_date = datetime.combine(end_date, time.min)
        docs = db.collection("interest_rate_configs") \
                 .where("effective_date", "<=", end_date) \
                 .order_by("effective_date", direction="ASCENDING").stream()
        
        return [doc.to_dict() for doc in docs]