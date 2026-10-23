# Bán vé và lịch xe

## Cách dùng

Khởi động lại website bằng `npm.cmd run dev:watch` tại thư mục chứa file này. Nếu cổng 3010 đã có website, dừng bằng Ctrl+C trong cửa sổ đang chạy rồi khởi động lại ở cùng thư mục, không mở thêm bản thứ hai. Backend tự thêm bảng mới và giữ dữ liệu cũ.

1. Đăng nhập → **Bán vé & lịch xe**.
2. Chọn **ngày xuất phát** và **Sài Gòn** hoặc **Quảng Nam / Tam Kỳ**.
3. Xe đúng chiều hiện sơ đồ 24 khoang: tầng dưới `1A1–1A6`, `1B1–1B6`; tầng trên `2A1–2A6`, `2B1–2B6`. Xe ngược chiều vẫn có thẻ để quản lý xem lịch, không bán trong chiều đang chọn.
4. Chọn một khoang trống, số người, tên và SĐT khách, điểm đón/trả. Ghi thêm địa chỉ trung chuyển cụ thể và tên người thứ hai nếu cần.
5. Chọn **Chưa thu tiền** hoặc **Đã thu đủ tiền**, rồi xác nhận. Hệ thống trả mã vé và khóa nguyên khoang.
6. Vé chưa thu có nút **Thu tiền**. Chỉ bấm sau khi thực nhận đủ tiền.

| Số người | Giá toàn bộ khoang |
|---|---:|
| 1 | 800.000đ |
| 2 | 1.200.000đ |

Một vé chỉ bán một khoang. Khách đi một người vẫn giữ cả khoang, không ghép thêm khách lạ. Muốn mua nhiều khoang, tạo từng vé. Chọn một ô chưa giữ chỗ trên server; chỉ xác nhận lưu thành công mới có vé. Vé do nhân viên nhập giữ khoang đến khi admin hủy. Vé khách tự đặt ở /dat-ve giữ chỗ 20 phút; chưa thanh toán thì tự hủy.

## Lịch và cho xe nghỉ

| Xe | Ngày chẵn | Ngày lẻ |
|---|---|---|
| Xe 1 — 0868612311 | Quảng Nam → Sài Gòn | Sài Gòn → Quảng Nam |
| Xe 2 — 0868612312 | Sài Gòn → Quảng Nam | Quảng Nam → Sài Gòn |
| Xe 3 — 0868612313 | Admin chọn lịch trước khi bán | Admin chọn lịch trước khi bán |

Chẵn/lẻ là **số ngày trong tháng**, không phải thứ trong tuần hoặc luân phiên cách một ngày liên tục. Ngày 31 rồi ngày 1 đều lẻ. Admin cần kiểm tra vị trí xe và thời gian quay đầu, dùng lịch riêng nếu lịch mặc định không phù hợp. Phần mềm chưa mô phỏng thời gian hành trình hay vị trí GPS.

Admin chọn **Lịch xe / nghỉ / số khoang**:

- **Trạng thái chung**: hoạt động hoặc nghỉ/ngừng bán đến khi bật lại.
- **Lịch thường lệ**: từ Quảng Nam ngày chẵn, ngày lẻ hoặc chưa có lịch.
- **Riêng ngày đang chọn**: theo mặc định, xuất phát Quảng Nam, xuất phát Sài Gòn, hoặc nghỉ ngày đó. Lịch riêng không vượt qua trạng thái nghỉ chung.
- **Mã khoang**: sửa khi cấu hình xe thực tế thay đổi. Không xóa khoang đang có vé chưa hủy từ hôm nay trở đi.

Cho xe nghỉ **không tự hủy vé, không tự chuyển khách và không tự hoàn tiền**. Thẻ xe cảnh báo vé cần xử lý ở ngày/chiều đang xem; quản lý kiểm tra các ngày đã bán, liên hệ khách và xử lý từng vé. Đổi chiều gây xung đột với vé chưa hủy bị từ chối. Lịch và trạng thái dùng phiên bản để tránh một màn hình cũ ghi đè thay đổi mới.

## Điểm đón / trả

Dữ liệu lấy từ danh sách người dùng cung cấp, gồm 12 điểm đón Sài Gòn, 13 điểm trả Quảng Nam; chiều về gồm 22 lựa chọn đón Quảng Nam và 11 điểm trả Sài Gòn. Tam Thành 12:45 trực tiếp và 15:00 trung chuyển là hai lựa chọn riêng. Hội An và Cầu Cửa Đại có đánh dấu trung chuyển theo thông tin được gửi.

Các điểm sau nửa đêm dùng ngày đi + 1 ngày, xử lý cả cuối tháng và cuối năm. Ví dụ xuất phát Sài Gòn 31/12 → Tam Kỳ 23:50 ngày 31/12; Văn phòng Quảng Nam 02:20 ngày 01/01. Đây là giờ dự kiến, không phải cam kết thời gian thực tế.

Giờ **đón tại Văn phòng Sài Gòn** chưa được cung cấp nên hiển thị cần xác nhận. Giờ **trả tại Văn phòng Sài Gòn 03:20 ngày kế** được giữ đúng dữ liệu cung cấp, dù sớm hơn các điểm trả khác trong danh sách; nhà xe cần xác nhận tính phù hợp trước khi vận hành. Địa chỉ cũng giữ theo thông tin nhà xe, chưa xác minh địa giới/địa chỉ mới. Có lựa chọn địa chỉ khác đã thỏa thuận; giờ của địa chỉ tự nhập cần xác nhận với khách.

