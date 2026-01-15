class Bank3:
    # Thêm default value = 0 hoặc None để có thể khởi tạo Bank() rỗng
    def __init__(self, taiSanUser=None, tienMatUser=0, tienMatFinsight=0, taiSanFinsight=0):
        self.taiSanUser = taiSanUser if taiSanUser else []  # Đảm bảo luôn là list
        self.tienMatUser = float(tienMatUser)
        self.tienMatFinsight = float(tienMatFinsight)
        self.taiSanFinsight = float(taiSanFinsight)

    def to_dict(self):
        return {
            "taiSanUser": self.taiSanUser,
            "tienMatUser": self.tienMatUser, 
            "tienMatFinsight": self.tienMatFinsight,
            "taiSanFinsight": self.taiSanFinsight,
        }