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

    // Set Default Date (Nếu chưa có giá trị)
    if (settleDateInput && !settleDateInput.value) settleDateInput.value = "2025-01-01";
    if (viewDateInput && !viewDateInput.value) viewDateInput.value = "2025-01-01";

    // --- 2. HELPERS (Khai báo trước để dùng ở dưới) ---
    const formatMoney = (val) => new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(val || 0);

   

    const createCard = (label, value, isMoney=false) => `
        <div class="stat-card">
            <div class="stat-label text-dark fw-bold">${label}</div>
            <div class="stat-value text-dark">${isMoney ? formatMoney(value) : value}</div>
        </div>`;

    // --- 3. EVENT LISTENERS ---
    
    // [QUAN TRỌNG] Trigger load sync data khi thay đổi View Date
    if (viewDateInput) {
        viewDateInput.addEventListener("change", () => {
            console.log("🔄 View Date changed to:", viewDateInput.value);
            // forceUpdateDate = true: Bắt buộc load theo ngày user chọn, bỏ qua logic tự động nhảy ngày
            loadSystemData(true); 
        });
    }

   

    // --- 4. MAIN LOGIC: LOAD DATA ---
    async function loadSystemData(forceUpdateDate = false) {
        if(loadingOverlay) loadingOverlay.style.display = 'flex';
        
        try {
            // Lấy ngày từ input (hoặc mặc định hôm nay)
            let vDate = viewDateInput ? viewDateInput.value : todayStr;
            
            console.log(`📡 Fetching data for date: ${vDate} (Force: ${forceUpdateDate})`);

            const res = await fetch(`/system3/api/overview?user_id=${TEST_USER_ID}&view_date=${vDate}`);
            const result = await res.json();

            if (res.ok && result.success) {
                const { user, bank, finsight, queue, history } = result.data;

                // --- LOGIC TỰ ĐỘNG CHỌN NGÀY THEO LỆNH NẠP (CASH_IN) ---
                if (queue && queue.length > 0) {
                    const sortedForDate = [...queue].sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
                    const cashInItem = sortedForDate.find(item => item.type === 'CASH_IN');

                    if (cashInItem) {
                        const cashInDateISO = toISODate(cashInItem.created_at);

                        // A. Luôn cập nhật ngày Phân bổ (Settle Date) theo lệnh nạp mới nhất
                        if (settleDateInput) settleDateInput.value = cashInDateISO;

                        // B. Logic cập nhật View Date
                        // Chỉ tự động chuyển View Date nếu user CHƯA chọn thủ công (forceUpdateDate = false)
                        if (viewDateInput && viewDateInput.value !== cashInDateISO && !forceUpdateDate) {
                            console.log(`🔀 Auto-switch ViewDate to ${cashInDateISO} (User hasn't manually changed yet)`);
                            viewDateInput.value = cashInDateISO;
                            
                            // Gọi đệ quy để load lại data đúng theo ngày nạp tiền
                            await loadSystemData(true); 
                            return; 
                        }

                        // Hiển thị thông báo
                        const elNotice = document.getElementById("allocationNotice");
                        const elNoticeText = document.getElementById("allocationNoticeText");
                        if (elNotice && elNoticeText) {
                            elNotice.style.display = "block";
                            elNoticeText.innerHTML = `Đã chọn ngày <b>${cashInDateISO.split('-').reverse().join('/')}</b> theo lệnh Nạp gần nhất.`;
                        }
                    }
                }

                // --- RENDER DỮ LIỆU ---
                renderUserWallet(user, history);
                renderSystemFund(finsight, result.data.total_balance_estimate);
                renderBank(bank);
                renderQueue(queue); 
                // renderDailyProfit(result.data.performance); // Nếu có hàm này
            }
        } catch (err) {
            console.error("❌ Error loading data:", err);
        } finally {
            if(loadingOverlay) loadingOverlay.style.display = 'none';
        }
    }

  
    // --- RENDER SECTIONS ---


    // 2. System Fund (4 Ô Vuông - All Black Text)
