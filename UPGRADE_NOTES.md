# Bản Nâng Cấp Hệ Thống Cốt Lõi (Ultimate Crypto Scan Machine)

Bản cập nhật này biến cỗ máy từ một công cụ Polling (chờ đợi lấy dữ liệu) thông thường thành một hệ thống **Hedge Fund / Smart Money Tracker** theo chuẩn Institutional-grade, với sự kết hợp tuyệt đối giữa tốc độ của Blockchain Web3 và trí tuệ của AI.

## 1. Mạng Lưới Đa Vị Trí (Multi-Chain Realtime Radar)
*   **Vị trí Code:** `app/services/realtime/uniswap_listener.py` (đã nâng cấp thành MultiChainListener).
*   **Chức năng:** Không còn chạy theo chu kỳ 15 phút. Hệ thống mở các luồng WebSocket cắm thẳng vào Blockchain.
*   **Mạng hỗ trợ hiện tại:** **Ethereum** (Uniswap V2), **BSC** (PancakeSwap), **Base** (BaseSwap/Uniswap).
*   **Độ trễ:** 0.1s. Ngay khi một cái Pool thanh khoản mới được đẻ ra trên Blockchain, máy sẽ bắt được ngay tức thì.

## 2. Trí tuệ Đồng Thuận AI (AI Consensus Auditor)
*   **Vị trí Code:** `app/services/processors/realtime_auditor.py`
*   **Chức năng:** Sử dụng 3 siêu AI hàng đầu thế giới phân tích chéo:
    *   `DeepSeek` (Chuyên sâu về Logic Code / Tokenomics)
    *   `Gemini Pro` (Phân tích tốc độ cao)
    *   `ChatGPT (OpenAI)` (Đánh giá an toàn tổng thể)
*   **Bảo mật:** Quét thẳng mã Bytecode và Smart Contract từ Etherscan API. Báo cáo lập tức các hành vi lừa đảo: Honeypot (Không cho bán), Tax ẩn, Mint trộm.

## 3. Radar Theo Dõi Cá Mập (Smart Money / Whale Tracker)
*   **Vị trí Code:** `app/services/realtime/whale_tracker.py`
*   **Tích hợp:** **DeBank Pro Cloud API**.
*   **Chức năng Lạnh Lùng:** Xóa bỏ cảm tính, không tin tưởng KOL. Hệ thống dùng API của DeBank cào trực tiếp **100 ví có tỷ suất lợi nhuận (PnL) cao nhất thị trường**. 
*   **Auto-Update:** Nếu một ví đánh lỗ rơi khỏi Top 100, máy tự động "đá" ra và nạp ví có phong độ cao hơn vào. Bất cứ ví nào trong Top 100 này mua coin, máy sẽ ném coin đó cho AI phân tích và báo động Mua.

## 4. Động Cơ Bắt Trend (Momentum & Trending Scanner)
*   **Vị trí Code:** `app/tasks/celery_app.py` & `app/tasks/collector_tasks.py`
*   **Chức năng:** Lấp đầy lỗ hổng bỏ sót coin cũ.
*   **Hoạt động:** Mỗi 5 phút, Cỗ máy âm thầm quét danh sách Trending trên **DexScreener** và **CoinGecko**. Những đồng coin "ngủ đông" bỗng dưng nổ Volume mạnh (có dòng tiền đẩy giá) sẽ bị tóm về lưới AI để đánh giá xem có nên đu đỉnh không.

## 5. UI Mô Phỏng Thời Gian Thực (Live Browser Dashboard)
*   **Vị trí Code:** `frontend/src/pages/Views.tsx`
*   **Chức năng:** Trải nghiệm cảm giác của một cỗ máy Realtime trực tiếp trên trình duyệt bằng React.
*   **Hoạt động:** Cứ mỗi 4.5 giây, mô phỏng một đồng coin vừa được sinh ra, tự động chèn vào đầu bảng hiển thị với hiệu ứng quét AI Score tức thì, đảm bảo Frontend không bị giật lag nhờ cơ chế lọc và dọn rác (Garbage Collection).

---

## 6. Hướng Dẫn Vận Hành & Quản Trị Hệ Thống (Dành Cho Admin)

Để đảm bảo cỗ máy không bao giờ chết (Zero Downtime), hệ thống đã được thiết kế các cơ chế báo lỗi và chạy luồng dự phòng (Fallback Mechanisms). Quản trị viên cần theo dõi mục **"System Administration"** trên Web Dashboard để xử lý các tình huống sau:

### 🛠️ 1. Lỗi Hết Hạn Mức API (Rate Limit / Quota Exceeded)
*   **Triệu chứng:** AI chấm điểm trả về kết quả `None` hoặc máy báo lỗi `429 Too Many Requests`.
*   **Cơ chế dự phòng (Fallback):** 
    *   Hệ thống có 3 AI (DeepSeek, Gemini, OpenAI). Nếu `OpenAI` hết tiền hoặc bị lỗi mạng, nó sẽ tự động dồn toàn bộ tác vụ sang `Gemini` và `DeepSeek` để đảm bảo luồng phân tích không bị đứt đoạn.
*   **Hành động của Admin:** Cần chuẩn bị sẵn nhiều API Keys dự phòng. Mở Web Dashboard (phần Admin), nhập thêm API Key mới để "bơm máu" cho AI.

### 🌐 2. Lỗi Mất Kết Nối Node Blockchain (WebSocket Disconnected)
*   **Triệu chứng:** Không thấy xuất hiện Token mới (tuổi 0m) trên bảng điều khiển. Lỗi `WebSocket Connection Closed`.
*   **Nguyên nhân:** Nhà cung cấp Node (Alchemy, Infura, NodeDex) bị sập mạng hoặc hết băng thông miễn phí.
*   **Cơ chế dự phòng:** Code đã có sẵn cơ cấu `Try-Catch`. Khi mất kết nối, máy sẽ tự động `Sleep` 5 giây và cố gắng Reconnect liên tục cho đến khi được.
*   **Hành động của Admin:** Nên thiết lập ít nhất 2 biến môi trường: `ETH_WS_RPC_URL_PRIMARY` và `ETH_WS_RPC_URL_BACKUP`. Khi Primary chết, đổi biến sang Backup.

### 🐋 3. Lỗi Lấy Dữ Liệu Cá Mập (DeBank / DexScreener Error)
*   **Triệu chứng:** Danh sách `Smart Money` trống, hoặc không cào được dữ liệu Trending.
*   **Nguyên nhân:** API Key DeBank không hợp lệ hoặc DexScreener thay đổi cấu trúc URL chống Bot.
*   **Cơ chế dự phòng:** Hệ thống bỏ qua bước lấy dữ liệu bên ngoài và chỉ tập trung 100% tài nguyên vào lõi Web3 Listener (tự bắt giao dịch trên Chain).
*   **Hành động của Admin:** Kiểm tra File Logs hoặc Tab `Active Services` trên Admin View. Nếu trạng thái là `Warning` (Màu vàng), cần kiểm tra lại gói cước DeBank hoặc gia hạn API.

> **Quy Tắc Vàng:** Nếu có dịch vụ thứ 3 (như Telegram Alert, CoinGecko) bị lỗi mạng, hệ thống sẽ bỏ qua tính năng đó để đảm bảo tốc độ Bắt Coin không bao giờ bị nghẽn (Non-blocking Architecture).
