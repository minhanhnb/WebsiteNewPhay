
document.addEventListener("DOMContentLoaded", () => {
    // --- 1. CONFIG & ELEMENTS ---
    const TEST_USER_ID = "user_default";
    const loadingOverlay = document.getElementById("loading-overlay");

    const containers = {
        user: document.getElementById('user-data-container'),
        system: document.getElementById('finsight-data-container'),
        bank: document.getElementById('bank-data-container'),
        queue: document.getElementById("queueContainer"),
    };
 
    // Inputs
    const settleDateInput = document.getElementById("settleDateInput") || document.getElementById("settleDate");
    const viewDateInput = document.getElementById("viewDate");
    const todayStr = new Date().toISOString().split('T')[0];

    // Set Default Date
    if (settleDateInput && !settleDateInput.value) settleDateInput.value = "2025-01-01";
    if (viewDateInput && !viewDateInput.value) viewDateInput.value = "2025-01-01";

    // --- 2. UX HELPERS (TOAST & LOADING) ---
    
    // Tạo Toast Container nếu chưa có
    if (!document.getElementById('toast-container')) {
        const toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        toastContainer.style.cssText = "position: fixed; top: 20px; right: 20px; z-index: 9999;";
        document.body.appendChild(toastContainer);
    }

    // Hàm hiển thị thông báo đẹp thay cho alert
    const showToast = (message, type = 'success') => {
        const toast = document.createElement('div');
        const bg = type === 'success' ? '#10b981' : '#ef4444';
        const icon = type === 'success' ? '✅' : '❌';
        
        toast.style.cssText = `
            background-color: ${bg}; color: white; padding: 12px 20px; 
            margin-bottom: 10px; border-radius: 6px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            display: flex; align-items: center; gap: 10px; font-weight: 500;
            opacity: 0; transform: translateY(-20px); transition: all 0.3s ease;
            min-width: 300px;
        `;
        toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
        
        document.getElementById('toast-container').appendChild(toast);
        
        // Animation in
        requestAnimationFrame(() => {
            toast.style.opacity = '1';
            toast.style.transform = 'translateY(0)';
        });

        // Auto hide
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(-20px)';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    };

    const toggleLoading = (show) => {
        if(loadingOverlay) loadingOverlay.style.display = show ? 'flex' : 'none';
    };

    const formatMoney = (val) => new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(val || 0);

    const createCard = (label, value, isMoney=false) => `
        <div class="stat-card">
            <div class="stat-label text-dark fw-bold">${label}</div>
            <div class="stat-value text-dark">${isMoney ? formatMoney(value) : value}</div>
        </div>`;

    // --- 3. CORE API LOGIC (AJAX & SEQUENTIAL) ---

    /**
     * Hàm gọi API chuẩn hóa UX:
     * 1. Hiện Loading
     * 2. Gọi API xử lý logic (Sync, Allocate...)
     * 3. Chờ xong -> Gọi tiếp Load Data (Refetch)
     * 4. Render xong data mới -> Hiện thông báo Success -> Tắt Loading
     */
    async function callApi(url, body, successMessage) {
        toggleLoading(true);
        try {
            // Bước 1: Gọi API xử lý
            const res = await fetch(url, {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify(body)
            });
            const data = await res.json();

            if (!res.ok || !data.success) {
                throw new Error(data.message || "Có lỗi xảy ra");
            }

            // Bước 2: Reload dữ liệu mới nhất (Chờ render xong mới đi tiếp)
            // Truyền true để force load theo ngày hiện tại user đang chọn
            await loadSystemData(true, true); 

            // Bước 3: Hiển thị thông báo thành công
            showToast(successMessage || data.message || "Thao tác thành công", 'success');

        } catch(e) {
            console.error(e);
            showToast(e.message || "Lỗi kết nối server", 'error');
        } finally {
            // Bước 4: Tắt loading
            toggleLoading(false);
        }
    }

    // --- 4. MAIN LOGIC: LOAD DATA ---
    // skipLoadingUI: Nếu gọi từ callApi thì không cần hiện/ẩn loading riêng lẻ nữa vì callApi đã bao bọc rồi
    async function loadSystemData(forceUpdateDate = false, skipLoadingUI = false) {
        if(!skipLoadingUI) toggleLoading(true);
        
        try {
            let vDate = viewDateInput ? viewDateInput.value : todayStr;
            console.log(`📡 Fetching data for date: ${vDate} (Force: ${forceUpdateDate})`);

            const res = await fetch(`/system2/api/overview?user_id=${TEST_USER_ID}&view_date=${vDate}`);
            const result = await res.json();

            if (res.ok && result.success) {
                const { user, bank, finsight, queue, history } = result.data;

                // --- LOGIC TỰ ĐỘNG CHỌN NGÀY ---
                if (queue && queue.length > 0) {
                    const sortedForDate = [...queue].sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
                    const cashInItem = sortedForDate.find(item => item.type === 'CASH_IN');

                    if (cashInItem) {
                        const cashInDateISO = toISODate(cashInItem.created_at);

                        // A. Luôn cập nhật ngày Phân bổ
                        if (settleDateInput) settleDateInput.value = cashInDateISO;

                        // B. Logic cập nhật View Date (đệ quy)
                        if (viewDateInput && viewDateInput.value !== cashInDateISO && !forceUpdateDate) {
                            console.log(`🔀 Auto-switch ViewDate to ${cashInDateISO}`);
                            viewDateInput.value = cashInDateISO;
                            // Gọi lại chính nó và return luôn để tránh render dữ liệu cũ
                            await loadSystemData(true, skipLoadingUI); 
                            return; 
                        }
                        
                        // Hiển thị Notice
                        updateAllocationNotice(cashInDateISO);
                    }
                }

                // --- RENDER DỮ LIỆU ---
                renderUserWallet(user, history);
                renderSystemFund(finsight, result.data.total_balance_estimate);
                renderBank(bank);
                renderQueue(queue); 
            }
        } catch (err) {
            console.error("❌ Error loading data:", err);
            if(!skipLoadingUI) showToast("Không thể tải dữ liệu", 'error');
        } finally {
            if(!skipLoadingUI) toggleLoading(false);
        }
    }

    // --- 5. RENDER FUNCTIONS (GIỮ NGUYÊN LOGIC HIỂN THỊ) ---
    
    function renderSystemFund(sys, total_balance_estimate) {
        if (!sys) return;
        const sysInventory = sys.inventory || [];
        const totalSysInvValue = sysInventory.reduce((sum, item) => sum + (item.giaTaiNgayXem * item.soLuong), 0);
        const totalUserAssetValue = total_balance_estimate || 0;
        const totalUserNetWorth = sys.user.cash + totalUserAssetValue;

        const invRows = sysInventory.map(item => `
            <tr>
                <td class="fw-bold text-dark" style="font-size: 0.85rem; padding: 10px 4px;">${item.maCD}</td>
                <td class="text-end text-dark" style="font-size: 0.85rem; padding: 10px 4px;">${new Intl.NumberFormat('en-US').format(item.soLuong)}</td>
                <td class="text-end text-dark" style="font-size: 0.8rem; padding: 10px 4px;">${formatMoney(item.giaTaiNgayXem)}</td>
            </tr>`).join('');

        let userRows = '';
        if (sys.user.assets && sys.user.assets.length > 0) {
            userRows = sys.user.assets.map(a => `
                <tr>
                    <td class="fw-bold text-dark" style="font-size: 0.85rem;">${a.maCD}</td>
                    <td class="text-end text-dark" style="font-size: 0.85rem;">${a.soLuong}</td>
                </tr>`).join('');
        }
        const userTableContent = userRows.length > 0 ? userRows : '<tr><td colspan="2" class="text-center small text-dark">Không có tài sản</td></tr>';

        const cardFinsightCash = createCard('Tiền Finsight', sys.tienMatFinSight, true);
        const cardFinsightAssets = `
            <div class="stat-card">
                <div class="stat-label text-dark fw-bold">Tài sản Finsight</div>
                <div class="stat-value text-dark">${formatMoney(totalSysInvValue)}</div>
                <div class="mt-3 pt-2 border-top" style="max-height: 140px; overflow-y: auto;">
                    <table class="table table-borderless table-minimal mb-0 w-100">
                        <thead class="text-dark small border-bottom"><tr><th>Mã</th><th class="text-end">SL</th><th class="text-end">Giá</th></tr></thead>
                        <tbody>${invRows.length > 0 ? invRows : '<tr><td colspan="3" class="text-center py-3">Kho trống</td></tr>'}</tbody>
                    </table>
                </div>
            </div>`;

        const cardUserTotal = `
            <div class="stat-card" style="grid-column: 1 / -1; background-color: #f8f9fa; border-bottom: 2px solid #dee2e6;">
                <div class="stat-label text-primary fw-bold text-uppercase" style="font-size: 0.75rem; letter-spacing: 0.5px;">Tổng tài sản User (Tiền + CD)</div>
                <div class="stat-value text-dark fw-bold" style="font-size: 1.6rem;">${formatMoney(totalUserNetWorth)}</div>
            </div>`;

        const cardUserCash = createCard('Tiền User', sys.user.cash, true);
        const cardUserAssets = `
            <div class="stat-card">
                <div class="stat-label text-dark fw-bold">Tài sản User</div>
                <div class="stat-value text-dark">${formatMoney(totalUserAssetValue)}</div>
                <div class="mt-3 pt-2 border-top" style="max-height: 120px; overflow-y: auto;">
                    <table class="table table-sm table-borderless table-minimal mb-0">
                        <thead class="text-dark small border-bottom"><tr><th>Mã</th><th class="text-end">SL</th></tr></thead>
                        <tbody>${userTableContent}</tbody>
                    </table>
                </div>
            </div>`;

        containers.system.innerHTML = `${cardFinsightCash}${cardFinsightAssets}${cardUserTotal}${cardUserCash}${cardUserAssets}`;
    }

    function renderBank(bank) {
        if (!bank) return;
        const assetList = bank.taiSanUser || [];
        const rows = assetList.length > 0 ? assetList.map(a => `<tr><td>${a.maCD}</td><td class="text-end">${a.soLuong}</td></tr>`).join('') : '';
        const assetHtml = assetList.length > 0 
            ? `<div class="mt-3 pt-2 border-top"><div class="stat-label mb-2">Danh mục Lưu Ký</div><div style="max-height: 150px; overflow-y: auto;"><table class="table table-sm table-borderless table-minimal mb-0"><thead><tr><th>Mã</th><th class="text-end">SL</th></tr></thead><tbody>${rows}</tbody></table></div></div>`
            : '<div class="mt-3 pt-2 border-top small text-muted">Chưa lưu ký</div>';

        containers.bank.innerHTML = `
            ${createCard('Tiền Finsight', bank.tienMatFinsight, true)}
            ${createCard('Tiền User', bank.tienMatUser, true)}
            <div class="stat-card" style="grid-column: 1 / -1;">
                <div class="stat-label">Tài sản User</div>
                <div class="stat-value">${assetList.length} <span style="font-size: 1rem; font-weight: 400; color: #999;">mã</span></div>
                ${assetHtml}
            </div>`;
    }

    function renderQueue(queue) {
        // (Giữ nguyên logic render queue của bạn, tôi rút gọn để tập trung vào logic sync)
        const container = document.getElementById("queueContainer");
        if (queue && queue.length > 0) {
    queue.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
}
        const filteredQueue = (queue || []).filter(item => item.type !== 'ALLOCATION_CASH_PAID');

        if (filteredQueue.length === 0) {
            container.innerHTML = `<div class="h-100 d-flex flex-column justify-content-center align-items-center text-muted opacity-50"><i class="fas fa-check-double fa-2x mb-2"></i><small>Tất cả các lệnh cần xử lý đã được xử lý</small></div>`;
            return; 
        }

        const formatDateTime = (dateStr) => {
            const d = new Date(dateStr);
            return isNaN(d) ? "" : `${String(d.getDate()).padStart(2,'0')}/${String(d.getMonth()+1).padStart(2,'0')}/${d.getFullYear()} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`;
        };
        const cellStyle = 'padding: 15px; vertical-align: middle; text-align: center;';
        
        const rowsHtml = filteredQueue.map(item => {
            let displayType = item.type;
            let displayClass = 'bg-light';
            let detailHtml = '';
            const details = item.details || {};

            if (item.type === 'LIQUIDATE_CD') { displayType = 'User bán CD'; displayClass = 'q-liq'; 
                if (details.sold) detailHtml = `<div class="mt-1 text-muted small fst-italic text-center">${details.sold.map(s => `<b>${s.soLuong}</b> x ${s.giaCD} (${s.maCD})`).join(', ')}</div>`;
            } else if (item.type === 'ALLOCATION_ASSET_DELIVERED') { displayType = 'User mua CD'; displayClass = 'q-alloc'; 
                const asset = details.assets?.[0];
                if (asset) detailHtml = `<div class="mt-1 text-muted small fst-italic text-center">${asset.soLuong} x ${asset.giaVon} (${asset.maCD})</div>`;
            } else if (item.type === 'CASH_IN') { displayType = 'Tăng vốn'; displayClass = 'q-cash-in'; }
            else if (item.type === 'CASH_OUT') { displayType = 'Giảm vốn'; displayClass = 'q-cash-out'; }
            else return '';

            return `<tr><td style="${cellStyle}">${formatDateTime(item.created_at)}</td><td style="${cellStyle}"><span class="q-badge ${displayClass}">${displayType}</span></td><td style="${cellStyle}">${detailHtml}</td><td class="fw-bold text-dark" style="${cellStyle}">${item.amount > 0 ? formatMoney(item.amount) : ''}</td></tr>`;
        }).join('');

        container.innerHTML = `<div class="table-responsive"><table class="table table-hover table-bordered mb-0" style="font-size: 0.9rem;"><thead class="bg-light text-dark fw-bold small text-uppercase"><tr><th style="${cellStyle} width: 160px;">THỜI GIAN</th><th style="${cellStyle} width: 250px;">LỆNH</th><th style="${cellStyle} width: 250px;">CHI TIẾT</th><th style="${cellStyle} width: 150px;">SỐ TIỀN</th></tr></thead><tbody class="bg-white">${rowsHtml}</tbody></table></div>`;
    }

    function renderUserWallet(user, history) {
        if (!user) return;
        const walletCardHtml = createCard('Số dư Ví', user.cash, true);
        
        // Tính lãi hôm nay từ user.profit_today (đã được tính từ backend)
        const profit = user.profit_today || 0;
        const colorClass = profit < 0 ? 'text-danger' : 'text-success';
        const sign = profit > 0 ? '+' : '';
        const profitCardHtml = `
            <div class="stat-card">
                <div class="stat-label text-dark fw-bold">Tiền lời hôm nay</div>
                <div class="d-flex align-items-center h-100">
                    <div class="stat-value ${colorClass}" id="pnl-value">${sign}${formatMoney(profit)}</div>
                </div>
            </div>`;

        const historyRows = (history || []).map(item => {
            const TYPE_CONFIG = {
                'NAP': { label: 'Nạp tiền', badge: 'bg-light text-success', sign: '+', cls: 'text-success' },
                'RUT': { label: 'Rút tiền', badge: 'bg-light text-danger', sign: '-', cls: 'text-danger' },
                'TIENLAI': { label: 'Tiền lãi', badge: 'bg-light text-success', sign: '+', cls: 'text-success' },
                'DEFAULT': { label: 'Giao dịch', badge: 'bg-light text-muted', sign: '', cls: 'text-muted' }
            };
            const cfg = TYPE_CONFIG[item.action_type || item.action] || TYPE_CONFIG['DEFAULT'];
            return `<tr><td class="small text-muted" style="text-align:center; vertical-align:middle;">${item.date_trans}</td><td style="text-align:center; vertical-align:middle;"><span class="badge ${cfg.badge}">${cfg.label}</span></td><td class="${cfg.cls} fw-bold text-end" style="text-align:center; vertical-align:middle;">${cfg.sign} ${formatMoney(item.amount)}</td></tr>`;
        }).join('');

        containers.user.innerHTML = walletCardHtml + profitCardHtml + `<div class="stat-card" style="grid-column: 1 / -1; margin-top: 15px;"><div class="stat-label text-dark fw-bold mb-3">Lịch sử giao dịch</div><div class="table-responsive" style="max-height: 300px; overflow-y: auto;"><table class="table table-sm table-hover mb-0" style="width:450px; table-layout:fixed;"><thead class="sticky-top bg-white"><tr class="small text-muted"><th>NGÀY</th><th>LOẠI</th><th class="text-end">SỐ TIỀN</th></tr></thead><tbody>${historyRows || '<tr><td colspan="3" class="text-center">Chưa có giao dịch</td></tr>'}</tbody></table></div></div>`;
    }

    // --- 6. EVENT LISTENERS ---

    if (viewDateInput) {
        viewDateInput.addEventListener("change", () => {
            console.log("🔄 View Date changed to:", viewDateInput.value);
            loadSystemData(true); 
        });
    }

    // Button Actions - Sử dụng callApi MỚI
    document.getElementById("btnAllocate")?.addEventListener("click", () => {
        const selectedDate = settleDateInput.value;
        if (!selectedDate) return showToast("Vui lòng chọn ngày phân bổ!", 'error');
        
        const dateDisplay = selectedDate.split('-').reverse().join('/');
        if(confirm(`Xác nhận Phân Bổ CD cho ngày: ${dateDisplay}?`)) {
            callApi("/system/api/allocate", { date: selectedDate, user_id: TEST_USER_ID }, "Phân bổ thành công");
        }
    });

    document.getElementById("btnSyncDiff")?.addEventListener("click", () => {
        const selectedDate = settleDateInput.value;
        if (!selectedDate) return showToast("Vui lòng chọn ngày sync!", 'error');

        const dateDisplay = selectedDate.split('-').reverse().join('/');
        if(confirm(`Xác nhận sync chênh lệch cho ngày: ${dateDisplay}?`)) {
            callApi("/system2/api/sync-all", { date: selectedDate, user_id: TEST_USER_ID }, "Đồng bộ chênh lệch thành công");
        }
    });

    document.getElementById("btnSyncBank")?.addEventListener("click", () => {
        if(confirm("Xác nhận Đồng bộ sang NHLK?")) {
            callApi("/system2/api/sync-bank", {}, "Đồng bộ NHLK thành công");
        }
    });

    document.getElementById("btnResetData")?.addEventListener("click", async () => {
        if (!confirm("⚠️ NGUY HIỂM: XÓA TOÀN BỘ dữ liệu?")) return;
        if (!confirm("Xác nhận lần cuối: Hành động này không thể hoàn tác.")) return;

        // Reset thì reload trang là hợp lý nhất
        toggleLoading(true);
        try {
            const res = await fetch("/system2/api/reset", {method: "POST"});
            const data = await res.json();
            if(data.success) window.location.reload();
            else showToast(data.message, 'error');
        } catch(e) {
            showToast("Lỗi kết nối", 'error');
            toggleLoading(false);
        }
    });

    // --- UTILS ---
    const toISODate = (d) => {
        const date = new Date(d);
        return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
    };

    function updateAllocationNotice(dateISO) {
        const elNotice = document.getElementById("allocationNotice");
        const elNoticeText = document.getElementById("allocationNoticeText");
        if (elNotice && elNoticeText) {
            elNotice.style.display = "block";
            elNoticeText.innerHTML = `Đã chọn ngày <b>${dateISO.split('-').reverse().join('/')}</b> theo lệnh Nạp gần nhất.`;
        }
    }

    // Init
    loadSystemData();
});