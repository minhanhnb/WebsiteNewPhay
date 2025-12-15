let switchTab; // Global function

document.addEventListener("DOMContentLoaded", () => {
    const TEST_USER_ID = "user_default";
    const loadingOverlay = document.getElementById("loading-overlay");

    const containers = {
        user: document.getElementById('user-data-container'),
        system: document.getElementById('finsight-data-container'),
        bank: document.getElementById('bank-data-container')
    };

    const sections = {
        user: document.getElementById('section-user'),
        system: document.getElementById('section-system'),
        bank: document.getElementById('section-bank')
    };

    // Date & Clock
    const settleDateInput = document.getElementById("settleDate");
    const viewDateInput = document.getElementById("viewDate");
    const todayStr = new Date().toISOString().split('T')[0];
    if(settleDateInput) settleDateInput.value = todayStr;
    if(viewDateInput) viewDateInput.value = todayStr;

    // --- TAB SWITCHER ---
    switchTab = function(tabName, el) {
        // Active Style
        document.querySelectorAll('.tab-link').forEach(t => t.classList.remove('active'));
        if(el) el.classList.add('active');

        // Toggle Content
        if(tabName === 'all') {
            Object.values(sections).forEach(s => s.classList.remove('hidden'));
        } else {
            Object.values(sections).forEach(s => s.classList.add('hidden'));
            if(sections[tabName]) sections[tabName].classList.remove('hidden');
        }
    };

    // --- DATA LOADING ---
    async function loadSystemData() {
        loadingOverlay.style.display = 'flex';
        try {
            // Lấy ngày từ input viewDate
            const vDate = viewDateInput ? viewDateInput.value : todayStr;
            
            // Gọi API với query parameter view_date
            const res = await fetch(`/system/api/overview?user_id=${TEST_USER_ID}&view_date=${vDate}`);
            const result = await res.json();

            
            if (res.ok && result.success) {
                // ... render logic giữ nguyên ...
                const { user, bank, finsight } = result.data;
                renderUserWallet(user, result.data.total_balance_estimate);
                renderSystemFund(finsight, user);
                renderBank(bank);
                renderQueue(result.data.queue); 
                renderPerformance(result.data.performance); 
            }
        } catch (err) {
            console.error(err);
        } finally {
            loadingOverlay.style.display = 'none';
        }
    }

    // [NEW] Auto reload khi đổi ngày xem
    if(viewDateInput) {
        viewDateInput.addEventListener("change", () => {
            loadSystemData(); // Gọi lại API ngay khi chọn ngày khác
        });
    }

    // --- RENDER HELPERS ---
    const formatMoney = (val) => new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(val || 0);

    // CARD TỐI GIẢN (Bỏ hết tham số màu mè, chỉ còn Label & Value)
    const createCard = (label, value, isMoney=false) => `
        <div class="stat-card">
            <div class="stat-label">${label}</div>
            <div class="stat-value">${isMoney ? formatMoney(value) : value}</div>
        </div>`;

    // --- RENDER SECTIONS ---

    // 1. User Wallet
    function renderUserWallet(user, totalEst) {
        if (!user) return;
        containers.user.innerHTML = `
            ${createCard('Số dư Ví', totalEst, true)}
        `;
    }

    // 2. System Fund (Kèm Bảng)
    function renderSystemFund(sys, user) {
        if (!sys || !user) return;
        
        const totalUserAssetValue = user.total_asset_value || 0;
        let assetDetailsHtml = '';

        // Bảng danh sách CD
        if (user.assets && user.assets.length > 0) {
            const rows = user.assets.map(a => `
                <tr>
                    <td class="fw-bold">${a.maCD}</td>
                    <td class="text-end">${a.soLuong}</td>
                </tr>`).join('');
            
            assetDetailsHtml = `
                <div class="mt-3 pt-2 border-top">
                    <div class="stat-label mb-2">Danh mục chi tiết</div>
                    <div style="max-height: 200px; overflow-y: auto;">
                        <table class="table table-sm table-borderless table-minimal mb-0">
                            <thead><tr><th>Mã</th><th class="text-end">SL</th></tr></thead>
                            <tbody>${rows}</tbody>
                        </table>
                    </div>
                </div>`;
        } else {
            assetDetailsHtml = '<div class="mt-3 pt-2 border-top small text-muted">Không có tài sản CD</div>';
        }

        containers.system.innerHTML = `
            ${createCard('Tiền Finsight', sys.tienMatFinSight, true)}
            ${createCard('Tiền User', user.cash, true)}
            
            <div class="stat-card" style="grid-column: 1 / -1;">
                <div class="d-flex justify-content-between">
                    <div>
                        <div class="stat-label">Tài sản CD của User</div>
                        <div class="stat-value" style="color: var(--accent-color);">${formatMoney(totalUserAssetValue)}</div>
                    </div>
                </div>
                ${assetDetailsHtml}
            </div>
        `;
    }

    // 3. Bank NHLK
    function renderBank(bank) {
        if (!bank) return;
        
        const assetList = bank.taiSanUser || [];
        let assetHtml = '';

        if (assetList.length > 0) {
            const rows = assetList.map(a => {
                const code = (typeof a === 'object') ? a.maCD : a;
                const qty = (typeof a === 'object') ? a.soLuong : '-';
                return `<tr><td>${code}</td><td class="text-end">${qty}</td></tr>`;
            }).join('');

            assetHtml = `
                <div class="mt-3 pt-2 border-top">
                    <div class="stat-label mb-2">Danh mục Lưu Ký</div>
                    <div style="max-height: 150px; overflow-y: auto;">
                        <table class="table table-sm table-borderless table-minimal mb-0">
                            <thead><tr><th>Mã</th><th class="text-end">SL</th></tr></thead>
                            <tbody>${rows}</tbody>
                        </table>
                    </div>
                </div>`;
        } else {
            assetHtml = '<div class="mt-3 pt-2 border-top small text-muted">Chưa lưu ký</div>';
        }

        containers.bank.innerHTML = `
            ${createCard('Tiền Finsight', bank.tienMatFinsight, true)}
            ${createCard('Tiền User', bank.tienMatUser, true)}

            <div class="stat-card" style="grid-column: 1 / -1;">
                <div class="stat-label">Tài sản User</div>
                <div class="stat-value">${assetList.length} <span style="font-size: 1rem; font-weight: 400; color: #999;">mã</span></div>
                ${assetHtml}
            </div>
        `;
    }
   //Render hàng đợi settle
    function renderQueue(queue) {
        const container = document.getElementById("queueContainer");
        const countBadge = document.getElementById("queueCount");
        
        if (!queue || queue.length === 0) {
            container.innerHTML = `
                <div class="h-100 d-flex flex-column justify-content-center align-items-center text-muted opacity-50">
                    <i class="fas fa-check-double fa-2x mb-2"></i>
                    <small>Tất cả đã được đồng bộ</small>
                </div>`;
            countBadge.innerText = "0 lệnh";
            countBadge.className = "badge bg-light text-muted border";
            // Disable nút Sync nếu không có gì để sync
            document.getElementById("btnSyncBank").disabled = true;
            return;
        }

        // Enable nút Sync
        const btnSync = document.getElementById("btnSyncBank");
        btnSync.disabled = false;
        btnSync.innerHTML = `<i class="fas fa-sync me-2"></i> Gửi lệnh Lưu ký (${queue.length})`;
        
        countBadge.innerText = `${queue.length} chờ xử lý`;
        countBadge.className = "badge bg-danger";

        // Map loại giao dịch sang tiếng Việt & Style
        const typeMap = {
            'CASH_IN': { text: 'Nạp Tiền', class: 'q-cash-in', icon: '+' },
            'CASH_OUT': { text: 'Rút Tiền', class: 'q-cash-out', icon: '-' },
            'ALLOCATION_CASH_PAID': { text: 'Thanh toán mua CD', class: 'q-alloc', icon: '-' },
            'ALLOCATION_ASSET_DELIVERED': { text: 'Nhận CD (Kho)', class: 'q-alloc', icon: '📦' },
            'LIQUIDATE_CD': { text: 'Bán CD (Kho)', class: 'q-liq', icon: '📦' }
        };

        const html = queue.map(item => {
            const map = typeMap[item.type] || { text: item.type, class: 'bg-light', icon: '•' };
            const amountStr = item.amount > 0 ? formatMoney(item.amount) : '';
            
            return `
                <div class="queue-item">
                    <div class="d-flex align-items-center gap-2">
                        <span class="q-badge ${map.class}">${map.text}</span>
                    </div>
                    <div class="fw-bold text-dark small">
                        ${map.icon} ${amountStr}
                    </div>
                </div>
            `;
        }).join('');

        container.innerHTML = html;
    }
    function renderPerformance(perf) {
        // Tìm container User để chèn vào (Hoặc tạo container riêng tùy bạn)
        // Ở đây tôi sẽ chèn nó vào đầu tiên trong User Container để user dễ thấy nhất
        const container = containers.user; 
        
        if (!perf) return;

        const profitToday = perf.profit_today || 0;
        const profitMonth = perf.profit_month || 0;

        // Xác định màu sắc: Lời (Xanh), Lỗ (Đỏ), Hòa (Xám)
        const colorClass = profitToday >= 0 ? 'text-success' : 'text-danger';
        const sign = profitToday > 0 ? '+' : ''; // Thêm dấu cộng cho đẹp

        const html = `
            <div class="stat-card" style="border-left: 5px solid #2ecc71;">
                <div class="d-flex justify-content-between align-items-start">
                    <div class="stat-label text-uppercase fw-bold text-success">
                        <i class="fas fa-chart-line me-2"></i>Hiệu quả đầu tư
                    </div>
                    <span class="badge bg-light text-muted border" style="font-size: 0.7rem;">
                        ${perf.last_updated}
                    </span>
                </div>

                <div class="mt-2">
                    <small class="text-muted">Lợi nhuận hôm nay</small>
                    <div class="stat-value ${colorClass}">
                        ${sign} ${formatMoney(profitToday)}
                    </div>
                </div>

                <div class="mt-3 pt-2 border-top d-flex justify-content-between align-items-center">
                    <span class="text-dark small fw-bold">Tháng này:</span>
                    <span class="fw-bold text-dark">
                        ${profitMonth > 0 ? '+' : ''}${formatMoney(profitMonth)}
                    </span>
                </div>
            </div>
        `;

        // Chèn vào đầu danh sách thẻ của User
        // container.innerHTML = html + container.innerHTML; 
        // Hoặc nếu muốn thay thế/bổ sung tùy layout, ở đây tôi dùng insertAdjacentHTML
        container.insertAdjacentHTML('afterbegin', html);
    }

    // --- BUTTON ACTIONS ---
    async function callApi(url, body) {
        loadingOverlay.style.display = 'flex';
        try {
            const res = await fetch(url, {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify(body)
            });
            const data = await res.json();
            alert((data.success ? "Thành công" : "Lỗi") + ": " + data.message);
            if(data.success) loadSystemData();
        } catch(e) {
            alert("Lỗi kết nối server");
        } finally {
            loadingOverlay.style.display = 'none';
        }
    }

    document.getElementById("btnSettle")?.addEventListener("click", () => {
        if(confirm("Xác nhận Chốt Sổ?")) callApi("/system/api/settle", { date: settleDateInput.value });
    });
    document.getElementById("btnAllocate")?.addEventListener("click", () => {
        if(confirm("Xác nhận Phân Bổ CD?")) callApi("/system/api/allocate", { date: settleDateInput.value, user_id: TEST_USER_ID });
    });
    document.getElementById("btnSyncBank")?.addEventListener("click", () => {
        if(confirm("Xác nhận Đồng bộ sang NHLK?")) callApi("/system/api/sync-bank", {});
    });

    document.getElementById("btnResetData")?.addEventListener("click", async () => {
        // Cảnh báo 2 lớp để tránh bấm nhầm
        if (!confirm("⚠️ NGUY HIỂM: Bạn có chắc chắn muốn XÓA TOÀN BỘ dữ liệu (Ngoại trừ thông tin CD)?")) return;
        if (!confirm("Xác nhận lần cuối: Hành động này không thể hoàn tác. Mọi tài khoản, giao dịch sẽ mất tại Ví User, CoreTVAM và NHLK.")) return;

        await callApi("/system/api/reset", {});
        
        // Sau khi reset, reload lại trang để về trạng thái trắng
        window.location.reload();
    });
    function scrollToSection(id) {
        const el = document.getElementById(id);
        if(el) {
            el.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'start' });
            
            // Highlight Tab active (chỉ là visual)
            document.querySelectorAll('.tab-link').forEach(t => t.classList.remove('active'));
            event.target.classList.add('active');
        }
    }
    
    // Override hàm switchTab cũ trong system_dashboard.js nếu cần thiết
    // (Vì layout ngang thì không cần ẩn hiện display:none nữa)
    window.switchTab = function(tabName, el) {
       // Logic cũ là ẩn hiện, logic mới là scroll tới
       // Bạn có thể xóa code cũ hoặc để code này đè lên.
       if(tabName === 'all') return; // Không làm gì
       
       let targetId = '';
       if(tabName === 'user') targetId = 'section-user';
       if(tabName === 'system') targetId = 'section-system';
       if(tabName === 'bank') targetId = 'section-bank';
       
       scrollToSection(targetId);
    };

    loadSystemData();
});