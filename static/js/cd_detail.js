
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
    // --- ELEMENTS MỚI CHO TEST CASE ---
    const elSimRateCurrent = document.getElementById("simRateCurrent");
    const elSimRateNew = document.getElementById("simRateNew");
    const btnRunTest = document.getElementById("btnRunTest");
    const btnApplyRate = document.getElementById("btnApplyRate");

    // Các ô hiển thị trong bảng
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

        // --- Thông tin chung ---
        document.getElementById("maDoiChieu").innerText = c1.maDoiChieu ?? "";
        document.getElementById("TCPH").innerText = c1.TCPH ?? "";
        document.getElementById("ngayPhatHanh").innerText = c1.ngayPhatHanh ?? "";
        document.getElementById("ngayDaoHan").innerText = c1.ngayDaoHan ?? "";
        document.getElementById("menhGia").innerText = c1.menhGia ?? "";
        document.getElementById("soLuong").innerText = c1.soLuong ?? "";
        document.getElementById("CDKhaDung").innerText = c1.CDKhaDung ?? "";
        document.getElementById("ngayTHQuyen").innerText = c1.ngayTHQuyen ?? "";
        document.getElementById("loaiLaiSuat").innerText = c1.loaiLaiSuat ?? "";
        document.getElementById("ghiChu").innerText = c1.ghiChu ?? "";

        // --- Lãi suất ---
        document.getElementById("laiSuat").innerText = c2.laiSuat ?? "";
        document.getElementById("quyUocNgay").innerText = c2.quyUocNgay ?? "";
        document.getElementById("tanSuatTraLai").innerText = c2.tanSuatTraLai ?? "";

        // --- Thông tin nhập kho ---
        document.getElementById("dirtyPrice").innerText = c3.dirtyPrice ?? "";
        document.getElementById("cleanPrice").innerText = c3.cleanPrice ?? "";
        document.getElementById("ngayThucHien").innerText = c3.ngayThucHien ?? "";
        document.getElementById("ngayThucTe").innerText = c3.ngayThucTe ?? "";
        document.getElementById("soLuongNhapKho").innerText = c3.soLuongNhapKho ?? "";

        // --- Thông tin giá ---
        document.getElementById("AI").innerText = c4.AI ?? "";
        document.getElementById("marketValueTKO").innerText = c4.marketValueTKO ?? "";
        document.getElementById("giaBanHomNay").innerText = c4.giaBanHomNay ?? "";

        renderStaticInfo(cdData);

        const today = new Date();
        elDate.value = today.toISOString().split('T')[0];
        
        const defRateRaw = cdData.thongTinLaiSuat?.laiSuat;
        const defRate = parseMoneyVN(defRateRaw) || 5.0; 
        elRate.value = defRate;
        elSimRateCurrent.value = defRate; // NEW: Đồng bộ lãi suất ban đầu

        calculateAndDraw();

    } catch (err) {
        console.error("Critical Error:", err);
        elPriceYield.innerText = "Lỗi kết nối";
    }

    // --- EVENTS ---
    elDate.addEventListener("input", updateDisplayOnly);
    elRate.addEventListener("input", calculateAndDraw);
    btnReset.addEventListener("click", () => {
        elDate.value = new Date().toISOString().split('T')[0];
        updateDisplayOnly();
    });
     // --- SỰ KIỆN MỚI ---
    
    // Khi lãi suất chính thay đổi -> Cập nhật luôn vào ô "Lãi suất hiện tại" của Test Case
    elRate.addEventListener("input", () => {
        calculateAndDraw(); // Hàm cũ
        elSimRateCurrent.value = elRate.value; // Sync xuống dưới
    });

    // Nút chạy Test Case
    btnRunTest.addEventListener("click", () => {
        runSimulationTestCase();
    });

    // Nút Áp dụng (Nếu user thấy lãi mới ngon thì bấm nút này để update lên UI chính)
    btnApplyRate.addEventListener("click", () => {
        elRate.value = elSimRateNew.value;
        calculateAndDraw(); // Vẽ lại chart chính
        elSimRateCurrent.value = elRate.value;
        btnApplyRate.style.display = 'none'; // Ẩn nút áp dụng đi
        alert("Đã áp dụng lãi suất mới!");
    });

    // --- LOGIC TEST CASE ---

   function runSimulationTestCase() {
        if (!cdData) return;

        const rateA = parseMoneyVN(elSimRateCurrent.value) / 100;
        const rateB = parseMoneyVN(elSimRateNew.value) / 100;
        const selectedDate = new Date(elDate.value);

        if (isNaN(rateB)) {
            alert("Vui lòng nhập lãi suất giả định hợp lệ!");
            return;
        }

        const resultA = calculatePricesAtPoint(rateA, selectedDate);
        const resultB = calculatePricesAtPoint(rateB, selectedDate);

        tdYieldA.innerText = formatCurrency(resultA.yieldPrice);
        tdYieldB.innerText = formatCurrency(resultB.yieldPrice);
        renderDiff(tdYieldDiff, resultA.yieldPrice, resultB.yieldPrice);
        
        tdCustomA.innerText = formatCurrency(resultA.customPrice);
        tdCustomB.innerText = formatCurrency(resultB.customPrice);
        renderDiff(tdCustomDiff, resultA.customPrice, resultB.customPrice);

        btnApplyRate.style.display = 'inline-block';
    }
     function calculateMarketValue(M, r_CD, currDate, issueDate) {
        // Market Value = Mệnh giá + Mệnh giá * Lãi suất CD * (Ngày hiện tại - Ngày phát hành) / 365
        const daysPassed = (currDate - issueDate) / (1000 * 60 * 60 * 24);
        if (daysPassed < 0) return M;
        
        const accruedInterest = M * r_CD * (daysPassed / 365);
        return M + accruedInterest;
    }
  

    // --- REFACTOR: Tách logic tính giá ra hàm riêng để dùng chung ---
    // Hàm này trả về Object { yieldPrice, customPrice }
   // Hàm tách biệt để dùng cho Test Case
    function calculatePricesAtPoint(userRate, datePoint) {
        const c1 = cdData.thongTinChung || {};
        const c2 = cdData.thongTinLaiSuat || {};
        
        const menhGia = parseMoneyVN(c1.menhGia);
        const cdCouponRate = parseMoneyVN(c2.laiSuat) / 100;
        const issueDate = parseDateVN(c1.ngayPhatHanh);
        const maturityDate = parseDateVN(c1.ngayDaoHan);
        const tanSuatStr = c2.tanSuatTraLai || "Cuối kỳ";

        if (!issueDate || !maturityDate || isNaN(datePoint)) {
            return { yieldPrice: 0, customPrice: 0 };
        }

        const nextCoupon = getNextCouponDate(issueDate, maturityDate, tanSuatStr, datePoint);
        const pYield = calculateYieldFormula(menhGia, cdCouponRate, userRate, nextCoupon, datePoint, issueDate, maturityDate);

        const firstNextCoupon = getNextCouponDate(issueDate, maturityDate, tanSuatStr, issueDate);
        const priceBaseDay0 = calculateYieldFormula(menhGia, cdCouponRate, userRate, firstNextCoupon, issueDate, issueDate, maturityDate);
        
        const daysPassed = (datePoint - issueDate) / (1000 * 60 * 60 * 24);
        const pCustom = priceBaseDay0 + (priceBaseDay0 * userRate * daysPassed) / 365;

        // Market Value không đổi theo userRate, nhưng vẫn tính để hoàn chỉnh
        // const pMarketValue = calculateMarketValue(menhGia, cdCouponRate, datePoint, issueDate); 

        return { yieldPrice: pYield, customPrice: pCustom }; 
    }
    // --- CORE LOGIC ---

   // --- 1. HÀM TÍNH TOÁN VÀ VẼ (Đã cập nhật việc truyền Lãi suất CD) ---
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
        const dataMarketValue = []; // NEW ARRAY

        // Tính giá Base ngày đầu (dùng cho công thức riêng)
        const firstNextCoupon = getNextCouponDate(issueDate, maturityDate, tanSuatStr, issueDate);
        const priceBaseDay0 = calculateYieldFormula(menhGia, cdCouponRate, userInputRate, firstNextCoupon, issueDate, issueDate, maturityDate);

        let loopDate = new Date(issueDate);
        let safetyCount = 0;

        while (loopDate <= maturityDate && safetyCount < 3000) {
            labels.push(formatDateVN(loopDate));

            // 1. Yield Price
            const nextCoupon = getNextCouponDate(issueDate, maturityDate, tanSuatStr, loopDate);
            const pYield = calculateYieldFormula(menhGia, cdCouponRate, userInputRate, nextCoupon, loopDate, issueDate, maturityDate);
            dataYield.push(pYield);

            // 2. Custom Price
            const daysPassed = (loopDate - issueDate) / (1000 * 60 * 60 * 24);
            const pCustom = priceBaseDay0 + (priceBaseDay0 * userInputRate * daysPassed) / 365;
            dataCustom.push(pCustom);

            // 3. Market Value (NEW)
            const pMarketValue = calculateMarketValue(menhGia, cdCouponRate, loopDate, issueDate);
            dataMarketValue.push(pMarketValue);

            loopDate.setDate(loopDate.getDate() + 5); 
            safetyCount++;
        }

        renderChart(labels, dataYield, dataCustom, dataMarketValue); // UPDATED CALL
        updateDisplayOnly();
    }
    // --- 2. HÀM CÔNG THỨC CHÍNH XÁC (Đã sửa theo yêu cầu của bạn) ---
    /**
     * Công thức: P = Giá Đáo Hạn / (1 + r_User * t/365)
     * Trong đó: Giá Đáo Hạn = Mệnh Giá + Tiền Lãi CD
     */
    function calculateYieldFormula(M, r_CD, r_User, nextDate, currDate, issueDate, maturityDate) {
        // Validation cơ bản
        if (currDate >= maturityDate) return M + (M * r_CD * ((maturityDate - issueDate)/(1000*60*60*24))/365); 
        
        // 1. TÍNH TỬ SỐ (Giá Đáo Hạn)
        // Tiền lãi = Mệnh giá * Lãi suất CD * (Số ngày thực tế của kỳ hạn / 365)
        const totalDaysCD = (maturityDate - issueDate) / (1000 * 60 * 60 * 24);
        const totalInterest = M * r_CD * (totalDaysCD / 365); 
        const giaDaoHan = M + totalInterest;
        console.log("gia dao hạn là", giaDaoHan)
        // 2. TÍNH MẪU SỐ (Chiết khấu dòng tiền)
        // t: Là số ngày từ hiện tại đến "Ngày tính lãi tiếp theo" (Next Coupon Date)
        // Nếu user muốn tính đến ngày đáo hạn luôn thì thay nextDate bằng maturityDate
        let daysToDiscount = (nextDate - currDate) / (1000 * 60 * 60 * 24);
        
        if (daysToDiscount < 0) daysToDiscount = 0;

        const denominator = 1 + (r_User * daysToDiscount) / 365;

        return giaDaoHan / denominator;
    }

  function updateDisplayOnly() {
        if (!cdData) return;
        
        // Lấy ngày bán dự kiến từ UI
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

        // 1. Yield Calc (Dùng selectedDate)
        const nextCoupon = getNextCouponDate(issueDate, maturityDate, tanSuatStr, selectedDate);
        const valYield = calculateYieldFormula(menhGia, cdCouponRate, userInputRate, nextCoupon, selectedDate, issueDate, maturityDate);

        // 2. Custom Calc (Dùng selectedDate)
        const firstNextCoupon = getNextCouponDate(issueDate, maturityDate, tanSuatStr, issueDate);
        const priceBaseDay0 = calculateYieldFormula(menhGia, cdCouponRate, userInputRate, firstNextCoupon, issueDate, issueDate, maturityDate);
        const daysPassed = (selectedDate - issueDate) / (1000 * 60 * 60 * 24);
        const valCustom = priceBaseDay0 + (priceBaseDay0 * userInputRate * daysPassed) / 365;
        
        // 3. Market Value Calc (Dùng selectedDate làm ngày tính toán)
        const valMarketValue = calculateMarketValue(menhGia, cdCouponRate, selectedDate, issueDate);

        elPriceYield.innerText = formatCurrency(valYield);
        elPriceCustom.innerText = formatCurrency(valCustom);
        elMarketValue.innerText = formatCurrency(valMarketValue);
    }
    // --- FORMULAS & HELPER ---


    function getNextCouponDate(start, end, freqStr, current) {
        // 1. Chuẩn hóa chuỗi đầu vào
        const s = (freqStr || "").toLowerCase().trim();
        
        // 2. Xử lý trường hợp đặc biệt: Cuối kỳ
        if (s.includes("cuối kỳ")) {
            return new Date(end);
        }

        // 3. Ánh xạ từ khóa sang số tháng
        let months = 12; // Mặc định là hàng năm (12 tháng) nếu không khớp
        
        if (s.includes("theo quý") || s.includes("3 tháng")) {
            months = 3;
        } 
        else if (s.includes("bán niên") || s.includes("6 tháng")) {
            months = 6;
        } 
        else if (s.includes("hàng năm") || s.includes("1 năm") || s.includes("12 tháng")) {
            months = 12;
        }
        // Giữ lại logic tháng lẻ nếu dữ liệu lịch sử có
        else if (s.includes("1 tháng") || s.includes("hàng tháng")) {
            months = 1;
        }

        // 4. Logic tìm ngày trả lãi tiếp theo
        // Bắt đầu từ ngày phát hành, cộng dồn tháng cho đến khi > ngày hiện tại
        let d = new Date(start);
        
        // Safety break: Chặn lặp vô hạn (tối đa 500 kỳ - tương đương 40 năm nếu trả theo tháng)
        let limit = 0; 
        
        // Loop chạy khi d vẫn nằm trong quá khứ hoặc bằng ngày hiện tại
        while (d <= current && limit < 500) {
            d = addMonths(d, months);
            
            // Nếu cộng xong mà vượt quá ngày đáo hạn -> Chặn lại ở ngày đáo hạn
            if (d > end) {
                return new Date(end);
            }
            limit++;
        }
        console.log("Ngày trả lãi tiếp theo",d)
        
        return d;
    }

    // Hàm hỗ trợ cộng tháng (Giữ nguyên logic tốt của bạn)
    function addMonths(date, months) {
        const d = new Date(date);
        d.setMonth(d.getMonth() + months);
        // Xử lý ngày cuộn (31/1 + 1 tháng -> 3/3, lùi về ngày cuối tháng 2 là 28/2 hoặc 29/2)
        if (d.getDate() !== date.getDate()) {
            d.setDate(0); 
        }
        return d;
    }


    // --- BỘ PARSER CHUYÊN DỤNG (QUAN TRỌNG) ---

    // Xử lý: "10/12/2023", "2023-12-10", "10-12-2023"
    function parseDateVN(str) {
        if (!str) return null;
        
        // Case 1: Đã là object Date
        if (str instanceof Date) return str;

        // Case 2: ISO string (YYYY-MM-DD)
        let d = new Date(str);
        if (!isNaN(d.getTime())) return d;

        // Case 3: DD/MM/YYYY hoặc DD-MM-YYYY (Việt Nam)
        const parts = str.split(/[-/]/); 
        if (parts.length === 3) {
            // Giả định phần đầu là ngày, phần 2 là tháng (DD/MM/YYYY)
            // Lưu ý: Tháng trong JS bắt đầu từ 0 (0 = tháng 1)
            const day = parseInt(parts[0], 10);
            const month = parseInt(parts[1], 10) - 1; 
            const year = parseInt(parts[2], 10);
            
            d = new Date(year, month, day);
            if (!isNaN(d.getTime())) return d;
        }

        return null; // Không parse được
    }

    // Xử lý: "100.000.000", "10,5" (lãi suất), 100000
    function parseMoneyVN(val) {
        if (val === undefined || val === null || val === "") return 0;
        if (typeof val === 'number') return val;

        let str = val.toString();
        
        // Nếu chuỗi chứa dấu phẩy (,) dùng làm thập phân (vd: 8,5%) 
        // -> replace , thành . 
        // NHƯNG nếu chuỗi chứa cả . và , (vd: 100.000,50) -> Phức tạp hơn
        // Logic đơn giản cho VN: Xóa hết dấu chấm (phân cách ngàn), thay phẩy bằng chấm
        
        if (str.includes(",") && str.includes(".")) {
            // Case: 100.000,50
            str = str.replace(/\./g, "").replace(",", ".");
        } else if (str.includes(",")) {
             // Case: 8,5 (lãi suất) hoặc 100,000 (kiểu Mỹ)
             // Ở đây ta ưu tiên Logic Lãi suất VN: 8,5 -> 8.5
             // Nếu là tiền kiểu Mỹ 100,000 -> thì sẽ thành 100.000 (100 đồng). 
             // Tạm thời replace , -> .
             str = str.replace(",", ".");
        } else if (str.includes(".")) {
            // Case: 100.000.000 (Tiền VN) hoặc 10.5 (Lãi suất)
            // Rất khó phân biệt tự động. 
            // Mẹo: Nếu số dấu chấm > 1 -> chắc chắn là tiền -> xóa hết.
            // Nếu chỉ có 1 dấu chấm -> coi là thập phân (hoặc chấp nhận sai nếu là 1.000 đồng)
            if ((str.match(/\./g) || []).length > 1) {
                str = str.replace(/\./g, "");
            } else {
                // Check ngữ cảnh, nhưng ở đây ta clean an toàn
                // Nếu giá trị lớn > 100 -> khả năng là tiền có dấu chấm -> xóa
                // Nếu < 100 -> lãi suất -> giữ nguyên
                // Đây là logic tương đối
                // TỐT NHẤT: Xóa hết dấu chấm nếu là mệnh giá
            }
        }
        
        // UPDATE LOGIC AN TOÀN NHẤT CHO PROJECT CỦA BẠN:
        // Giả sử Mệnh giá Backend trả về là int/float hoặc string sạch, 
        // hoặc string format kiểu VN: "100.000.000"
        
        // Thử regex lấy số
        // Cách an toàn: Xóa mọi thứ không phải số, dấu chấm, dấu trừ
        // Nếu format là 100.000.000 (VN) -> replace . bằng rỗng
        
        // Reset logic đơn giản hóa cho bạn:
        // 1. Nếu chuỗi có nhiều dấu chấm (ví dụ 10.000.000) -> Xóa hết chấm.
        if ((str.match(/\./g) || []).length > 1) {
            str = str.replace(/\./g, "");
        }
        // 2. Nếu chuỗi có dấu phẩy -> Thay bằng chấm
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

   function renderChart(labels, d1, d2, d3) { // ADD D3
        const ctx = document.getElementById('priceChart').getContext('2d');
        if (myChart) myChart.destroy();

        myChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Giá Yield (User Rate)',
                        data: d1,
                        borderColor: 'rgb(255, 99, 132)',
                        borderWidth: 2,
                        pointRadius: 0,
                        tension: 0.1
                    },
                    {
                        label: 'Giá Custom (User Rate)',
                        data: d2,
                        borderColor: 'rgb(54, 162, 235)',
                        borderWidth: 2,
                        pointRadius: 0,
                        tension: 0.1
                    },
                    { // NEW DATASET: Market Value
                        label: 'Market Value (Book)',
                        data: d3,
                        borderColor: 'rgb(241, 196, 15)', // Màu vàng
                        backgroundColor: 'rgba(241, 196, 15, 0.2)',
                        borderWidth: 2,
                        pointRadius: 0,
                        tension: 0.1,
                        borderDash: [5, 5] // Dotted line
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
                            callback: (value) => value / 1000000 + ' Triệu'
                        }
                    }
                }
            }
        });
    }

    function renderStaticInfo(data) {
        const c1 = data.thongTinChung || {};
        const el = (id, val) => { const e = document.getElementById(id); if(e) e.innerText = val ?? ""; };
        el("menhGia", formatCurrency(parseMoneyVN(c1.menhGia)));
        el("ngayPhatHanh", c1.ngayPhatHanh);
        el("ngayDaoHan", c1.ngayDaoHan);
        el("tanSuatTraLai", data.thongTinLaiSuat?.tanSuatTraLai);
    }
    function renderDiff(element, valA, valB) {
        const diff = valB - valA;
        const diffStr = formatCurrency(Math.abs(diff));
        
        if (diff > 0) {
            element.innerHTML = `<span class="diff-positive">+${diffStr} ⬆</span>`;
        } else if (diff < 0) {
            element.innerHTML = `<span class="diff-negative">-${diffStr} ⬇</span>`;
        } else {
            element.innerHTML = `<span style="color:#7f8c8d">0 ₫</span>`;
        }
    }
});



