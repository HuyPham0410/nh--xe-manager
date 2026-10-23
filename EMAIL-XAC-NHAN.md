# Email xác nhận — Nhà xe Thanh Tĩnh

Địa chỉ gửi dự kiến: giahuyphamm@gmail.com. Cấu hình đã chuẩn bị trong `.env`, nhưng chưa có mật khẩu ứng dụng nên chưa gửi thư thật.

1. Chủ tài khoản Google tạo mật khẩu ứng dụng theo hướng dẫn chính thức: https://support.google.com/accounts/answer/185833 (cần bật xác minh 2 bước; một số tài khoản không có tùy chọn này).
2. Mở `.env` trên máy chủ, điền mật khẩu ứng dụng vào `SMTP_PASSWORD`. Không gửi mật khẩu trong chat, không dùng mật khẩu đăng nhập Gmail, không đưa `.env` lên Git.
3. Khởi động lại dịch vụ đang chạy. Không mở thêm bản thứ hai trên cùng cổng.
4. Đặt vé thử bằng email bạn kiểm soát, kiểm tra cả hộp thư Spam. Chỉ xác nhận thu tiền khi đã nhận tiền thật.

Khách mở `/dat-ve`, chọn ngày, chiều đi, khoang, điểm đón/trả và email. Máy chủ chọn xe phù hợp. Vé công khai chưa thanh toán giữ chỗ 20 phút rồi hết hạn. Thanh toán vẫn do nhân viên xác nhận, chưa tích hợp cổng thanh toán.

Vé và yêu cầu gửi thư được lưu trong cùng giao dịch SQLite. Tác vụ nền đọc `ticket_messages` để gửi qua Gmail SMTP SSL cổng 465. Khi chưa cấu hình, trạng thái là `not_configured`. Sau khi cấu hình, quản lý gửi lại từ Sổ vé nội bộ. `accepted` chỉ nghĩa dịch vụ đã nhận thư, chưa đảm bảo khách nhận. `unknown` cần kiểm tra hộp thư/dịch vụ trước khi gửi lại để tránh trùng. Nội dung gồm mã vé, hành trình, khoang, số người, giá, điểm đón/trả và trạng thái thanh toán; không hiện xe.

SMS chưa triển khai cho khách. Link 127.0.0.1 chỉ dùng trên máy đang chạy; cần triển khai máy chủ và HTTPS trước khi chia sẻ cho khách bên ngoài.
