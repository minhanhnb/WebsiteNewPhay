document.addEventListener("DOMContentLoaded", async () => {
    const tableBody = document.getElementById("cd-table-body");
    const pagination = document.getElementById("pagination");

    let cds = [];
    let page = 1;
    const pageSize = 5;

  // --- Fetch CD từ backend ---
async function loadCDs() {
    const res = await fetch("/cd/all");
    const data = await res.json();

    // Dữ liệu là một array => gán trực tiếp
    cds = Array.isArray(data) ? data : [];

    renderTable();
    renderPagination();
}

function renderTable() {
    tableBody.innerHTML = "";

    const start = (page - 1) * pageSize;
    const end = start + pageSize;
    const pageItems = cds.slice(start, end);

    pageItems.forEach(cd => {
        const maDoiChieu = cd?.thongTinChung?.maDoiChieu ?? "-";
        const CDKhaDung = cd?.thongTinChung?.CDKhaDung ?? "-";

        const tr = document.createElement("tr");

        tr.innerHTML = `
            <td id="data-id">${maDoiChieu}</td>
            <td>${CDKhaDung}</td>
            <td>
                <button class="btn-view" data-id="${maDoiChieu}">
                    Xem CD
                </button>
                <button class="btn-delete" data-id="${maDoiChieu}">
                    Xóa CD
                </button>
            </td>
        `;

        tableBody.appendChild(tr);
    });
}

    function renderPagination() {
        pagination.innerHTML = "";

        const totalPages = Math.ceil(cds.length / pageSize);

        for (let i = 1; i <= totalPages; i++) {
            const btn = document.createElement("button");
            btn.textContent = i;
            if (i === page) btn.classList.add("active");

            btn.addEventListener("click", () => {
                page = i;
                renderTable();
                renderPagination();
            });

            pagination.appendChild(btn);
        }
    }

    // --- Xử lý xem chi tiết ---
    document.addEventListener("click", e => {
        if (e.target.classList.contains("btn-view")) {
            const id = e.target.dataset.id;
            const cd = cds.find(x => x.maDoiChieu === id);
            openDetail(cd);
        }
    });


    // Load ban đầu
    loadCDs();
});

document.addEventListener("click", function (e) {
    if (e.target.classList.contains("btn-view")) {
        const id = e.target.dataset.id;
        window.location.href = `/cd/manage/${id}`; 
    }
});

document.addEventListener("click", async function (e) {
    // Tìm button delete gần nhất (hỗ trợ cả khi click trúng icon bên trong)
    const btn = e.target.closest(".btn-delete");
    if (!btn) return;

    const assetId = btn.getAttribute("data-id");
    const assetName = btn.closest("tr")?.querySelector("td:first-child")?.innerText || "tài sản này";

    // 1. Cảnh báo bảo mật: Xóa tài sản là hành động nhạy cảm
    if (!confirm(`⚠️ XÁC NHẬN XÓA: Bạn có chắc chắn muốn xóa mã CD: ${assetName} khỏi hệ thống?`)) return;

    try {
        btn.disabled = true;
        const response = await fetch(`/cd/delete/${assetId}`, {
            method: "DELETE",
            headers: { "Content-Type": "application/json" }
        });

        const result = await response.json();

        if (response.ok && result.success) {
            alert("✅ Đã xóa tài sản thành công.");
            // Gọi lại hàm
            if (typeof loadCDs === "function") loadCDs();
        } else {
            alert("❌ Lỗi: " + result.message);
        }
    } catch (err) {
        console.error("Delete Asset Error:", err);
        alert("❌ Lỗi kết nối server.");
    } finally {
        btn.disabled = false;
    }
     loadCDs();
});
document.getElementById("btn-sync-price").addEventListener("click", async () => {
    if (!confirm("Bạn có chắc chắn muốn tính toán lại giá bán cho TOÀN BỘ CD trong kho?")) return;

    const btn = document.getElementById("btn-sync-price");
    const originalText = btn.innerText;
    btn.innerText = "Đang tính toán...";
    btn.disabled = true;

    try {
        const res = await fetch("/cd/sync-daily-price", {
            method: "POST",
            headers: { "Content-Type": "application/json" }
        });
        
        const data = await res.json();
        
        if (res.ok) {
            alert(`✅ ${data.message}`);
            // Reload lại bảng để thấy giá mới (nếu bảng có hiện cột giá)
            location.reload(); 
        } else {
            alert(`❌ Lỗi: ${data.message}`);
        }
    } catch (err) {
        console.error(err);
        alert("Có lỗi xảy ra khi kết nối server.");
    } finally {
        btn.innerText = originalText;
        btn.disabled = false;
    }
});