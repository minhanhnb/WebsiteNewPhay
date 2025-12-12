from flask import jsonify, request

class SystemController:
    def __init__(self, service):
        self.service = service

    # Controller KHÔNG còn hàm render_template nữa
    # Nó chỉ tập trung xử lý dữ liệu (Data Processing)

    def get_overview(self):
        """
        API handler: Lấy user_id từ request -> Gọi Service -> Trả JSON
        """
        # 1. Lấy tham số
        user_id = request.args.get('user_id')
        
        # 2. Validation
        if not user_id:
            return jsonify({
                "success": False, 
                "message": "Missing user_id parameter"
            }), 400
        
        try:
            # 3. Gọi Service
            data = self.service.get_full_overview(user_id)
            
            # 4. Kiểm tra kết quả trả về
            if not data.get('user'):
                 return jsonify({
                    "success": False, 
                    "message": "User not found"
                }), 404

            # 5. Trả về JSON thành công
            return jsonify({
                "success": True, 
                "data": data
            }), 200

        except Exception as e:
            # Log error (print hoặc dùng logger)
            print(f"Error in system_controller: {e}")
            return jsonify({
                "success": False, 
                "message": "Internal Server Error"
            }), 500
        

    def settle_cash(self):
        try:
            data = request.json
            date_str = data.get('date')
            # Lấy user_id từ request hoặc mặc định
            user_id = data.get('user_id', 'user_default') 

            if not date_str:
                return jsonify({"success": False, "message": "Thiếu ngày giao dịch"}), 400

            # Truyền user_id vào hàm
            result = self.service.process_daily_settlement(date_str, user_id)
            
            return jsonify({
                "success": result['status'] == 'success',
                "message": result['message']
            }), 200

        except Exception as e:
            print(f"Error settle_cash: {e}")
            return jsonify({"success": False, "message": str(e)}), 500
        

    def allocate_cd(self):
        """
        API Trigger phân bổ CD
        POST /system/api/allocate
        Body: { "user_id": "...", "date": "2023-12-12" }
        """
        try:
            # Lấy data từ Body JSON
            data = request.get_json() or {}
            
            user_id = data.get('user_id', 'user_default')
            date_str = data.get('date') # Lấy ngày được gửi lên

            # Gọi Service truyền thêm date_str
            result = self.service.process_asset_allocation(user_id, date_str)
            
            return jsonify({
                "success": result['status'] == 'success',
                "message": result['message'],
                "data": result.get('details', [])
            }), 200
        except Exception as e:
            print(f"Error Allocating: {e}")
            return jsonify({"success": False, "message": str(e)}), 500
            

    def withdraw_money(self):
        try:
            data = request.json or {}
            user_id = data.get('user_id', 'user_default')
            amount = data.get('amount')
            date_str = data.get('date')

            if not amount: return jsonify({"message": "Thiếu số tiền"}), 400
            
            result = self.service.process_withdrawal(user_id, amount, date_str)
            return jsonify({"success": result['status']=='success', "message": result['message']}), 200
        except Exception as e:
            return jsonify({"message": str(e)}), 500
        
    def reset_database(self):
        try:
            result = self.service.reset_database()
            return jsonify(result), 200
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500    

    def sync_bank(self):
        """API Trigger đồng bộ cuối ngày"""
        try:
            # Service đọc log từ queue và đẩy sang Bank Repo
            result = self.service.sync_batch_to_bank()
            return jsonify({"success": result['status']=='success', "message": result['message']}), 200
        except Exception as e:
            print(f"Sync Bank Error: {e}")
            return jsonify({"success": False, "message": str(e)}), 500