function renderSystemFund(sys, total_balance_estimate) {
    if (!sys) return;

    // --- 1. CHUẨN BỊ DỮ LIỆU ---
    const sysInventory = sys.inventory || [];
    const totalSysInvValue = sysInventory.reduce((sum, item) => sum + (item.giaTaiNgayXem * item.soLuong), 0);
    const totalUserAssetValue = total_balance_estimate || 0;
    
    // TÍNH TỔNG TÀI SẢN USER (Tiền mặt + Giá trị tài sản)
    const totalUserNetWorth = sys.user.cash + totalUserAssetValue;

    const invRows = sysInventory.map(item => `
        <tr>
            <td class="fw-bold text-dark" style="font-size: 0.85rem; padding: 10px 4px;">${item.maCD}</td>
            <td class="text-end text-dark" style="font-size: 0.85rem; padding: 10px 4px;">${new Intl.NumberFormat('en-US').format(item.soLuong)}</td>
            <td class="text-end text-dark" style="font-size: 0.8rem; padding: 10px 4px;">${formatMoney(item.giaTaiNgayXem)}</td>
        </tr>
    `).join('');

    let userRows = '';
    if (sys.user.assets && sys.user.assets.length > 0) {
        userRows = sys.user.assets.map(a => `
            <tr>
                <td class="fw-bold text-dark" style="font-size: 0.85rem;">${a.maCD}</td>
                <td class="text-end text-dark" style="font-size: 0.85rem;">${a.soLuong}</td>
            </tr>`).join('');
    }
    const userTableContent = userRows.length > 0 ? userRows : '<tr><td colspan="2" class="text-center small text-dark">Không có tài sản</td></tr>';


    // --- 2. TẠO HTML CÁC CARD ---

    // Nhóm 1: Finsight Core
    const cardFinsightCash = `
        <div class="stat-card">
            <div class="stat-label text-dark fw-bold">Tiền Finsight</div>
            <div class="stat-value text-dark">${formatMoney(sys.tienMatFinSight)}</div>
        </div>
    `;

    const cardFinsightAssets = `
        <div class="stat-card">
            <div class="stat-label text-dark fw-bold">Tài sản Finsight</div>
            <div class="stat-value text-dark">${formatMoney(totalSysInvValue)}</div>
            <div class="mt-3 pt-2 border-top" style="max-height: 140px; overflow-y: auto;">
                <table class="table table-borderless table-minimal mb-0 w-100">
                    <thead class="text-dark small border-bottom">
                        <tr><th>Mã</th><th class="text-end">SL</th><th class="text-end">Giá</th></tr>
                    </thead>
                    <tbody>${invRows.length > 0 ? invRows : '<tr><td colspan="3" class="text-center py-3">Kho trống</td></tr>'}</tbody>
                </table>
            </div>
        </div>
    `;

    // Nhóm 2: User Portfolio (Với thẻ TỔNG nằm trên)
    const cardUserTotal = `
        <div class="stat-card" style="grid-column: 1 / -1; background-color: #f8f9fa; border-bottom: 2px solid #dee2e6;">
            <div class="stat-label text-primary fw-bold text-uppercase" style="font-size: 0.75rem; letter-spacing: 0.5px;">Tổng tài sản User (Tiền + CD)</div>
            <div class="stat-value text-dark fw-bold" style="font-size: 1.6rem;">${formatMoney(totalUserNetWorth)}</div>
        </div>
    `;

    const cardUserCash = `
        <div class="stat-card">
            <div class="stat-label text-dark fw-bold">Tiền User</div>
            <div class="stat-value text-dark">${formatMoney(sys.user.cash)}</div>
        </div>
    `;

    const cardUserAssets = `
        <div class="stat-card">
            <div class="stat-label text-dark fw-bold">Tài sản User</div>
            <div class="stat-value text-dark">${formatMoney(totalUserAssetValue)}</div>
            <div class="mt-3 pt-2 border-top" style="max-height: 120px; overflow-y: auto;">
                <table class="table table-sm table-borderless table-minimal mb-0">
                    <thead class="text-dark small border-bottom">
                        <tr><th>Mã</th><th class="text-end">SL</th></tr>
                    </thead>
                    <tbody>${userTableContent}</tbody>
                </table>
            </div>
        </div>
    `;

    // --- 3. RENDER RA GIAO DIỆN ---
    containers.system.innerHTML = `
        ${cardFinsightCash}
        ${cardFinsightAssets}
        ${cardUserTotal}
        ${cardUserCash}
        ${cardUserAssets}
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

    // --- 0. SẮP XẾP ---
    if (queue && queue.length > 0) {
        queue.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
    }
    
    // Lọc danh sách trước khi render để code sạch hơn
    const filteredQueue = (queue || []).filter(item => item.type !== 'ALLOCATION_CASH_PAID');

    if (filteredQueue.length === 0) {
        container.innerHTML = `
            <div class="h-100 d-flex flex-column justify-content-center align-items-center text-muted opacity-50">
                <i class="fas fa-check-double fa-2x mb-2"></i>
                <small>Tất cả các lệnh cần xử lý đã được xử lý</small>
            </div>`;
        return; 
    }

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

    // --- STYLE DÙNG CHUNG CHO CÁC Ô ---
    // vertical-align: middle -> Căn giữa dọc
    // text-align: center -> Căn giữa ngang
    // padding: 16px -> Giãn cách rộng rãi
    const cellStyle = 'padding: 15px; vertical-align: middle; text-align: center;';

    // --- 1. SETUP TABLE STRUCTURE ---
    const tableStart = `
        <div class="table-responsive">
            <table class="table table-hover table-bordered mb-0" style="font-size: 0.9rem;">
                <thead class="bg-light text-dark fw-bold small text-uppercase">
                    <tr>
                        <th style="${cellStyle} width: 160px;">THỜI GIAN</th>
                        <th style="${cellStyle} width: 250px;">LỆNH</th>
                        <th style="${cellStyle} width: 250px;">CHI TIẾT</th>
                        <th style="${cellStyle} width: 150px;">SỐ TIỀN</th>
                    </tr>
                </thead>
                <tbody class="bg-white">
    `;

    // --- 2. BODY (ROWS) ---
    const rowsHtml = filteredQueue.map(item => {
        let displayType = item.type;
        let displayClass = 'bg-light';
        let detailHtml = '';

        const details = item.details || {};

        // CASE 1: BÁN CD
        if (item.type === 'LIQUIDATE_CD') {
            displayType = 'User bán CD'; 
            displayClass = 'q-liq'; 
            
            if (details.sold && Array.isArray(details.sold) && details.sold.length > 0) {
                const soldItems = details.sold.map(s => `<b>${s.soLuong}</b> x ${s.maCD}`).join(', ');
                // Thêm class text-center vào div con để chắc chắn nó cũng căn giữa
                detailHtml = `<div class="mt-1 text-muted small fst-italic text-center">${soldItems}</div>`;
            }
        } 
        
        // CASE 2: PHÂN BỔ
        else if (item.type === 'ALLOCATION_ASSET_DELIVERED') {
            displayType = 'User Mua CD'; 
            displayClass = 'q-alloc'; 
            
            const assetDetail = details.assets && details.assets.length > 0 ? details.assets[0] : null;
            
            if (assetDetail) {
                const maCD = assetDetail.maCD || "";
                const soLuong = assetDetail.soLuong || 0;
                
                if (maCD || soLuong) {
                    // Thêm class text-center
                    detailHtml = `<div class="mt-1 text-muted small fst-italic text-center">
                       ${soLuong} x ${maCD} 
                    </div>`;
                }
            }
        }

        // CASE 3: NẠP/RÚT
        else if (item.type === 'CASH_IN') {
            displayType = 'Nạp Tiền'; displayClass = 'q-cash-in';
        } else if (item.type === 'CASH_OUT') {
            displayType = 'Rút Tiền'; displayClass = 'q-cash-out';
        }
        else {
           return '';
        }

        const amountStr = item.amount > 0 ? formatMoney(item.amount) : '';
        const dateTimeDisplay = formatDateTime(item.created_at);
     
        // --- TRẢ VỀ DÒNG TR ---
        // Áp dụng cellStyle cho tất cả các ô td
        return `
            <tr>
                <td style="${cellStyle}">
                    ${dateTimeDisplay}
                </td>

                <td style="${cellStyle}">
                    <span class="q-badge ${displayClass}">${displayType}</span>
                </td>
                
                <td style="${cellStyle}">
                    ${detailHtml}
                </td>

                <td class="fw-bold text-dark" style="${cellStyle}">
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

    container.innerHTML = tableStart + rowsHtml + tableEnd;
}

   
    // 1. User Wallet & Profit Structure (Render khung HTML cho cả 2 thẻ)
