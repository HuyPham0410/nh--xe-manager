# Nhà xe Thanh Tĩnh

Vẫn còn đang trong giai đoạn phát triển và thử nghiệm.

Thư mục này là gốc kho Git riêng của ứng dụng. Chạy toàn bộ lệnh bên dưới tại đây. CV và tài liệu cá nhân nằm ngoài kho. Xem [hướng dẫn Git](GIT.md).

Project thực hành từng bước để xây sổ hàng gửi dùng được trong thực tế.

Đã có mục **Xe & nhân viên**: ba xe định danh bằng SĐT 0868612311–0868612313, hồ sơ lái/phụ và phân công mỗi xe 2 lái + 2 phụ. Admin quản lý, nhân viên xem; xem [hướng dẫn sử dụng và giải thích code](QUAN-LY-XE-VA-NHAN-VIEN.md).

Mục **Bán vé & lịch xe** có 24 khoang/xe, vé 800.000đ cho 1 người hoặc 1.200.000đ cho 2 người, lịch chẵn/lẻ, điểm đón/trả hai chiều, thu/hoàn tiền và cho xe nghỉ. Xem [hướng dẫn bán vé và lịch xe](BAN-VE-VA-LICH-XE.md). Xe 3 cần admin chọn lịch trước khi mở bán.

Đã có chuyển đơn Chờ đi sang ngày kế khi xe đầy (nhập xe nhận thay, giữ ngày nhận và tiền thu gốc). Khung Tổng thu chi hỗ trợ Hôm nay, 14 ngày và tháng lịch. Xem thao tác chi tiết trong `CACH-FOLDER-VAN-HANH.md`.

Hướng dẫn ngắn về từng file, cách khởi động và luồng xử lý: [Cách folder vận hành](CACH-FOLDER-VAN-HANH.md).

Mỗi tài khoản nhân viên hiện có **Thu chi hôm nay**: tiền do chính tài khoản thu, khoản chi có lý do và chênh lệch Thu − Chi. Admin xem tổng cả hai đầu hoặc theo chi nhánh. Tính năng nằm ở giao diện Next.js; số liệu được kiểm soát quyền tại backend. Tổng thu chi không phải số dư quỹ hoặc lợi nhuận. Chưa có sửa/hủy khoản chi.

## Chạy cả website từ thư mục này

Yêu cầu: Node.js 22.12+ và Python 3.11+.

Lần đầu: `npm.cmd ci`, rồi `npm.cmd run setup`. Sau đó chạy `npm.cmd run dev`, hoặc mở `CHAY-NHA-XE.bat`. Truy cập http://127.0.0.1:3000. Một lệnh khởi động cả backend Python và frontend Next.js; Ctrl+C dừng cả hai tiến trình do lệnh này tạo.

Nếu trước đó đã chạy riêng backend ở cổng 8765 hoặc frontend ở cổng 3000, hãy dừng cửa sổ chạy cũ trước. Bộ khởi động báo lỗi cổng bận và không tự tắt tiến trình có sẵn. Tài khoản vẫn nằm trong `nha-xe-v1/TAI-KHOAN.txt`.

`.env` ở thư mục gốc cấu hình PORT, BACKEND_PORT và PYTHON_COMMAND. Nếu Python không có trong PATH, đặt PYTHON_COMMAND thành đường dẫn tới python.exe. Không thêm tham số vào giá trị này. Có thể sao chép `.env.example` khi thiết lập máy mới; giữ nguyên `.env` nếu đã có cấu hình.

| Lệnh tại thư mục gốc | Công dụng |
|---|---|
| `npm.cmd run dev` | Chạy backend và frontend, Next tự cập nhật giao diện khi sửa code |
| `npm.cmd run dev:watch` | Node tự khởi động lại bộ dịch vụ khi sửa server.js, backend hoặc .env; dành Windows/macOS |
| `npm.cmd run build` | Build Next với cổng backend lấy từ .env |
| `npm.cmd start` | Chạy bản Next đã build cùng backend cục bộ |
| `npm.cmd test` | Kiểm thử cấu hình bộ khởi động |
| `npm.cmd run test:smoke` | Khởi động thử ở cổng 13000/18765, kiểm tra API và dừng cả hai dịch vụ; không tạo đơn hàng |
| `npm.cmd run typecheck` | Kiểm tra TypeScript frontend |

Đổi BACKEND_PORT thì build lại trước `npm start`, vì Next lưu đích proxy trong bản build. `npm start` vẫn là chạy thử cục bộ: backend Python hiện tại chưa phải máy chủ production. Các dịch vụ chỉ lắng nghe 127.0.0.1.

## Các file bạn cung cấp

Đã giữ nguyên bản sao của 8 file portfolio trong `../../references/portfolio-config/`, gồm cả `.env`. Toàn bộ thư mục tham khảo bị loại khỏi Git; không chia sẻ file `.env` gốc. Nguồn ở `C:/Users/giahu/newwork/HenryPham-git` không bị thay đổi.

Ở thư mục gốc này, `.env`, `.env.example`, `.gitignore`, `package.json`, `package-lock.json`, `server.js`, `nodemon.json` và README được điều chỉnh cho nhà xe. Không dùng package-lock của portfolio để cài dependencies cho nhà xe, vì hai ứng dụng có bộ thư viện khác nhau. `server.js` mới điều phối Python và Next, không yêu cầu `./src/server` của portfolio. Node đọc `.env` trực tiếp, không cần dotenv.

`nodemon.json` là cấu hình tham khảo tùy chọn, không thuộc đường chạy được hỗ trợ hiện tại. Nodemon đã được bỏ khỏi dependencies sau khi npm báo cảnh báo bảo mật ở chuỗi phụ thuộc; `dev:watch` dùng Node watch tích hợp.

Đã xác minh: build Next/TypeScript thành công; 3 kiểm thử cấu hình đạt; phép thử khởi động thật xác nhận cả backend và proxy Next trả 401 khi chưa đăng nhập, sau khi dừng cả hai cổng đều được giải phóng. Phép thử HTTP cần quyền kết nối localhost ngoài sandbox. Chưa kiểm tra trực quan lại toàn bộ giao diện trong lần tích hợp này.

1. Đọc [lộ trình học và làm](LO-TRINH-HOC-VA-LAM.md).
2. Chạy backend theo [hướng dẫn bản đầu](nha-xe-v1/README.md).
3. Chạy giao diện React/Next.js theo [hướng dẫn frontend](nha-xe-web/README.md).

Hiện tại: Next.js + React + TypeScript ở frontend; Python + SQLite ở backend. Hướng tiếp theo: chuyển backend sang NestJS, dữ liệu sang PostgreSQL sau khi hiểu và kiểm thử được luồng hiện có.

Các file trong `../../sources/` là tài liệu tham chiếu chỉ đọc.
