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

    # def sync_daily_price(self):
    #     try:
    #         # Có thể nhận thêm tham số 'system_rate' từ request nếu muốn dùng 1 lãi suất chung
    #         # data = request.json 
    #         # system_rate = data.get('rate', None)
            
    #         result = self.service.calculate_daily_price_batch()
    #         return jsonify(result), 200
    #     except Exception as e:
    #         print(f"Controller Error: {e}")
    #         return jsonify({"message": str(e)}), 500

    def handle_delete_asset(self, asset_id):
        try:
            # Gọi Service xử lý nghiệp vụ
            success, message = self.service.delete_asset_logic(asset_id)
            
            if success:
                return jsonify({"success": True, "message": message}), 200
            return jsonify({"success": False, "message": message}), 400
        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 500
            

    