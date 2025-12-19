document.addEventListener("DOMContentLoaded", () => {

    const modal = document.getElementById("modal-config-rate");
    const openBtn = document.getElementById("btn-open-config-rate");  // NÚT TRIGGER
    const closeBtn = document.querySelector(".close-modal");
    const cancelBtn = document.querySelector(".cancel-btn");

    // OPEN MODAL
    if (openBtn) {
        openBtn.addEventListener("click", () => {
            loadHistory();
            modal.classList.remove("hidden");
        });
    }

    // CLOSE MODAL
    [closeBtn, cancelBtn].forEach(btn => {
        btn.addEventListener("click", () => {
            modal.classList.add("hidden");
        });
    });

 
document.getElementById('btn-apply-rate').onclick = async () => {
    const data = {
        rate: document.getElementById('input-new-rate').value,
        effective_date: document.getElementById('input-effective-date').value
    };

    if(!data.rate || !data.effective_date) return alert("Vui lòng nhập đủ thông tin");

    const response = await fetch('/api/config/interest-rate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });

    if(response.ok) {
        alert("Cấu hình lãi suất thành công! Hệ thống sẽ áp dụng từ ngày bạn đã chọn.");
    } else {
        alert("Có lỗi xảy ra.");
    }
};

async function loadInterestHistory() {
    const tbody = document.getElementById('interest-history-body');
    tbody.innerHTML = '<tr><td colspan="3">Đang tải...</td></tr>';

    try {
        const res = await fetch('/api/config/interest-history');
        const data = await res.json();
        
        tbody.innerHTML = ''; // Xóa trạng thái loading
        
        data.forEach(item => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><strong>${item.effective_date}</strong></td>
                <td><span class="status-badge" style="background:#e3f2fd; color:#1976d2">${item.rate}%</span></td>
                <td style="color: #888">${item.created_at}</td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        tbody.innerHTML = '<tr><td colspan="3">Không thể tải dữ liệu</td></tr>';
    }
}

// Gọi hàm này khi bấm nút mở Modal
document.getElementById('btn-open-config-rate').addEventListener('click', () => {
    document.getElementById('modal-config-rate').classList.remove('hidden');
    loadInterestHistory(); // Cập nhật lại bảng mỗi lần mở
});

});