Các điểm và giờ được lưu bản sao trong vé để sửa danh mục sau này không thay đổi vé cũ. Hiện chỉnh danh mục gốc tại `nha-xe-v1/ticket_routes.py`; chưa có giao diện quản lý danh mục điểm dừng.

Không bán ngày đã qua. Với điểm đón có giờ, server cũng chặn bán mới khi giờ đón hôm nay đã qua; điểm tự thỏa thuận/chưa có giờ cần nhân viên xác nhận thủ công.

## Cập nhật khoang và thu chi

- Giao diện tải lại mỗi 5 giây sau mỗi lần nhận kết quả, khi quay lại cửa sổ và sau khi lưu. Mạng chậm có thể làm thời gian dài hơn; đây là tải định kỳ, chưa dùng WebSocket.
- Lúc lưu, server kiểm tra xe, lịch, ngày, khoang và giá lại trong một giao dịch ghi. Ràng buộc database chỉ cho một vé chưa hủy trên mỗi xe + ngày + khoang. Hai người bán cùng ô thì chỉ một người thành công.
- Mỗi yêu cầu đặt có mã riêng. Gửi lại cùng yêu cầu không tạo vé hoặc khoản thu thứ hai; gửi mã cũ với nội dung khác bị từ chối.
- Vé chưa thu chưa ghi tiền. Vé đã thu hoặc bấm Thu tiền tạo đúng một khoản thu trong `cash_entries`, gắn với tài khoản thực hiện và chi nhánh xuất phát. Tổng thu chi hôm nay/14 ngày/tháng có cả tiền vé và tiền hàng; báo cáo cước hàng phía dưới vẫn chỉ tính hàng gửi.
- Admin hủy vé cần lý do. Vé đã thu chỉ được hủy khi admin xác nhận **đã hoàn đủ tiền**, lúc đó tạo khoản chi hoàn tiền ở thời điểm hủy. Đây là ghi nhận thu/hoàn thủ công, không có chuyển khoản tự động. Chưa hỗ trợ cọc, hoàn một phần, đổi ngày hoặc đổi khoang trực tiếp.
- Nhân viên chỉ bán và thu vé xuất phát tại chi nhánh tài khoản. Admin thao tác cả hai chiều, chỉnh lịch và hủy vé. Mọi API yêu cầu đăng nhập; thay đổi dữ liệu cần mã CSRF.

## Code đi qua đâu?

`ticket-workspace.tsx → lib/api.ts → Next chuyển tiếp /api → app.py → tickets.py → SQLite`

| File/bảng | Trách nhiệm |
|---|---|
| `nha-xe-web/components/ticket-workspace.tsx` | Bộ lọc ngày/chiều, sơ đồ tầng, biểu mẫu bán, danh sách vé, điều hành xe |
| `nha-xe-v1/tickets.py` | Giá, lịch, bán/thu/hủy vé, kiểm tra trùng, migration |
| `nha-xe-v1/ticket_routes.py` | Điểm đón/trả, giờ và ngày đến tương đối |
| `bus_sales` | Trạng thái mở bán, quy luật chẵn/lẻ, danh sách khoang từng xe |
| `bus_days` | Lịch ngoại lệ theo xe và ngày |
| `tickets` | Vé, khách liên hệ, khoang, giá chốt, bản sao điểm dừng và trạng thái |
| `ticket_audit`, `fleet_audit` | Ai đã bán/thu/hủy hoặc chỉnh lịch, lúc nào |
| `cash_entries.ticket_id` | Liên kết thu/hoàn với vé, ngăn ghi trùng |
| `nha-xe-v1/test_tickets.py` | Kiểm thử API trên database tạm |

Hợp đồng API: `GET /api/tickets?day=YYYY-MM-DD&origin=SG|TK` đọc lịch và tình trạng. Các POST `/api/tickets/book`, `/collect`, `/cancel` thao tác vé; `/config` và `/day` chỉnh cấu hình/lịch xe. Giá gửi từ trình duyệt không quyết định số tiền; backend tự tính theo số người.

Kiểm tra: tại `nha-xe-v1`, chạy `python -m unittest test_app test_tickets -q`; tại thư mục gốc ứng dụng chạy `npm.cmd run build`.

Đây là màn hình bán vé nội bộ cho nhân viên/admin. Chưa có cổng khách tự thanh toán, SMS, in vé chuyên dụng hoặc đồng bộ tồn kho với Vexere. Vé bán bên Vexere không tự khóa khoang tại đây; cần thống nhất nguồn quản lý chỗ trước khi dùng đồng thời hai hệ thống.


## Trang khách hàng và email
Nhà xe Thanh Tĩnh có trang `/dat-ve` không cần tài khoản, chỉ hiện ngày, chiều đi và khoang, không hiện xe. Máy chủ tự chọn xe còn chỗ đúng lịch. Nhân viên dùng mục Bán vé; sổ và thao tác thu tiền nằm ở Sổ vé nội bộ. Khách không tự xác nhận thanh toán. Xem EMAIL-XAC-NHAN.md để bật gửi thư. SMS chưa bật.
