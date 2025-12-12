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
    if(settleDateInput) settleDateInput.value = new Date().toISOString().split('T')[0];
    
    setInterval(() => {
        document.getElementById('clock').innerText = new Date().toLocaleString('vi-VN');
    }, 1000);

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
            const res = await fetch(`/system/api/overview?user_id=${TEST_USER_ID}`);
            const result = await res.json();
            
            if (res.ok && result.success) {
                const { user, bank, finsight } = result.data;
                renderUserWallet(user, result.data.total_balance_estimate);
                renderSystemFund(finsight, user);
                renderBank(bank);
            }
        } catch (err) {
            console.error(err);
        } finally {
            loadingOverlay.style.display = 'none';
        }
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
                    <td class="text-end text-muted">${formatMoney(a.giaVon)}</td>
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

    loadSystemData();
});