function renderUserWallet(user, history) {
    if (!user) return;
    
    // Card 1: Số dư Ví (Dùng hàm createCard có sẵn)
    // Giả sử createCard trả về string HTML class="stat-card"
    const walletCardHtml = createCard('Số dư Ví', user.cash, true);

    // Card 2: Tiền lời hôm nay (Cấu trúc tương tự stat-card để thành ô vuông)
    const profitCardHtml = `
        <div class="stat-card">
            <div class="stat-label text-dark fw-bold">Tiền lời hôm nay</div>
            <div class="d-flex align-items-center h-100">
                <div class="stat-value text-success" id="pnl-value">${user.profit_today}</div>
            </div>
        </div>
    `;
    
    const historyRows = (history || []).map(item => {
    // 1. Định nghĩa cấu hình cho từng loại giao dịch (Dễ dàng thêm mới tại đây)
    const TYPE_CONFIG = {
        'NAP':     { label: 'Nạp tiền', cls: 'text-success', badge: 'bg-light text-success', sign: '+' },
        'RUT':     { label: 'Rút tiền', cls: 'text-danger',  badge: 'bg-light text-danger',  sign: '-' },
        'TIENLAI': { label: 'Tiền lãi', cls: 'text-success', badge: 'bg-light text-success', sign: '+' },
        'DEFAULT': { label: 'Giao dịch',  cls: 'text-muted',   badge: 'bg-light text-muted',   sign: ''  }
    };

    // 2. Lấy type hiện tại và đối chiếu cấu hình
    const typeKey = item.action_type || item.action;
    const cfg = TYPE_CONFIG[typeKey] || TYPE_CONFIG['DEFAULT'];


    return `
        <tr>
            <td class="small text-muted" style="text-align: center;
    vertical-align: middle; ">${item.date_trans}</td>
            <td style="text-align: center;
    vertical-align: middle;">
                <span class="badge ${cfg.badge}" >${cfg.label}</span>
            </td>
            <td class="${cfg.cls} fw-bold text-end" style="text-align: center;
    vertical-align: middle;">
                ${cfg.sign} ${formatMoney(item.amount)}
            </td>
        </tr>`;
   }).join('');
    const historyCardHtml = `
        <div class="stat-card" style="grid-column: 1 / -1; margin-top: 15px;">
            <div class="stat-label text-dark fw-bold mb-3">Lịch sử giao dịch</div>
            <div class="table-responsive" style="max-height: 300px; overflow-y: auto;">
                <table class="table table-sm table-hover  mb-0" style="width : 450px;table-layout: fixed;">
                    <thead class="sticky-top bg-white">
                        <tr class="small text-muted">
                            <th>NGÀY</th><th>LOẠI</th><th class="text-end">SỐ TIỀN</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${historyRows || '<tr><td colspan="3" class="text-center py-3 text-muted">Chưa có giao dịch</td></tr>'}
                    </tbody>
                </table>
            </div>
        </div>`;

    // Đẩy vào container
    containers.user.innerHTML = walletCardHtml + profitCardHtml + historyCardHtml;
}

