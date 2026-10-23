# Sổ nhà xe — bản chạy đầu tiên

Đã có bước học tiếp theo: giao diện React/TypeScript/Next.js ở `../nha-xe-web`, dùng lại API và dữ liệu bản này. Xem `../LO-TRINH-HOC-VA-LAM.md` để học theo từng mốc. Mở bản mới ở cổng 3000; cổng 8765 vẫn là backend và giao diện tham chiếu.

Phần dưới mô tả sổ hàng bản đầu. Backend đã bổ sung xe/nhân viên trong `fleet.py` và bán vé/lịch chạy trong `tickets.py`, điểm đón/trả trong `ticket_routes.py`. Các tính năng mới dùng giao diện Next.js; xem `../BAN-VE-VA-LICH-XE.md`.

## Chạy trên Windows

1. Cài Python 3.11 trở lên nếu máy chưa có.
2. Mở `CHAY.bat` trong thư mục này. Giữ cửa sổ đó mở.
3. Vào http://127.0.0.1:8765 bằng trình duyệt trên cùng máy.
4. Mở `TAI-KHOAN.txt` được sinh ở lần chạy đầu để lấy mật khẩu. Có admin, nhanvien_sg, nhanvien_tk. Mỗi tài khoản dùng mật khẩu ngẫu nhiên riêng.

Không cần cài thư viện ngoài. Không có dữ liệu khách hàng mẫu trong cơ sở dữ liệu thật. Dữ liệu kiểm thử nằm trong thư mục tạm, được xóa sau kiểm thử.

## Dùng thử

- Đăng nhập nhân viên SG, nhận hàng: SĐT, tên, mô tả tự do, số lượng, cước, thanh toán, nơi giao, ghi chú. Sau khi lưu, form trống để nhập tiếp.
- Hướng gửi tự lấy theo tài khoản. Ngày nhận tự lấy giờ Việt Nam.
- Đăng xuất, dùng nhân viên TK, vào Tìm hàng để tìm xuyên mọi ngày. Bấm Đã tới, Thu tiền khi đã nhận tiền thật, rồi Đã giao. Đơn trả đầu kia bắt buộc thu tiền trước khi giao; đơn cho nợ được giao khi chưa thu.
- Admin xem Tiền & lịch sử, xuất CSV tương thích Excel. Chọn ngày ở tab Hàng gửi trước khi vào báo cáo. Báo cáo không chọn ngày sẽ dùng hôm nay.
- In danh sách sẽ in các kết quả đang hiển thị, tối đa 1.000 đơn. Nếu nhiều hơn, giao diện yêu cầu thu hẹp kết quả. CSV của admin xuất đầy đủ đơn của ngày đã chọn.

## Cách xây dựng

- `app.py`: máy chủ HTTP Python, API JSON, đăng nhập, kiểm tra quyền và quy tắc nghiệp vụ.
- `static/index.html`: form và bảng tiếng Việt; `style.css`: giao diện responsive, chữ lớn và bố cục in giấy; `app.js`: gửi yêu cầu API và cập nhật màn hình.
- `data.sqlite3`: dữ liệu SQLite lưu trên đĩa, có các bảng users, cargo, audit. Chưa tạo bảng tương lai để tránh cấu trúc không dùng đến.
- SQL dùng tham số, giá tiền là số nguyên đồng. Mật khẩu băm PBKDF2 SHA256 310.000 vòng với salt riêng. Cookie HttpOnly/SameSite, token chống CSRF, phiên 8 giờ, giới hạn đăng nhập sai.
- Cập nhật đơn và lịch sử nằm trong cùng giao dịch. Thao tác chuyển trạng thái/thu tiền dùng khóa ghi để chặn hai yêu cầu thu trùng. Màn hình dựng nội dung khách bằng textContent để tránh thực thi HTML nhập vào.
- Không dùng AI, dịch vụ cloud hoặc thư viện frontend trong hoạt động của ứng dụng.

## Báo cáo và phạm vi quyền

Nhân viên cả hai chi nhánh được tra cứu tất cả hàng để trả lời khách. Chỉ chi nhánh đích hoặc admin được đánh dấu đến, giao và thu tiền. Nhân viên không được gọi API báo cáo/xuất tiền. Giao diện Next.js có bộ chọn Tất cả / Sài Gòn / Tam Kỳ cho admin; khi nhận hàng admin chọn được chi nhánh gửi. Tài khoản nhân viên vẫn bị máy chủ cố định chi nhánh khi tạo đơn. Giao diện HTML tham chiếu cũ chưa có bộ chọn này.

