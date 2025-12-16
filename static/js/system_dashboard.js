
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

    // Date 
    const defaultDateISO = "2025-01-01"; 

    const settleDateInput = document.getElementById("settleDate");
    const viewDateInput = document.getElementById("viewDate");
    const todayStr = new Date().toISOString().split('T')[0];
    if (settleDateInput) {
            settleDateInput.value = defaultDateISO;
            }
    if (viewDateInput) {
        viewDateInput.value = defaultDateISO;
            }
    
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
                renderDailyProfit(result.data.performance);
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

    // --- 0. SẮP XẾP: Cũ nhất lên đầu ---
    if (queue && queue.length > 0) {
        queue.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
    }
    const filteredQueue = (queue || []).filter(item => 
        item.type !== 'ALLOCATION_CASH_PAID' // Loại bỏ lệnh Cash Paid
    );
    if (filteredQueue.length === 0) {
        container.innerHTML = `
            <div class="h-100 d-flex flex-column justify-content-center align-items-center text-muted opacity-50">
                <i class="fas fa-check-double fa-2x mb-2"></i>
                <small>Tất cả các lệnh cần xử lý đã được xử lý</small>
            </div>`;
        // ... (cập nhật badge, nút Sync nếu cần) ...
        return; 
    }

    // Helper: Format DateTime
    const formatDateTime = (dateStr) => {
        if (!dateStr) return "";
        const d = new Date(dateStr);
        if (isNaN(d.getTime())) return "";
        const dd = String(d.getDate()).padStart(2, '0');
        const mm = String(d.getMonth() + 1).padStart(2, '0');
        const yyyy = d.getFullYear();
        const HH = String(d.getHours()).padStart(2, '0');
        const MM = String(d.getMinutes()).padStart(2, '0');
        const SS = String(d.getSeconds()).padStart(2, '0');
        return `${dd}/${mm}/${yyyy} ${HH}:${MM}:${SS}`;
    };



    // --- 1. SETUP TABLE STRUCTURE ---
    // Tạo khung bảng và Header (thead)
    // align-middle: Căn giữa theo chiều dọc cho tất cả các ô
    const tableStart = `
        <div class="table-responsive">
            <table class="table table-hover table-bordered mb-0" style="font-size: 0.9rem;">
                <thead class="bg-light text-dark fw-bold small text-uppercase">
                    <tr>
                        <th  class="align-middle text-center" style="width: 150px;">THỜI GIAN</th>
                        <th class="align-middle text-center" style="width: 150px;">LOẠI LỆNH</th>
                        <th class="align-middle text-center" style="width: 100px;">CHI TIẾT</th>
                        <th  class="align-middle text-center" style="width: 120px;">SỐ TIỀN</th>
                      
                    </tr>
                </thead>
                <tbody class="bg-white">
    `;

    // --- 2. BODY (ROWS) ---
    const rowsHtml = queue.map(item => {
        let displayType = item.type;
        let displayClass = 'bg-light';
        let detailHtml = '';

        const details = item.details || {};

        // --- XỬ LÝ LOGIC HIỂN THỊ (Giữ nguyên logic của bạn) ---

        // CASE 1: BÁN CD
        if (item.type === 'LIQUIDATE_CD') {
            displayType = 'User bán CD'; 
            displayClass = 'q-liq'; 
           
            
            if (details.sold && Array.isArray(details.sold) && details.sold.length > 0) {
                const soldItems = details.sold.map(s => `<b>${s.soLuong}</b> x ${s.maCD}`).join(', ');
                detailHtml = `<div class="mt-1 text-muted small fst-italic">${soldItems}</div>`;
            }
        } 
        
        // CASE 2: PHÂN BỔ
        else if (item.type === 'ALLOCATION_ASSET_DELIVERED') {
            displayType = 'User Mua CD'; 
            displayClass = 'q-alloc'; 
            displayIcon = '📦';
            
            // --- FIX: Truy cập vào phần tử [0] của mảng 'assets' ---
            const assetDetail = details.assets && details.assets.length > 0 ? details.assets[0] : null;
            
            if (assetDetail) {
                // Lấy Mã CD và Số lượng từ phần tử đầu tiên
                const maCD = assetDetail.maCD || "";
                const soLuong = assetDetail.soLuong || 0;
                
                // Xây dựng chuỗi chi tiết
                if (maCD || soLuong) {
                    // Ví dụ: ID003 (SL: 5)
                    detailHtml = `<div class="mt-1 text-muted small fst-italic">
                       ${soLuong} x ${maCD} 
                    </div>`;
                }
            }
        }

        // CASE 3: NẠP/RÚT
        else if (item.type === 'CASH_IN') {
            displayType = 'Nạp Tiền'; displayClass = 'q-cash-in'; displayIcon = '+';
        } else if (item.type === 'CASH_OUT') {
            displayType = 'Rút Tiền'; displayClass = 'q-cash-out'; displayIcon = '-';
        }
        else 
        {
           return '';
        }

        const amountStr = item.amount > 0 ? formatMoney(item.amount) : '';
        const dateTimeDisplay = formatDateTime(item.created_at);
     

        // --- TRẢ VỀ DÒNG TR ---
        return `
            <tr>
                <td class="align-middle text-center">
                    ${dateTimeDisplay}
                </td>

                <td class="align-middle text-center">
                    <span class="q-badge ${displayClass}">${displayType}</span>
                  
                </td>
                <td class="align-middle text-center">
                    <span >  ${detailHtml}</span>
                  
                </td>

                <td class="align-middle text-center">
                    ${amountStr}
                </td>

               
            </tr>
        `;
    }).join('');

    const tableEnd = `
                </tbody>
            </table>
        </div>
    `;

    // Ghép chuỗi HTML
    container.innerHTML = tableStart + rowsHtml + tableEnd;

}


    function renderDailyProfit(perfData) {
        // 1. Lấy Element
        const pnlValueEl = document.getElementById('pnl-value');
        const pnlTimeEl = document.getElementById('pnl-time');
        const pnlBarEl = document.getElementById('pnl-bar');

        // Guard clause: Nếu không có HTML thì dừng
        if (!pnlValueEl) return;

        // 2. Xử lý dữ liệu an toàn
        const profit = (perfData && perfData.profit_today) ? perfData.profit_today : 0;
        const lastUpdated = (perfData && perfData.last_updated) ? perfData.last_updated : '--:--';

        // 3. Logic hiển thị (Màu sắc & Dấu)
        const isPositive = profit >= 0;
        const isZero = profit === 0;

        // Xác định class màu
        let colorClass = 'text-success'; 
        let barColor = '#10b981'; // Xanh
        let sign = '+';

        if (profit < 0) {
            colorClass = 'text-danger';
            barColor = '#ef4444'; // Đỏ
            sign = ''; // Số âm tự có dấu trừ (formatMoney sẽ tự thêm)
        } else if (isZero) {
            colorClass = 'text-muted'; // Màu xám
            barColor = '#e9ecef';
            sign = '';
        }

        // 4. Update UI
        // Reset class cũ và gán class mới
        pnlValueEl.className = `display-6 fw-bold mb-0 ${colorClass}`;
        
        // [SỬA LỖI TẠI ĐÂY] Đổi formatCurrencyVND thành formatMoney
        // formatMoney là hàm bạn đã khai báo ở đầu file js
        pnlValueEl.innerText = `${sign}${formatMoney(profit)}`; 
        
        // Update giờ và thanh màu dưới đáy
        if (pnlTimeEl) pnlTimeEl.innerText = lastUpdated;
        if (pnlBarEl) pnlBarEl.style.backgroundColor = barColor;
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
    // Hàm này được gọi khi bấm nút "Gửi lệnh Lưu ký"
function prepareSyncData(queue) {
    const elNotice = document.getElementById("allocationNotice");
    const elNoticeText = document.getElementById("allocationNoticeText");
    const elDateInput = document.getElementById("allocationDate");
    
    // 1. Tìm lệnh NẠP TIỀN (CASH_IN) trong queue
    // (Giả sử queue đã được sort cũ nhất lên đầu)
    const cashInItem = queue.find(item => item.type === 'CASH_IN');
    
    // Helper: Chuyển Date object thành chuỗi YYYY-MM-DD cho input type="date"
    const toISODate = (d) => {
        const yyyy = d.getFullYear();
        const mm = String(d.getMonth() + 1).padStart(2, '0');
        const dd = String(d.getDate()).padStart(2, '0');
        return `${yyyy}-${mm}-${dd}`;
    };

    // Helper: Format hiển thị kiểu dd/mm/yyyy cho đẹp
    const toReadableDate = (d) => {
        return `${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}/${d.getFullYear()}`;
    };

    let targetDate = new Date(); // Mặc định là hôm nay nếu không tìm thấy
    let hasCashIn = false;

    if (cashInItem && cashInItem.created_at) {
        // Lấy ngày từ lệnh CASH_IN
        targetDate = new Date(cashInItem.created_at);
        hasCashIn = true;
    }

    // 2. Set giá trị mặc định cho Input
    if (elDateInput) {
        elDateInput.value = toISODate(targetDate);
    }

    // 3. Hiển thị Notice thông minh
    if (elNotice && elNoticeText) {
        if (hasCashIn) {
            elNotice.style.display = "flex";
            elNotice.className = "alert alert-primary d-flex align-items-start small mb-3"; // Màu xanh dương
            elNoticeText.innerHTML = `
                <strong>Cơ chế T+0 kích hoạt:</strong><br>
                Ngày phân bổ đã được tự động set về <b>${toReadableDate(targetDate)}</b> 
                theo ngày lệnh Nạp tiền của User.
            `;
        } else {
            // Trường hợp không có lệnh Nạp (ví dụ chỉ có Rút hoặc Bán CD)
            // Có thể ẩn notice hoặc hiện cảnh báo khác
            elNotice.style.display = "none";
            
            // Hoặc giữ mặc định là hôm nay
        }
    }
}
// Hàm helper chuyển Date sang chuỗi YYYY-MM-DD cho input date
const toISODate = (d) => {
    const date = new Date(d);
    const yyyy = date.getFullYear();
    const mm = String(date.getMonth() + 1).padStart(2, '0');
    const dd = String(date.getDate()).padStart(2, '0');
    return `${yyyy}-${mm}-${dd}`;
};

// Hàm xử lý logic T0
function handleT0Rule(queue) {
    const elInput = document.getElementById("settleDateInput");
    const elNotice = document.getElementById("allocationNotice");
    const elNoticeText = document.getElementById("allocationNoticeText");

    if (!elInput) return;

    // 1. Tìm lệnh NẠP TIỀN (CASH_IN) đầu tiên trong queue (Queue đã sort cũ nhất lên đầu)
    const cashInItem = queue.find(item => item.type === 'CASH_IN');

    if (cashInItem) {
        // [CASE 1] Có lệnh nạp -> Lấy ngày của lệnh đó (T0 của lệnh)
        const t0Date = cashInItem.created_at; 
        
        // Auto-fill vào Input
        elInput.value = toISODate(t0Date);

        // Hiện Notice
        if (elNotice && elNoticeText) {
            elNotice.style.display = "block";
            elNoticeText.innerHTML = `Hệ thống tự động chọn ngày <b>${toISODate(t0Date)}</b> theo lệnh Nạp tiền mới nhất (T+0).`;
        }
    } else {
        // [CASE 2] Không có lệnh nạp -> Mặc định là Hôm nay
        const today = new Date();
        elInput.value = toISODate(today);

        // Ẩn Notice (hoặc hiện thông báo mặc định khác tùy bạn)
        if (elNotice) elNotice.style.display = "none";
    }
}

    document.getElementById("btnAllocate")?.addEventListener("click", () => {
    const elInput = document.getElementById("settleDateInput");
    const selectedDate = elInput.value;

    if (!selectedDate) {
        alert("Vui lòng chọn ngày phân bổ!");
        return;
    }

    // Format ngày hiển thị trong confirm cho đẹp (dd/mm/yyyy)
    const dateDisplay = selectedDate.split('-').reverse().join('/');

    if(confirm(`Xác nhận Phân Bổ CD cho ngày: ${dateDisplay}?`)) {
        callApi("/system/api/allocate", { 
            date: selectedDate, // Giá trị này đã chuẩn logic T0 hoặc do User chỉnh
            user_id: TEST_USER_ID 
        });
    }
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