from flask import jsonify, request
from services.cd_service import CDService

class CDController:
    def __init__(self, service: CDService):
        self.service = service

    def add_cd(self):
        try:
            payload = request.get_json()
            result = self.service.add_cd(payload)
            return jsonify(result), 201
        
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        
        except Exception as e:
            return jsonify({"error": "Internal server error"}), 500
    
    def get_all_cd(self):
        return self.service.get_all_cd()
    
    
    def get_cd_detail(self, maDoiChieu):
        return self.service.get_cd_by_id(maDoiChieu)

    def sync_daily_price(self):
        try:
            # Có thể nhận thêm tham số 'system_rate' từ request nếu muốn dùng 1 lãi suất chung
            # data = request.json 
            # system_rate = data.get('rate', None)
            
            result = self.service.calculate_daily_price_batch()
            return jsonify(result), 200
        except Exception as e:
            print(f"Controller Error: {e}")
            return jsonify({"message": str(e)}), 500