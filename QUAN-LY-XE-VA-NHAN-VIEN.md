# Xe và nhân viên — cách dùng và cách code vận hành

## Sử dụng

1. Mở terminal tại thư mục chứa file này. Nếu website đang chạy bản cũ, Ctrl+C trong đúng cửa sổ đang chạy rồi chạy lại `npm.cmd run dev:watch`. Không chạy thêm một bản trên cùng cổng.
2. Đăng nhập admin, chọn **Xe & nhân viên**.
3. Lần đầu backend khởi động bản mới, hệ thống tạo Xe 1 — 0868612311, Xe 2 — 0868612312, Xe 3 — 0868612313. Không tự điền biển số hoặc tên nhân viên giả.
4. Chọn **Thêm nhân viên**, nhập họ tên, SĐT, vai trò Lái xe / Phụ xe. Cần ít nhất 6 lái và 6 phụ đang làm việc để đủ cả ba xe.
5. Chọn **Phân công** trên mỗi xe, chọn 2 lái và 2 phụ rồi lưu. Có thể thay người bằng cách chọn lại cả tổ. **Bỏ phân công** giải phóng cả 4 vị trí của xe.
6. **Sửa xe** đổi tên, SĐT hoặc bổ sung biển số. SĐT xe không được trùng nhau. Mã số nội bộ của xe không thay đổi khi sửa SĐT, nên tổ xe vẫn gắn đúng xe.
7. **Sửa nhân viên** cập nhật liên hệ, vai trò hoặc trạng thái đã nghỉ. Muốn đổi vai trò / cho nghỉ người đang được phân công, phải thay người hoặc bỏ phân công trước.

Nhân viên đăng nhập chỉ xem danh bạ và tổ xe; admin có quyền sửa. Hồ sơ lái/phụ không tự tạo tài khoản đăng nhập. Dữ liệu mới xuất hiện khi mở mục này hoặc bấm **Tải lại**; chưa tự cập nhật tức thời giữa hai máy. Tải lại đóng biểu mẫu đang sửa.

## Một lần bấm Lưu đi qua những đâu?

`Giao diện React → API qua Next.js → Python kiểm tra → SQLite lưu → React tải lại danh sách`

| File | Trách nhiệm |
|---|---|
| `nha-xe-web/components/cargo-workspace.tsx` | Menu chính, đăng nhập, chuyển sang mục Xe & nhân viên |
| `nha-xe-web/components/fleet-workspace.tsx` | Thẻ xe, danh sách nhân viên, biểu mẫu sửa và phân công |
| `nha-xe-web/lib/api.ts` | Gửi yêu cầu, cookie đăng nhập và mã CSRF; đọc lỗi server |
| `nha-xe-v1/app.py` | Kiểm tra đăng nhập / quyền quản lý; chuyển yêu cầu sang module fleet |
| `nha-xe-v1/fleet.py` | Tạo bảng, tạo ba xe lần đầu, kiểm tra và lưu nghiệp vụ |
| `nha-xe-v1/data.sqlite3` | File cơ sở dữ liệu hiện tại trên máy chạy backend |
| `nha-xe-v1/test_app.py` | Kiểm thử bằng máy chủ HTTP và cơ sở dữ liệu tạm |

“Hợp đồng API” ở phần này là thỏa thuận về đường dẫn và cấu trúc dữ liệu:

- `GET /api/fleet`: trả `{buses: [...], employees: [...]}` cho người đã đăng nhập.
- `POST /api/fleet/employee`: tạo với `name, phone, role, active`; khi sửa cần thêm `id, version`. `role` là `driver` hoặc `assistant`; `active` là true/false.
- `POST /api/fleet/bus`: sửa `id, version, name, phone, plate`.
- `POST /api/fleet/crew`: gửi `id, version, crew`. Ví dụ `crew` gồm `driver1, driver2, assistant1, assistant2`, mỗi giá trị là mã nhân viên. `{}` nghĩa là bỏ phân công toàn bộ.

Ví dụ ý nghĩa: giao diện gửi “xe số 1, phiên bản 2, phân công bốn người có mã 1–4”. Backend kiểm tra những mã đó có tồn tại, còn làm việc, đúng vai trò và có đang thuộc xe khác không. Khi hợp lệ, server lưu rồi tăng phiên bản xe lên 3. Nếu người khác vẫn gửi phiên bản 2, server yêu cầu tải lại thay vì ghi đè.

## Dữ liệu và bảo vệ khi cùng thao tác

- `buses`: hồ sơ 3 xe; `employees`: hồ sơ lái/phụ.
- `bus_crew`: bốn vị trí trên một xe. Ràng buộc UNIQUE ngăn một người xuất hiện trên hai xe hoặc hai vị trí.
- `fleet_audit`: ghi người thực hiện, thời điểm, dữ liệu trước/sau mỗi lần lưu thành công. Hiện lưu trong database, chưa có màn hình xem riêng.
- `fleet_migrations`: đánh dấu đã tạo ba xe, để khởi động lại không ghi đè thông tin quản lý đã sửa.
- `BEGIN IMMEDIATE`: lấy quyền ghi trước khi kiểm tra và lưu. Toàn bộ thay đổi cùng nhật ký nằm trong một giao dịch: lỗi thì không lưu dở dang.
- Kiểm tra quyền và mã CSRF ở server; giấu nút sửa ở giao diện chỉ là hỗ trợ trải nghiệm.

## Phạm vi hiện tại

Đây là danh bạ và **tổ xe hiện tại**. Lịch chạy và trạng thái nghỉ/mở bán nằm ở mục **Bán vé & lịch xe**; vé đã liên kết với xe. Xem [hướng dẫn bán vé](BAN-VE-VA-LICH-XE.md). Chưa có lịch đổi ca nhân viên theo chuyến, chấm công, lương, bằng lái hết hạn hoặc bảo dưỡng. Trường xe nhận hàng thay ở sổ hàng vẫn là văn bản riêng. Chưa có thêm/xóa xe ngoài ba xe ban đầu trong giao diện.

## Tự kiểm tra khi học

Tại thư mục `nha-xe-v1`, chạy `python -m unittest test_app -q`. Kiểm thử dùng database tạm, không thêm nhân viên thử vào dữ liệu thật. Tại thư mục gốc ứng dụng, chạy `npm.cmd run build` để kiểm tra frontend và tạo bản build.

Các tình huống được kiểm thử: tạo đủ ba tổ 2 lái + 2 phụ; phân quyền; mã CSRF; trùng vai trò/người; nhân viên đã nghỉ; dữ liệu cũ; hai yêu cầu cạnh tranh cùng người; khởi động lại không làm mất sửa đổi. Kiểm thử tự động không thay thế chạy thử thao tác thực tế trên điện thoại và máy tính trước khi dùng chính thức.