Tổng cước = cước các đơn tạo trong ngày chọn, theo chi nhánh gửi khi có lọc. Thực thu = số tiền xác nhận thu trong ngày chọn tại chi nhánh thu tiền, kể cả đơn tạo ngày trước hoặc gửi từ đầu kia. Đầu kia chưa thu và nợ chưa thu = dư chưa thu hiện tại của các đơn tạo ngày chọn tại chi nhánh gửi, không phải ảnh chụp số dư lịch sử tại cuối ngày. Tất cả sẽ gộp hai chi nhánh. CSV và lịch sử được lọc theo chi nhánh gửi. Tiền ghi nhận một lần cho toàn bộ đơn, chưa hỗ trợ trả một phần. Admin bấm thu sau khi nhận đơn sẽ ghi nhận tại chi nhánh đích; tiền đã trả lúc tạo đơn ghi tại chi nhánh gửi. Các bản ghi thu tiền cũ không bị sửa tự động.

## Kiểm chứng

Chạy `python -m unittest -v test_app.py` và `node --check static/app.js` (nếu có Node). Kiểm thử tích hợp đi qua HTTP thật trên cơ sở dữ liệu tạm: xác thực, chống CSRF, kiểm tra cước âm, không tin chi nhánh do trình duyệt gửi, tra cứu, phân quyền, chuyển trạng thái, chặn giao chưa thu, chặn thu trùng, tổng tiền, lịch sử và đăng xuất.

## Tự review và đánh giá

Các lỗi đã tìm và sửa: kết nối SQLite chưa đóng hoàn toàn gây khóa file trên Windows; thông báo khởi động có dấu gây lỗi với terminal dùng cp1252. Đã chạy lại kiểm thử nghiệp vụ sau sửa đóng kết nối.

Điểm mạnh: luồng nhập ngắn; dữ liệu bền vững; quy tắc kiểm tra ở máy chủ; lịch sử thao tác; phân biệt cước và thực thu; không phụ thuộc gói bên ngoài.

Hạn chế cần xử lý trước vận hành thật:

1. Máy chủ chuẩn Python chỉ dành chạy thử trên một máy, chỉ lắng nghe localhost. Điện thoại và hai chi nhánh chưa dùng chung dữ liệu. Cần dịch vụ triển khai có HTTPS, giám sát và cơ chế chạy bền vững.
2. Chưa có đổi mật khẩu, khôi phục tài khoản, tạo/khóa nhân viên. File mật khẩu khởi tạo cần giữ kín; người có quyền đọc ổ đĩa có thể đọc file này. Phiên và bộ đếm đăng nhập sai nằm trong bộ nhớ, mất khi khởi động lại.
3. Chưa có sửa/hủy đơn, hoàn tiền, trả một phần, thu nợ theo khách, chốt sổ hoặc chống nhấn gửi lại sau lỗi mạng. Nút lưu bị khóa trong lúc gửi, nhưng chưa có khóa idempotency phía máy chủ cho tạo đơn.
4. Chưa có sao lưu tự động/khôi phục được kiểm chứng. Khi sao lưu thủ công phải dừng ứng dụng rồi sao chép cả thư mục, đặc biệt data.sqlite3 và các file WAL nếu còn. Không lấy CSV thay cho bản sao lưu.
5. Chưa có autocomplete xếp theo tần suất; hiện chỉ gợi ý cố định. Tìm theo tên chưa hỗ trợ bỏ dấu tiếng Việt. Chưa phân trang; giới hạn 1.000 kết quả được thông báo rõ.
6. Lịch sử giao diện hiển thị 100 thao tác gần nhất toàn hệ thống. Cơ sở dữ liệu lưu trước/sau, nhưng giao diện chưa hiển thị chi tiết chênh lệch; chưa có sửa cước.
7. Chưa kiểm chứng trực quan đầy đủ trên điện thoại, máy in, người dùng thật; chưa thử tải lớn và chưa có bài kiểm thử cạnh tranh nhiều máy khách. Không có chế độ offline.
8. Chưa có tổng tiền riêng cho nhân viên, chi tiết tiền theo chi nhánh hay bộ lọc ngày độc lập trong tab báo cáo. Chưa có nhập dữ liệu sổ cũ.

Đánh giá kỹ thuật chủ quan: khoảng 7/10 cho bản thử Phase 1 trên một máy; khoảng 3/10 cho khả năng vận hành thật tại hai chi nhánh. Đây không phải tỷ lệ bảo đảm chất lượng. Không gọi hệ thống hoàn hảo: mới có một kịch bản kiểm thử tích hợp với nhiều kiểm tra, chưa thay thế nghiệm thu thực tế.

Nên cho 1–2 nhân viên thử với đơn giả, đo thời gian nhập và đối chiếu tiền. Sau đó bổ sung quản lý mật khẩu, sửa/hủy có lịch sử, sao lưu và triển khai dùng chung trước khi nhập dữ liệu khách thật. Vé và chuyến xe theo Phase 2–3.