// 2. Daily Profit Logic (Update dữ liệu vào ô vuông thứ 2)
function renderDailyProfit(perfData) {
    // 1. Lấy Element (Đã được tạo ra bởi hàm renderUserWallet ở trên)
    const pnlValueEl = document.getElementById('pnl-value');

    // Guard clause: Nếu chưa render HTML thì dừng
    if (!pnlValueEl) return;

    // 2. Xử lý dữ liệu an toàn
    const profit = (perfData && perfData.profit_today) ? perfData.profit_today : 0;
    
    // 3. Logic hiển thị (Màu sắc & Dấu)
    const isZero = profit === 0;

    // Mặc định là màu xanh lá (text-success) như yêu cầu
    let colorClass = 'text-success'; 
    let barColor = '#10b981'; // Xanh
    let sign = '+';

    if (profit < 0) {
        colorClass = 'text-danger'; // Lỗ thì vẫn nên đỏ để cảnh báo
        barColor = '#ef4444'; // Đỏ
        sign = ''; // Số âm tự có dấu trừ
    } else if (isZero) {
        colorClass = 'text-success'; // 0 đồng cũng cho xanh theo ý bạn (hoặc text-muted nếu muốn xám)
        barColor = '#10b981';
        sign = '';
    }

    // 4. Update UI
    // Reset class cũ và gán class mới
    pnlValueEl.className = `stat-value ${colorClass}`;
    
    // Format tiền
    pnlValueEl.innerText = `${sign}${formatMoney(profit)}`; 
    
   
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
   document.getElementById("btnSyncDiff")?.addEventListener("click", () => {
    const elInput = document.getElementById("settleDateInput");
    const selectedDate = elInput.value;

    if (!selectedDate) {
        alert("Vui lòng chọn ngày sync!");
        return;
    }

    // Format ngày hiển thị trong confirm cho đẹp (dd/mm/yyyy)
    const dateDisplay = selectedDate.split('-').reverse().join('/');

    if(confirm(`Xác nhận sync chênh lệch cho ngày: ${dateDisplay}?`)) {
        callApi("/system3/api/syncDiff", { 
            date: selectedDate, // Giá trị này đã chuẩn logic T0 hoặc do User chỉnh
            user_id: TEST_USER_ID 
        });
    }
});
    document.getElementById("btnSyncBank")?.addEventListener("click", () => {
        if(confirm("Xác nhận Đồng bộ sang NHLK?")) callApi("/system3/api/sync-bank", {});
    });

    document.getElementById("btnResetData")?.addEventListener("click", async () => {
        // Cảnh báo 2 lớp để tránh bấm nhầm
        if (!confirm("⚠️ NGUY HIỂM: Bạn có chắc chắn muốn XÓA TOÀN BỘ dữ liệu (Ngoại trừ thông tin CD)?")) return;
        if (!confirm("Xác nhận lần cuối: Hành động này không thể hoàn tác. Mọi tài khoản, giao dịch sẽ mất tại Ví User, CoreTVAM và NHLK.")) return;

        await callApi("/system3/api/reset", {});
        
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