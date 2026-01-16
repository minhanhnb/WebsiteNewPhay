from flask import jsonify, request

class TransactionController3:
    def __init__(self, service):
        self.service = service

    def get_dashboard_data(self):
        # Lấy tham số ?date=... từ URL
        target_date = request.args.get('date')
        
        # Gọi service
        data = self.service.get_user_dashboard(target_date_str=target_date)
        
        return jsonify(data), 200

    def submit_transaction(self):
        try:
            data = request.json
            result = self.service.add_transaction(data)
            print("Đang chạy controller system 2")
            if result.get("status") == "success":
                return jsonify(result), 200
            else:
                return jsonify(result), 400
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
    
    def delete_transaction(self, trans_id):
        try:
            result = self.service.delete_transaction(trans_id)
            
            if result.get("status") == "success":
                return jsonify(result), 200
            else:
                return jsonify(result), 400
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500