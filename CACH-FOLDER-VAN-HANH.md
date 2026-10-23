# Folder nhà xe vận hành như thế nào?

## 1. Bắt đầu từ đâu?

Mở terminal tại thư mục chứa file này, chạy `npm.cmd run dev:watch`. Lệnh trong `package.json` gọi `server.js`. File đó đọc `.env`, khởi động Python backend trước rồi Next.js frontend. Cấu hình máy hiện tại: frontend **3010**, backend **18765**. Mở http://127.0.0.1:3010. Chỉ chạy một cửa sổ; Ctrl+C để dừng.

Máy mới: cài Node 22.12+ và Python 3.11+, chạy `npm.cmd ci` rồi `npm.cmd run setup`. `CHAY-NHA-XE.bat` là cách bấm chạy thông thường. `dev:watch` tự khởi động lại khi sửa backend hoặc cấu hình; Next tự cập nhật khi sửa giao diện. Khởi động lại backend sẽ hết phiên đăng nhập hiện tại.

## 2. Mỗi chỗ giữ việc gì?

| File/thư mục | Vai trò |
|---|---|
| `.env` | Cổng chạy, đường dẫn Python; cấu hình riêng của máy, không đưa lên Git |
| `.env.example` | Cấu hình mẫu để tạo `.env` trên máy mới |
| `package.json` / `package-lock.json` | Danh sách lệnh và phiên bản thư viện ở thư mục gốc |
| `server.js` | Điều phối hai dịch vụ, kiểm tra cổng và dừng các tiến trình nó tạo |
| `nha-xe-web/app/page.tsx` | Trang chính Next.js |
| `nha-xe-web/components/` | Các khối React: đăng nhập, nhận hàng, bảng, báo cáo, thu chi |
| `nha-xe-web/components/daily-cash.tsx` | Tổng thu/chi hôm nay, chi tiết và form ghi chi |
| `nha-xe-web/components/ticket-workspace.tsx` | Sơ đồ khoang, bán vé, điểm đón/trả và điều hành lịch xe |
| `nha-xe-web/lib/api.ts` | Gọi API, gửi cookie/CSRF và báo lỗi |
| `nha-xe-web/lib/types.ts` | Mô tả kiểu dữ liệu TypeScript |
| `nha-xe-web/next.config.ts` | Chuyển yêu cầu `/api/*` đến Python |
| `nha-xe-v1/app.py` | Kiểm tra đăng nhập, quyền và nghiệp vụ; đọc/ghi dữ liệu |
| `nha-xe-v1/fleet.py` | Hồ sơ xe, nhân viên và phân công tổ xe |
| `nha-xe-v1/tickets.py` / `ticket_routes.py` | Bán/thu/hủy vé, lịch xe và danh mục điểm đón/trả |
| `nha-xe-v1/data.sqlite3` | Dữ liệu thật, vẫn tồn tại sau khi tắt website |
| `nha-xe-v1/TAI-KHOAN.txt` | Mật khẩu khởi tạo; giữ kín |
| `nha-xe-v1/test_app.py` | Kiểm thử nghiệp vụ trên database tạm |
| `nha-xe-v1/static/` | Giao diện thuần cũ để tham khảo; tính năng mới nằm ở Next.js |
| `test/` | Kiểm tra cấu hình khởi động và kết nối hai dịch vụ |
| `../../references/portfolio-config/` | Bản sao cấu hình portfolio, không tham gia chạy nhà xe |
| `../../sources/` | Tài liệu đồng bộ chỉ đọc |
| `node_modules/`, `.next/` | Thư viện đã cài và kết quả build; không sửa thủ công |

## 3. Một thao tác đi qua đâu?

`Nhân viên bấm Lưu → React tạo JSON → /api/cargo → Next chuyển tiếp → Python kiểm tra → SQLite lưu → API trả kết quả → React tải lại bảng và tổng tiền.`

