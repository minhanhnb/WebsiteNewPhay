from firebase_config import db

class BaseRepository:
    def __init__(self, collection_name):
        self.collection = db.collection(collection_name)

    def _get_first(self):
        """Helper để lấy document đầu tiên (dùng cho Bank/Finsight)"""
        docs = self.collection.limit(1).stream()
        for doc in docs:
            return doc.to_dict()
        return None