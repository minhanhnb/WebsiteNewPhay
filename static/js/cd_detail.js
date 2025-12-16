document.addEventListener("DOMContentLoaded", async () => {
    // --- STATE MANAGEMENT ---
    let cdData = null;
    let myChart = null;

    // Elements
    const maDoiChieu = document.body.getAttribute("data-ma");
    const elDate = document.getElementById("simulationDate");
    const elRate = document.getElementById("userInterestRate");

    const elPriceYield = document.getElementById("displayPriceYield");
    const elPriceCustom = document.getElementById("displayPriceCustom");
    const elMarketValue = document.getElementById("displayMarketValue");
    const btnReset = document.getElementById("btnReset");

    // Các ô hiển thị trong bảng (Test Case Elements)
    const tdYieldA = document.getElementById("tdYieldA");
    const tdYieldB = document.getElementById("tdYieldB");
    const tdYieldDiff = document.getElementById("tdYieldDiff");
    const tdCustomA = document.getElementById("tdCustomA");
    const tdCustomB = document.getElementById("tdCustomB");
    const tdCustomDiff = document.getElementById("tdCustomDiff");

    // --- MAIN FLOW ---
    try {
        const res = await fetch(`/cd/${maDoiChieu}`);
        if (!res.ok) throw new Error("API Error");
        cdData = await res.json();
        
        const c1 = cdData.thongTinChung || {};
        const c2 = cdData.thongTinLaiSuat || {};
        const c3 = cdData.thongTinNhapKho || {};
        const c4 = cdData.thongtinGia || {};

        // --- Render Text Info ---
        const setText = (id, val) => { 
            const el = document.getElementById(id); 
            if(el) el.innerText = val ?? ""; 
        };

        setText("maDoiChieu", c1.maDoiChieu);
        setText("TCPH", c1.TCPH);
        setText("ngayPhatHanh", c1.ngayPhatHanh);
        setText("ngayDaoHan", c1.ngayDaoHan);
        setText("menhGia", formatCurrency(parseMoneyVN(c1.menhGia)));
        setText("soLuong", c1.soLuong);
        setText("CDKhaDung", c1.CDKhaDung);
        setText("ngayTHQuyen", c1.ngayTHQuyen);
        setText("loaiLaiSuat", c1.loaiLaiSuat);
        setText("ghiChu", c1.ghiChu);

        setText("laiSuat", c2.laiSuat);
        setText("quyUocNgay", c2.quyUocNgay);
        setText("tanSuatTraLai", c2.tanSuatTraLai);

        setText("dirtyPrice", c3.dirtyPrice);
        setText("cleanPrice", c3.cleanPrice);
        setText("ngayThucHien", c3.ngayThucHien);
        setText("ngayThucTe", c3.ngayThucTe);
        setText("soLuongNhapKho", c3.soLuongNhapKho);

        setText("AI", c4.AI);
        setText("marketValueTKO", c4.marketValueTKO);
        setText("giaBanHomNay", c4.giaBanHomNay);

        // --- INIT CONTROLS ---
        const today = new Date();
        elDate.value = today.toISOString().split('T')[0];
        
        // [FIXED] Luôn set mặc định là 4.0
        if (!elRate.value || elRate.value == "") {
             elRate.value = 4.0;
        } else {
             elRate.value = 4.0; 
        }

        calculateAndDraw();

    } catch (err) {
        console.error("Critical Error:", err);
        if(elPriceYield) elPriceYield.innerText = "Lỗi kết nối";
    }

    // --- EVENTS ---
    elDate.addEventListener("input", updateDisplayOnly);
    elRate.addEventListener("input", calculateAndDraw);
    
    btnReset.addEventListener("click", () => {
        elDate.value = new Date().toISOString().split('T')[0];
        updateDisplayOnly();
    });


    // --- CALCULATION LOGIC ---

    function calculateAndDraw() {
        if (!cdData) return;

        const c1 = cdData.thongTinChung || {};
        const c2 = cdData.thongTinLaiSuat || {};

        const userInputRate = parseMoneyVN(elRate.value) / 100; 
        const menhGia = parseMoneyVN(c1.menhGia);
        const issueDate = parseDateVN(c1.ngayPhatHanh);
        const maturityDate = parseDateVN(c1.ngayDaoHan);
        const cdCouponRate = parseMoneyVN(c2.laiSuat) / 100; 
        const tanSuatStr = c2.tanSuatTraLai || "Cuối kỳ";

        if (isNaN(menhGia) || !issueDate || !maturityDate) return;

        const labels = [];
        const dataYield = [];
        const dataCustom = [];
        const dataMarketValue = [];

        // Base price calculation (Ngày đầu tiên)
        const firstNextCoupon = getNextCouponDate(issueDate, maturityDate, tanSuatStr, issueDate);
        const priceBaseDay0 = calculateYieldFormula(menhGia, cdCouponRate, userInputRate, firstNextCoupon, issueDate, issueDate, maturityDate, tanSuatStr);

        let loopDate = new Date(issueDate);
        let safetyCount = 0;

        while (loopDate <= maturityDate && safetyCount < 3000) {
            labels.push(formatDateVN(loopDate));

            // [FIXED LOGIC] Lấy ngày trả lãi gần nhất trước đó để tính lãi tích luỹ trong kỳ này
            const lastCoupon = getLastCouponDate(issueDate, maturityDate, tanSuatStr, loopDate);
            const nextCoupon = getNextCouponDate(issueDate, maturityDate, tanSuatStr, loopDate);

            // 1. Yield Price
            // Lưu ý: Hàm calculateYieldFormula đã được update để xử lý reset giá
            const pYield = calculateYieldFormula(menhGia, cdCouponRate, userInputRate, nextCoupon, loopDate, issueDate, maturityDate, tanSuatStr);
            dataYield.push(pYield);

            // 2. Custom Price (Yield + X)
            // Logic cũ: (loopDate - issueDate) -> Sai vì nó cộng dồn mãi mãi.
            // Logic mới: (loopDate - lastCoupon) -> Chỉ tính ngày nắm giữ trong kỳ lãi hiện tại.
            const daysPassedInPeriod = (loopDate - lastCoupon) / (1000 * 60 * 60 * 24);
            
            // Công thức: Giá Gốc + (Giá Gốc * Lãi User * Số ngày trong kỳ / 365)
            // priceBaseDay0 ở đây tượng trưng cho giá Clean Price (Gốc)
            const pCustom = priceBaseDay0 + (priceBaseDay0 * userInputRate * daysPassedInPeriod) / 365;
            dataCustom.push(pCustom);

            // 3. Market Value
            const pMarketValue = calculateMarketValue(menhGia, cdCouponRate, loopDate, issueDate, tanSuatStr);
            dataMarketValue.push(pMarketValue);

            loopDate.setDate(loopDate.getDate() + 30); 
            safetyCount++;
        }

        renderChart(labels, dataYield, dataCustom, dataMarketValue);
        updateDisplayOnly(); 
    }

    // --- 2. HÀM CÔNG THỨC CHÍNH XÁC (Đã sửa logic Reset) ---
    function calculateYieldFormula(M, r_CD, r_User, nextDate, currDate, issueDate, maturityDate, freqStr) {
        // Nếu đã đáo hạn
        if (currDate >= maturityDate) {
             // Logic cuối kỳ thì cộng hết, logic định kỳ thì chỉ cộng kỳ cuối
             const s = (freqStr || "").toLowerCase().trim();
             if (s.includes("cuối kỳ")) {
                 const totalDays = (maturityDate - issueDate)/(1000*60*60*24);
                 return M + (M * r_CD * totalDays/365);
             } else {
                 // Nếu trả định kỳ, tại ngày đáo hạn nhận Gốc + Lãi kỳ cuối
                 // Cần tìm ngày trả lãi trước đó để tính số ngày kỳ cuối
                 const lastDate = getLastCouponDate(issueDate, maturityDate, freqStr, new Date(maturityDate.getTime() - 86400000));
                 const daysInPeriod = (maturityDate - lastDate)/(1000*60*60*24);
                 return M + (M * r_CD * daysInPeriod/365);
             }
        }
        
        // 1. XÁC ĐỊNH TỬ SỐ (DÒNG TIỀN TƯƠNG LAI)
        let giaTuongLai = 0;
        const s = (freqStr || "").toLowerCase().trim();

        if (s.includes("cuối kỳ")) {
            // CD trả lãi cuối kỳ: Lãi tính trên TỔNG thời gian từ đầu đến cuối
            const totalDaysCD = (maturityDate - issueDate) / (1000 * 60 * 60 * 24);
            const totalInterest = M * r_CD * (totalDaysCD / 365); 
            giaTuongLai = M + totalInterest;
        } else {
            // CD trả lãi định kỳ: Dòng tiền sắp nhận = Gốc (nếu đáo hạn) + Lãi của KỲ NÀY thôi
            // Cần tính xem kỳ này dài bao nhiêu ngày (NextCoupon - LastCoupon)
            const lastDate = getLastCouponDate(issueDate, maturityDate, freqStr, currDate);
            const daysInPeriod = (nextDate - lastDate) / (1000 * 60 * 60 * 24);
            
            // Lãi coupon sắp nhận
            const couponPayment = M * r_CD * (daysInPeriod / 365);
            
            // Giả định Yield Price tính về Par + Coupon (đơn giản hoá cho dirty price)
            // Tại mỗi kỳ, giá trị tương lai là Mệnh Giá + Coupon kỳ đó
            giaTuongLai = M + couponPayment;
        }

        // 2. CHIẾT KHẤU VỀ HIỆN TẠI
        let daysToDiscount = (nextDate - currDate) / (1000 * 60 * 60 * 24);
        if (daysToDiscount < 0) daysToDiscount = 0;

        const denominator = 1 + (r_User * daysToDiscount) / 365;
        return giaTuongLai / denominator;
    }

    function calculateMarketValue(M, r_CD, currDate, issueDate, freqStr) {
        // [FIXED] Market Value = Mệnh giá + Lãi tích luỹ (Accrued Interest)
        // Lãi tích luỹ phải được reset về 0 sau mỗi lần trả lãi.
        
        // 1. Tìm ngày bắt đầu tính lãi của kỳ này
        const lastCouponDate = getLastCouponDate(issueDate, null, freqStr, currDate);
        
        // 2. Tính số ngày đã trôi qua trong kỳ này
        const daysPassedInPeriod = (currDate - lastCouponDate) / (1000 * 60 * 60 * 24);
        
        if (daysPassedInPeriod < 0) return M;

        // 3. Tính lãi tích luỹ
        const accruedInterest = M * r_CD * (daysPassedInPeriod / 365);
        
        return M + accruedInterest;
    }

    function updateDisplayOnly() {
        if (!cdData) return;
        
        const selectedDate = new Date(elDate.value); 
        const userInputRate = parseMoneyVN(elRate.value) / 100;
        
        const c1 = cdData.thongTinChung || {};
        const c2 = cdData.thongTinLaiSuat || {};
        
        const menhGia = parseMoneyVN(c1.menhGia);
        const cdCouponRate = parseMoneyVN(c2.laiSuat) / 100;
        const issueDate = parseDateVN(c1.ngayPhatHanh);
        const maturityDate = parseDateVN(c1.ngayDaoHan);
        const tanSuatStr = c2.tanSuatTraLai || "Cuối kỳ";

        if (!issueDate || !maturityDate) return;

        // Yield
        const nextCoupon = getNextCouponDate(issueDate, maturityDate, tanSuatStr, selectedDate);
        const valYield = calculateYieldFormula(menhGia, cdCouponRate, userInputRate, nextCoupon, selectedDate, issueDate, maturityDate, tanSuatStr);

        // Custom
        // Tính từ ngày trả lãi gần nhất
        const lastCoupon = getLastCouponDate(issueDate, maturityDate, tanSuatStr, selectedDate);
        // Lấy giá gốc tại đầu kỳ (tạm tính là yield tại ngày đầu kỳ đó)
        const nextCouponForBase = getNextCouponDate(issueDate, maturityDate, tanSuatStr, lastCoupon);
        const priceBase = calculateYieldFormula(menhGia, cdCouponRate, userInputRate, nextCouponForBase, lastCoupon, issueDate, maturityDate, tanSuatStr);
        
        const daysPassed = (selectedDate - lastCoupon) / (1000 * 60 * 60 * 24);
        const valCustom = priceBase + (priceBase * userInputRate * daysPassed) / 365;
        
        // Market
        const valMarketValue = calculateMarketValue(menhGia, cdCouponRate, selectedDate, issueDate, tanSuatStr);

        if(elPriceYield) elPriceYield.innerText = formatCurrency(valYield);
        if(elPriceCustom) elPriceCustom.innerText = formatCurrency(valCustom);
        if(elMarketValue) elMarketValue.innerText = formatCurrency(valMarketValue);
    }

    // --- HELPER FUNCTIONS ---

    // [NEW FUNCTION] Tìm ngày trả lãi gần nhất TRƯỚC ngày hiện tại
    function getLastCouponDate(start, end, freqStr, current) {
        const s = (freqStr || "").toLowerCase().trim();
        // Nếu là trả lãi cuối kỳ, thì ngày bắt đầu tính lãi luôn là ngày phát hành
        if (s.includes("cuối kỳ")) return new Date(start);

        // Logic tương tự getNextCoupon nhưng tìm ngày <= current
        let months = 12;
        if (s.includes("theo quý") || s.includes("3 tháng")) months = 3;
        else if (s.includes("bán niên") || s.includes("6 tháng")) months = 6;
        else if (s.includes("hàng năm") || s.includes("1 năm") || s.includes("12 tháng")) months = 12;
        else if (s.includes("1 tháng") || s.includes("hàng tháng")) months = 1;

        let d = new Date(start);
        let prev = new Date(start);
        let limit = 0;

        while (d <= current && limit < 500) {
            prev = new Date(d); // Lưu lại ngày hiện tại trước khi cộng
            d = addMonths(d, months);
            
            // Nếu cộng xong mà vượt quá maturity, thì check xem maturity có <= current không
            if (end && d > end) {
                // Nếu ngày đáo hạn đã qua rồi (current >= maturity), thì trả về maturity (hoặc prev tuỳ logic)
                // Ở đây ta muốn tìm mốc tính lãi, thường là prev
                break;
            }
            limit++;
        }
        return prev;
    }

    function getNextCouponDate(start, end, freqStr, current) {
        const s = (freqStr || "").toLowerCase().trim();
        if (s.includes("cuối kỳ")) return new Date(end);

        let months = 12;
        if (s.includes("theo quý") || s.includes("3 tháng")) months = 3;
        else if (s.includes("bán niên") || s.includes("6 tháng")) months = 6;
        else if (s.includes("hàng năm") || s.includes("1 năm") || s.includes("12 tháng")) months = 12;
        else if (s.includes("1 tháng") || s.includes("hàng tháng")) months = 1;

        let d = new Date(start);
        let limit = 0; 
        // Tìm ngày đầu tiên LỚN HƠN current
        while (d <= current && limit < 500) {
            d = addMonths(d, months);
            if (d > end) return new Date(end);
            limit++;
        }
        return d;
    }

    function addMonths(date, months) {
        const d = new Date(date);
        d.setMonth(d.getMonth() + months);
        if (d.getDate() !== date.getDate()) d.setDate(0); 
        return d;
    }

    function parseDateVN(str) {
        if (!str) return null;
        if (str instanceof Date) return str;
        let d = new Date(str);
        if (!isNaN(d.getTime())) return d;
        const parts = str.split(/[-/]/); 
        if (parts.length === 3) {
            const day = parseInt(parts[0], 10);
            const month = parseInt(parts[1], 10) - 1; 
            const year = parseInt(parts[2], 10);
            d = new Date(year, month, day);
            if (!isNaN(d.getTime())) return d;
        }
        return null; 
    }

    function parseMoneyVN(val) {
        if (val === undefined || val === null || val === "") return 0;
        if (typeof val === 'number') return val;
        let str = val.toString();
        if ((str.match(/\./g) || []).length > 1) str = str.replace(/\./g, "");
        str = str.replace(/,/g, ".");
        return parseFloat(str) || 0;
    }

    function formatCurrency(val) {
        if (isNaN(val)) return "---";
        return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(val);
    }

    function formatDateVN(date) {
        if (!date) return "";
        const d = date.getDate();
        const m = date.getMonth() + 1;
        const y = date.getFullYear();
        return `${d}/${m}/${y}`;
    }

    function renderChart(labels, d1, d2, d3) { 
        const ctx = document.getElementById('priceChart').getContext('2d');
        if (myChart) myChart.destroy();

        myChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Giá Yield',
                        data: d1,
                        borderColor: 'rgb(255, 99, 132)',
                        borderWidth: 2,
                        pointRadius: 0,
                        tension: 0.1
                    },
                    {
                        label: 'Giá Yield + Khoảng X',
                        data: d2,
                        borderColor: 'rgb(54, 162, 235)',
                        borderWidth: 2,
                        pointRadius: 0,
                        tension: 0.1
                    },
                    { 
                        label: 'Market Value',
                        data: d3,
                        borderColor: 'rgb(241, 196, 15)', 
                        backgroundColor: 'rgba(241, 196, 15, 0.2)',
                        borderWidth: 2,
                        pointRadius: 0,
                        tension: 0.1,
                        borderDash: [5, 5] 
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: (context) => context.dataset.label + ': ' + formatCurrency(context.raw)
                        }
                    }
                },
                scales: {
                    y: {
                        ticks: {
                            callback: (value) => formatCurrency(value) 
                        }
                    }
                }
            }
        });
    }
});