React xử lý giao diện; TypeScript giúp phát hiện lỗi khi viết code. Python mới quyết định người dùng được làm gì và dữ liệu có hợp lệ không. SQLite có các bảng hàng gửi, thu chi, xe/nhân viên và vé/lịch xe. Chưa sử dụng NestJS hoặc PostgreSQL. Xem [bán vé và lịch xe](BAN-VE-VA-LICH-XE.md) để theo dõi luồng mới và danh sách bảng chi tiết.

## 4. Thu chi hôm nay tính thế nào?

- **Đã thu:** tiền cước do tài khoản đó xác nhận nhận tiền hôm nay. Chọn Đã trả lúc tạo đơn ghi thu cho người tạo; bấm Thu tiền sau đó ghi thu cho người bấm. Nợ/chưa trả chưa tính vào thu.
- **Đã chi:** các khoản tài khoản đó ghi bằng form số tiền + lý do. Máy chủ tự gắn người ghi, chi nhánh nhân viên và thời gian Việt Nam.
- **Thu − Chi:** chênh lệch phát sinh, không phải lợi nhuận hay số dư quỹ; chưa có tồn đầu ngày và bàn giao tiền.
- Nhân viên chỉ xem thu/chi của chính tài khoản. Admin xem toàn bộ hoặc theo chi nhánh, có tên người thực hiện. Nếu nhiều người dùng chung tài khoản thì không tách được từng người; hiện dự án mới có hai tài khoản nhân viên SG/TK.
- Tổng tính toàn bộ khoản hôm nay; chi tiết hiện tối đa 100 khoản gần nhất. Tự cập nhật sau thao tác và mỗi 30 giây; không phụ thuộc ngày lọc danh sách hàng.
- Đơn và khoản thu được ghi cùng giao dịch database. Khoản chi có mã yêu cầu để gửi lại sau lỗi mạng không bị ghi hai lần. Chưa có sửa/hủy chi, thu ngoài cước, phê duyệt chi hoặc chứng từ.
- Dữ liệu cũ được khôi phục khoản thu từ lịch sử có người thực hiện; không đoán nếu thiếu bằng chứng. Khôi phục chạy lại không nhân đôi tiền. Không tự sửa chi nhánh của khoản thu lịch sử.

## 5. Kiểm tra và giữ dữ liệu

### Hai người nhập đơn cùng lúc

Đã kiểm thử ngày 22/10/2026 bằng hai phiên đăng nhập riêng, mỗi phiên có kết nối HTTP riêng, đồng bộ thời điểm gửi. Chạy 30 cặp admin/nhân viên (60 đơn), gồm cùng đầu và khác đầu, cả ba cách thanh toán. Kết quả: 60 yêu cầu thành công, 60 mã đơn riêng, 60 lịch sử nhận hàng, 20 khoản thu tương ứng 20 đơn đã trả; đúng người tạo, chi nhánh, nội dung và tổng thu. Database tạm qua kiểm tra toàn vẹn, không đụng dữ liệu thật.

Mỗi request mở kết nối SQLite riêng; database lần lượt thực hiện các giao dịch ghi, có thời gian chờ khóa 10 giây. Đơn, lịch sử và khoản thu được commit cùng nhau. Kết quả này xác nhận tình huống đã thử, chưa phải kiểm thử tải lớn, mất điện hoặc mất mạng lúc lưu. Tạo đơn hiện chưa chống gửi lại cùng request sau lỗi mạng.

Thử tay hai tài khoản trên hai máy hoặc hai trình duyệt/profile riêng. Hai tab trong cùng profile dùng chung cookie đăng nhập nên không mô phỏng được hai tài khoản độc lập. Để thấy đơn người khác vừa tạo, bấm Tải lại ở bảng; bảng chưa cập nhật thời gian thực. Khung thu chi tự cập nhật mỗi 30 giây.

