document.addEventListener("DOMContentLoaded", () => {
    // --- 1. CONFIG & ELEMENTS ---
    const elTotal = document.getElementById("totalBalance");
    const elTableBody = document.getElementById("historyBody");
    const elViewDate = document.getElementById("viewDate");
    const form = document.getElementById("transForm");
    
    // Default Date
    const todayStr = new Date().toISOString().split('T')[0];
    const transDateInput = document.getElementById("transDate");
    if (transDateInput) transDateInput.value = todayStr;
    if (elViewDate) elViewDate.value = todayStr;
    
    const formatMoney = (val) => new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(val);

    // --- 2. MAIN FUNCTIONS ---

    // A. Tải dữ liệu Dashboard
    async function loadData() {
        try {
            let targetDate = new Date().toISOString().split('T')[0];
            if (elViewDate && elViewDate.value) {
                targetDate = elViewDate.value;
            }

            // [FIX CACHE] Thêm tham số t=... để ép trình duyệt không dùng Cache cũ
            const timestamp = new Date().getTime(); 
            const res = await fetch(`/ttt/api/dashboard?date=${targetDate}&t=${timestamp}`);
            
            if (!res.ok) throw new Error("API Error");
            const data = await res.json();

            // Hiển thị Tổng Tài Sản (Cash + Assets)
            if (elTotal) elTotal.innerText = formatMoney(data.balance);
            
            // Hiển thị Lịch sử
            if (elTableBody) renderHistory(data.history || []);

        } catch (err) {
            console.error("Lỗi:", err);
            if (elTotal) elTotal.innerText = "Error";
        }
    }

    if (elViewDate) elViewDate.addEventListener("change", loadData);

    // B. Render Lịch sử & Gắn sự kiện Xóa
    function renderHistory(history) {
        elTableBody.innerHTML = "";

        if (!history || history.length === 0) {
            elTableBody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">Chưa có giao dịch nào</td></tr>';
            return;
        }

        history.forEach(item => {
            const row = document.createElement("tr");
            const isNap = item.type === "NAP";
            const cls = isNap ? "type-nap" : "type-rut";
            const label = isNap ? "Nạp tiền" : "Rút tiền";
            const sign = isNap ? "+" : "-";
            const date = item.date
            
            const transId = item.id || item._id;

            row.innerHTML = `
                <td>${date}</td>
                <td><span class="${cls}">${label}</span></td>
                <td class="${cls} fw-bold">${sign} ${formatMoney(item.amount)}</td>
                <td class="text-muted small">${item.note || ""}</td>
                <td class="text-center">
                    <button class="btn-delete" data-id="${transId}" 
                            style="border:none; background:transparent; color:#e74c3c; cursor:pointer; font-size: 1.1rem;"
                            title="Xóa giao dịch này">
                        <i class="fas fa-trash-alt"></i> 🗑
                    </button>
                </td>
            `;
            elTableBody.appendChild(row);
        });

        // Gắn sự kiện Click Xóa
        document.querySelectorAll(".btn-delete").forEach(btn => {
            btn.addEventListener("click", async (e) => {
                e.preventDefault();
                const button = e.currentTarget; 
                const transId = button.getAttribute("data-id");

                if (!transId) return;

                if (confirm("⚠️ CẢNH BÁO: Xóa giao dịch này sẽ hoàn lại tiền vào ví Finsight. Bạn có chắc chắn?")) {
                    await deleteTransaction(transId);
                }
            });
        });
    }

    // C. Hàm gọi API Xóa
    async function deleteTransaction(transId) {
        try {
            const res = await fetch(`/ttt/api/transact/${transId}`, {
                method: "DELETE"
            });
            const result = await res.json();
            
            if (res.ok && result.success) {
                alert("✅ " + result.message);
                // Gọi loadData để cập nhật ngay lập tức
                await loadData();
            } else {
                alert("❌ " + (result.message || "Lỗi xóa giao dịch"));
            }
        } catch (err) {
            console.error(err);
            alert("Lỗi kết nối server khi xóa");
        }
    }

    // --- 3. SUBMIT FORM (NẠP/RÚT) ---
    // --- 3. SUBMIT FORM (NẠP/RÚT) ---
    if (form) {
        form.addEventListener("submit", async (e) => {
            e.preventDefault();
            
            // ... (Phần lấy dữ liệu input giữ nguyên) ...
            const actionInput = document.querySelector('input[name="action"]:checked');
            if (!actionInput) { alert("Vui lòng chọn hành động!"); return; }
            
            const action = actionInput.value;
            const date_trans = document.getElementById("transDate").value;
            const rawAmount = document.getElementById("transAmount").value;
            const amount = parseFloat(rawAmount.replace(/\./g, "").replace(/,/g, "."));

            if (!amount || amount <= 0) {
                alert("Số tiền không hợp lệ!");
                return;
            }

            if (action === "RUT") {
                if(!confirm(`Xác nhận RÚT ${formatMoney(amount)}?\nHệ thống sẽ tự động bán CD nếu tiền mặt không đủ.`)) return;
            }

            const payload = { 
                action_type: action, 
                amount: amount, 
                date_trans: date_trans, 
                note: document.getElementById("transNote").value,
                user_id: "user_default"
            };

            const btnSubmit = form.querySelector(".btn-submit");
            const orgText = btnSubmit.innerText;

            try {
                btnSubmit.innerText = "Đang xử lý...";
                btnSubmit.disabled = true;

                const res = await fetch("/ttt/api/transact", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload)
                });
                
                const result = await res.json();
                console.log("Submit Result:", result); // Debug log

                // [FIX LỖI TẠI ĐÂY]
                // Backend trả về { "status": "success" }, không phải { "success": true }
                // Nên ta phải check result.status === 'success'
                if (res.ok && result.status === 'success') {
                    alert("✅ " + result.message);
                    
                    // Reset form
                    form.reset();
                    document.getElementById("transDate").value = new Date().toISOString().split('T')[0];
                    document.getElementById("actNap").checked = true;
                    
                    // Gọi loadData để cập nhật số dư
                    console.log("Calling loadData()...");
                    await loadData(); 
                    
                } else {
                    alert("❌ " + (result.message || "Có lỗi xảy ra"));
                }
            } catch (err) {
                console.error(err);
                alert("Lỗi kết nối server");
            } finally {
                btnSubmit.innerText = orgText;
                btnSubmit.disabled = false;
            }
        });
    }

    // Auto format input money
    const inputAmount = document.getElementById("transAmount");
    if (inputAmount) {
        inputAmount.addEventListener("input", (e) => {
            let val = e.target.value.replace(/\D/g, "");
            if (val) e.target.value = new Intl.NumberFormat('vi-VN').format(parseInt(val));
        });
    }

    // --- 4. INIT ---
    loadData();
});