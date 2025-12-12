document.addEventListener("DOMContentLoaded", () => {

    const modal = document.getElementById("modal-add-cd");
    const openBtn = document.getElementById("btn-open-add-cd");  // NÚT TRIGGER
    const closeBtn = document.querySelector(".close-btn");
    const cancelBtn = document.querySelector(".cancel-btn");

    // OPEN MODAL
    if (openBtn) {
        openBtn.addEventListener("click", () => {
            modal.classList.remove("hidden");
        });
    }

    // CLOSE MODAL
    [closeBtn, cancelBtn].forEach(btn => {
        btn.addEventListener("click", () => {
            modal.classList.add("hidden");
        });
    });

    // TAB SWITCHING
    const tabBtns = document.querySelectorAll(".tab-btn");
    const tabPanes = document.querySelectorAll(".tab-pane");

    tabBtns.forEach(btn => {
        btn.addEventListener("click", () => {

            tabBtns.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");

            const tabId = btn.dataset.tab;

            tabPanes.forEach(pane => {
                pane.classList.remove("active");
                if (pane.id === tabId) {
                    pane.classList.add("active");
                }
            });
        });
    });

});

document.getElementById("save-btn").addEventListener("click", () => {

    const getNumber = (id) => {
        const element = document.getElementById(id);
        if (!element || !element.value) return 0; // Trả về 0 nếu rỗng

        // Bước 1: Loại bỏ dấu phẩy ngăn cách hàng nghìn (nếu có, VD: "1,000" -> "1000")
        const cleanValue = element.value.toString().replace(/,/g, '');
        
        // Bước 2: Chuyển sang Float (để nhận cả số thập phân)
        const numberValue = parseFloat(cleanValue);

        // Bước 3: Kiểm tra NaN (Not a Number), nếu lỗi trả về 0
        return isNaN(numberValue) ? 0 : numberValue;
    };

    // Helper lấy string (giữ nguyên logic cũ cho gọn code)
    const getString = (id) => document.getElementById(id)?.value || "";

    const payload = {
        thongTinChung: {
            maDoiChieu: getString("ma-doi-chieu"),
            toChuc: getString("to-chuc"),
            loaiLaiSuat: getString("loai-lai-suat"),
            
            CDKhaDung: getNumber("so-luong"), 
            soLuong: getNumber("so-luong"),
            menhGia: getNumber("menh-gia"),

            ngayPhatHanh: getString("ngay-phat-hanh"),
            ngayDaoHan: getString("ngay-dao-han"),
            ngayTHQuyen: getString("ngay-quyen"),
            ghiChu: getString("ghi-chu")
        },

        thongTinLaiSuat: {
            laiSuat: getNumber("lai-suat"), // Lãi suất thường là số
            tanSuatTraLai: getString("tan-suat"),
            quyUoc: getString("quy-uoc"),
        },

        thongTinNhapKho: {
            ngayTH: getString("ngay-th"),
            ngayTT: getString("ngay-tt"),
            
            // --- CÁC TRƯỜNG SỐ ĐÃ ĐƯỢC XỬ LÝ ---
            soLuongCD: getNumber("so-luong"), 
            dirtyPrice: getNumber("dirty-price")
            // ------------------------------------
        }
    };

    fetch("/cd/add", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    })
    .then(res => res.json())
    .then(result => {
        console.log(result);
        alert("Tạo CD thành công!");
    })
    .catch(err => {
        console.error(err);
        alert("Lỗi khi tạo CD.");
    });

});