### Chuyển hàng xe đầy sang ngày kế

Trong sổ hàng, nhân viên đầu gửi hoặc admin bấm **Xe đầy — chuyển ngày kế**, nhập tên/biển số xe nhận thay và xác nhận. Chỉ áp dụng cho đơn đang Chờ đi. Hệ thống tự tăng ngày đi dự kiến thêm một ngày và đưa toàn bộ đơn sang sổ ngày mới; không cần nhập lại. In danh sách dùng các đơn của ngày đi đang chọn. Mã đơn, ngày nhận gốc, cước và ngày thu tiền được giữ nguyên; lịch sử lưu người chuyển và dữ liệu trước/sau. Bấm lại từ dữ liệu cũ sẽ bị từ chối để tránh chuyển thêm một ngày ngoài ý muốn.

Database có thêm `scheduled_date` (ngày đi trên sổ) và `vehicle` (xe nhận thay). Dữ liệu cũ tự lấy ngày nhận làm ngày đi ban đầu. Báo cáo cước và CSV trong tab Tiền & lịch sử vẫn theo ngày nhận gốc, CSV có thêm ngày đi và xe để đối chiếu; không phải phơ chuyến. Hệ thống chưa tính sức chứa hàng tự động và chưa tách một phần số lượng trong cùng đơn. Danh mục/lịch xe đã có cho bán vé; trường xe của hàng gửi vẫn là văn bản riêng. Người vận hành xác định hàng dư; phần mềm tự dời sổ sau xác nhận.

### Thu chi 2 tuần và 1 tháng

Khung Tổng thu chi có Hôm nay, **2 tuần (14 ngày)** và **1 tháng**. Hai tuần tính cả ngày kết thúc và 13 ngày trước đó. Một tháng tính từ ngày 1 đến hết ngày cuối tháng được chọn, kể cả tháng nhuận. Khoảng ngày được in rõ trên màn hình. Nhân viên vẫn chỉ xem khoản của tài khoản mình, admin xem cả hai đầu hoặc lọc chi nhánh.

API `/api/cash-report` cộng toàn bộ giao dịch trong khoảng ngày theo giờ Việt Nam, không phụ thuộc ngày nhận hay ngày đi của hàng. Chi tiết hiện tối đa 100 khoản; tổng vẫn tính đầy đủ. Form Ghi khoản chi luôn ghi cho hôm nay, kể cả khi đang xem tháng trước. Muốn xem khoản vừa ghi, chọn Hôm nay. Không coi Thu − Chi là lợi nhuận hoặc số dư quỹ.

`npm.cmd run build`: kiểm tra/build frontend. Đổi cổng backend thì build lại trước `npm.cmd start`. `npm.cmd test`: kiểm tra cấu hình. Trong `nha-xe-v1`, chạy `python -m unittest test_app test_tickets -q` để kiểm tra nghiệp vụ bằng dữ liệu tạm.

Tiền vé đã thu cũng vào Tổng thu chi; vé chưa thu chưa ghi tiền. Hủy vé đã thu cần admin xác nhận đã hoàn đủ tiền và được ghi thành khoản chi hoàn vé. Báo cáo cước hàng và CSV phía dưới vẫn chỉ dành cho hàng gửi.

Giữ bản sao lưu dữ liệu trước nâng cấp. Sao lưu thủ công: dừng website và sao chép thư mục `nha-xe-v1`, gồm database cùng các file WAL/SHM nếu còn. CSV chỉ là xuất báo cáo, không thay thế backup. Không chia sẻ `.env`, `TAI-KHOAN.txt` hoặc database chứa thông tin khách.

Đây vẫn là ứng dụng chạy cục bộ. Hai chi nhánh truy cập qua Internet cần một bước triển khai riêng với HTTPS, quản lý tài khoản và sao lưu. Lộ trình học chi tiết ở `LO-TRINH-HOC-VA-LAM.md`.
