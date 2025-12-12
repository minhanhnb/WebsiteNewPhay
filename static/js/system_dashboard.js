// Biến global để HTML gọi được
let switchTab;
document.addEventListener("DOMContentLoaded", () => {
    // 1. CONFIG
    const TEST_USER_ID = "user_default";
    const loadingOverlay = document.getElementById("loading-overlay");

    // Elements
    const containers = {
        user: document.getElementById('user-data-container'),
        system: document.getElementById('finsight-data-container'),// Tab 2: System Fund
        bank: document.getElementById('bank-data-container')
    };

    const settleDateInput = document.getElementById("settleDate");
    if(settleDateInput) settleDateInput.value = new Date().toISOString().split('T')[0];

    // Helpers
    const formatMoney = (val) => new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(val || 0);
    const createCard = (label, value, icon, isMoney=false, colorClass='text-dark', borderClass='') => `
        <div class="stat-card ${borderClass}">
            <i class="${icon} stat-icon"></i>
            <div class="stat-label">${label}</div>
            <div class="stat-value ${colorClass}">${isMoney ? formatMoney(value) : value}</div>
        </div>`;

    // 2. MAIN LOAD DATA
    async function loadSystemData() {
        loadingOverlay.style.display = 'flex';
        try {
            const res = await fetch(`/system/api/overview?user_id=${TEST_USER_ID}`);
            const result = await res.json();
            
            if (res.ok && result.success) {
                const { user, bank, finsight } = result.data;
                
                // [FIX 1] Truyền cả user vào hàm renderSystemFund
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

    // --- RENDER FUNCTIONS ---

// --- RENDER FUNCTIONS ---

    // TAB 1: USER WALLET (Đã sửa: Chỉ hiện Số dư tổng và Tiền mặt)
    function renderUserWallet(user, totalEst) {
        if (!user) return;
        
        // Tab này bây giờ rất gọn, chỉ tập trung vào Net Worth
        containers.user.innerHTML = `
            ${createCard('Số dư (Balance)', totalEst, 'fas fa-wallet', true, 'text-success', 'border-success')}
        `;
    }


    // TAB 2: SYSTEM FUND (Đã sửa: Lồng bảng chi tiết vào Card Tổng giá trị CD)
    // TAB 2: SYSTEM FUND (Đã sửa: Hiện bảng CD luôn, bỏ nút toggle)
    function renderSystemFund(sys, user) {
        if (!sys || !user) return;
        
        // 1. Tính toán số liệu
        const totalUserCash = user.cash;
        const totalUserAssetValue = user.total_asset_value || 0;

        // 2. Xây dựng nội dung bảng (Table HTML)
        let assetDetailsHtml = '';
        
        const hasAssets = user.assets && user.assets.length > 0;

        if (hasAssets) {
            const rows = user.assets.map(a => `
                <tr>
                    <td class="fw-bold text-primary">${a.maCD}</td>
                    <td class="text-end fw-bold">${a.soLuong}</td>
                    <td class="text-end text-muted">${formatMoney(a.giaVon)}</td>
                </tr>`).join('');
            
            // Render bảng trực tiếp (không dùng class 'collapse')
            // Thêm style max-height để nếu danh sách dài quá thì cuộn, không làm vỡ giao diện
            assetDetailsHtml = `
                <div class="mt-3 border-top pt-3">
                    <div class="small fw-bold text-muted mb-2 text-uppercase" style="font-size: 0.75rem;">
                        Chi tiết danh mục (${user.assets.length} mã)
                    </div>
                    <div class="mini-table-container" style="max-height: 200px; overflow-y: auto;">
                        <table class="table table-sm table-hover table-borderless mb-0">
                            <thead class="text-secondary sticky-top bg-white" style="font-size: 0.8rem; text-transform: uppercase;">
                                <tr>
                                    <th>Mã CD</th>
                                    <th class="text-end">Số Lượng</th>
                                    <th class="text-end">Giá Vốn</th>
                                </tr>
                            </thead>
                            <tbody>${rows}</tbody>
                        </table>
                    </div>
                </div>
            `;
        } else {
            // Trường hợp không có tài sản
            assetDetailsHtml = `
                <div class="mt-3 border-top pt-3 text-muted fst-italic small">
                    User chưa nắm giữ CD nào
                </div>
            `;
        }

        // 3. Render HTML
        containers.system.innerHTML = `
            ${createCard('Tiền mặt Finsight', sys.tienMatFinSight, 'fas fa-vault', true, 'text-danger', 'border-danger')}            
            
            ${createCard('Tiền mặt User', totalUserCash, 'fas fa-users', true, 'text-primary', 'border-primary')}
            
            <div class="stat-card border-info" style="grid-column: 1 / -1;">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <div class="stat-label">Tổng Giá trị CD User</div>
                        <div class="stat-value text-info">${formatMoney(totalUserAssetValue)}</div>
                    </div>
                    <i class="fas fa-hand-holding-usd stat-icon position-static text-info opacity-25" style="font-size: 3rem;"></i>
                </div>
                
                ${assetDetailsHtml}
            </div>
        `;
    }
          

   // TAB 3: BANK (Đã sửa: Hiển thị chi tiết Mã CD và Số Lượng)
    function renderBank(bank) {
        if (!bank) return;
        
        const assetList = bank.taiSanUser || [];
        const assetCount = assetList.length;

        // 1. Tạo bảng danh sách Tài sản lưu ký
        let assetHtml = '<div class="text-center text-muted py-3 small">Chưa có tài sản lưu ký</div>';

        if (assetCount > 0) {
            const rows = assetList.map(a => {
                // Xử lý an toàn: Nếu data cũ là string (chỉ có mã), hiển thị mã và N/A số lượng
                // Nếu data mới là object {maCD, soLuong}, hiển thị đầy đủ
                const code = (typeof a === 'object' && a.maCD) ? a.maCD : a;
                const qty = (typeof a === 'object' && a.soLuong) ? a.soLuong : 'N/A';
                
                return `
                <tr>
                    <td class="fw-bold text-info">${code}</td>
                    <td class="text-end fw-bold">${qty}</td>
                </tr>`;
            }).join('');

            assetHtml = `
                <div class="mt-3 border-top pt-3">
                    <div class="mini-table-container" style="max-height: 200px; overflow-y: auto;">
                        <table class="table table-sm table-hover table-borderless mb-0">
                            <thead class="text-secondary sticky-top bg-white" style="font-size: 0.8rem; text-transform: uppercase;">
                                <tr>
                                    <th>Mã CD</th>
                                    <th class="text-end">Số Lượng (Lưu Ký)</th>
                                </tr>
                            </thead>
                            <tbody>${rows}</tbody>
                        </table>
                    </div>
                </div>
            `;
        }

        // 2. Render Giao diện
        containers.bank.innerHTML = `
            ${createCard('Tiền mặt User ', bank.tienMatUser, 'fas fa-user-lock', true, 'text-info', 'border-info')}
            
            ${createCard('Tiền mặt Finsight', bank.tienMatFinsight, 'fas fa-building-columns', true, 'text-secondary')}
            
            <div class="stat-card" style="grid-column: 1 / -1;">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <div class="stat-label"> CD User</div>
                        <div class="stat-value text-dark">${assetCount} <span class="fs-6 text-muted fw-normal">mã tài sản</span></div>
                    </div>
                    <i class="fas fa-file-contract stat-icon position-static text-dark opacity-25" style="font-size: 3rem;"></i>
                </div>
                
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
            alert((data.success ? "✅ " : "⚠️ ") + data.message);
            if(data.success) loadSystemData();
        } catch(e) {
            alert("Lỗi kết nối");
        } finally {
            loadingOverlay.style.display = 'none';
        }
        
    }

    document.getElementById("btnSettle")?.addEventListener("click", () => {
        const date = settleDateInput.value;
        if(confirm(`Chốt sổ ngày ${date}?`)) callApi("/system/api/settle", { date });
    });

    document.getElementById("btnAllocate")?.addEventListener("click", () => {
        const date = settleDateInput.value;
        if(confirm(`Chạy phân bổ CD ngày ${date}?`)) callApi("/system/api/allocate", { date, user_id: TEST_USER_ID });
    });

    document.getElementById("btnSyncBank")?.addEventListener("click", () => {
        if(confirm("Sync sang NHLK?")) callApi("/system/api/sync-bank", {});

    });

    // Init
    loadSystemData();
});