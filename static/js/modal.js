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

    const payload = {
        thongTinChung: {
            maDoiChieu: document.getElementById("ma-doi-chieu").value,
            toChuc: document.getElementById("to-chuc").value,
            loaiLaiSuat: document.getElementById("loai-lai-suat").value,
            CDKhaDung : document.getElementById("so-luong").value,
            soLuong : document.getElementById("so-luong").value,
            ngayPhatHanh: document.getElementById("ngay-phat-hanh").value,
            ngayDaoHan: document.getElementById("ngay-dao-han").value,
            menhGia: document.getElementById("menh-gia").value,
            ngayTHQuyen: document.getElementById("ngay-quyen").value,
            ghiChu: document.getElementById("ghi-chu").value
        },

        thongTinLaiSuat: {
           laiSuat: document.getElementById("lai-suat").value,
            tanSuatTraLai: document.getElementById("tan-suat").value,
            quyUoc: document.getElementById("quy-uoc").value,
        },

        thongTinNhapKho: {
            ngayTH: document.getElementById("ngay-th").value,
            ngayTT: document.getElementById("ngay-tt").value,
            soLuongCD: document.getElementById("so-luong").value,
            dirtyPrice: document.getElementById("dirty-price").value

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
