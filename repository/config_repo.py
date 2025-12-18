from firebase_config import db
from datetime import datetime

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