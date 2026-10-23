# Sổ nhà xe — bước học React / Next.js

Frontend mới dùng React, TypeScript và Next.js App Router. Backend vẫn là Python/SQLite trong `../nha-xe-v1`. Đây là bước chuyển dần có chủ đích: học một lớp tại một thời điểm và có bản trước để đối chiếu.

## Admin quản lý hai đầu

Trên thanh chức năng có bộ chọn **Tất cả hai đầu / Sài Gòn / Tam Kỳ**. Chọn một chi nhánh để lọc hàng gửi từ đó, hoặc chuyển **Chiều hàng** sang hàng đến đó. Báo cáo và CSV áp dụng chi nhánh đang chọn; báo cáo ghi rõ cước theo đầu gửi và thực thu theo nơi nhận tiền. Khi đang xem Tất cả, form Nhận hàng yêu cầu chọn chi nhánh; chọn một đầu trước thì form điền sẵn chiều gửi và vẫn cho admin đổi. Nhân viên không có bộ chuyển quyền này.

Ví dụ: đơn Sài Gòn → Tam Kỳ, cước 30.000đ, trả đầu kia. Cước thuộc báo cáo hàng gửi Sài Gòn; khi thu thì 30.000đ thuộc thực thu Tam Kỳ, kể cả admin xác nhận. Không sửa tự động những bản ghi thu tiền cũ.

Kiểm thử bổ sung đã đạt: admin tạo ở mỗi đầu; lọc hàng gửi/hàng đến; tiền trả trước và trả đầu kia vào đúng chi nhánh; CSV/lịch sử đúng đầu; từ chối chi nhánh không hợp lệ; nhân viên không đổi được chi nhánh bằng cách gửi dữ liệu giả.

## Chạy

Yêu cầu: Python 3.11+ và Node.js phù hợp phiên bản Next trong package-lock. Máy dùng để phát triển hiện có Node 22.12.0.

1. Chạy `../nha-xe-v1/CHAY.bat` và giữ backend tại `127.0.0.1:8765` hoạt động.
2. Tại thư mục `nha-xe-web`, chạy `npm.cmd ci` khi cài lần đầu hoặc sau khi lockfile thay đổi.
3. Chạy `npm.cmd run dev`.
4. Mở http://127.0.0.1:3000. Dùng tài khoản trong `../nha-xe-v1/TAI-KHOAN.txt`.

Hai giao diện cùng dùng một SQLite; đơn tạo ở frontend mới xuất hiện ở bản cũ. Không nhập đơn thử lẫn vào dữ liệu thật nếu bạn đã bắt đầu vận hành.

## Kiến trúc hiện tại

```text
Trình duyệt :3000
  → React component
  → lib/api.ts gọi /api/*
  → Next.js rewrite cùng origin
  → Python API :8765 kiểm tra phiên, quyền và dữ liệu
  → SQLite: users, cargo, audit
```

Next chuyển tiếp API để giữ cookie cùng origin. Đây là proxy phát triển cục bộ, không phải một backend NestJS đã hoàn thành. Session cookie hiện vẫn dùng HTTP localhost; khi triển khai thật phải có HTTPS và cấu hình cookie tương ứng. Không công khai hai cổng dev.

## Cách đọc code

- `app/layout.tsx`: ngôn ngữ trang, metadata, CSS chung.
- `app/page.tsx`: route `/`.
- `components/cargo-workspace.tsx`: điều phối phiên đăng nhập, tab, ngày, tìm kiếm và các hành động.
- `components/login-form.tsx`: form đăng nhập với loading/error.
- `components/cargo-form.tsx`: nhận hàng liên tục, form và focus.
- `components/cargo-table.tsx`: hiển thị props, phát callback hành động.
- `components/daily-report.tsx`: tải báo cáo theo ngày.
- `lib/types.ts`: kiểu dữ liệu và union types.
- `lib/api.ts`: fetch có CSRF/cookie, xử lý HTTP errors và AbortSignal.
- `lib/format.ts`: định dạng tiền và nhãn tiếng Việt.

Quyền trong UI chỉ để hiển thị nút. Máy chủ vẫn quyết định quyền thực sự. TypeScript giúp kiểm tra lúc viết/build, không thay thế validate dữ liệu nhận qua mạng.

## Tự review thay đổi

Đã chuyển thao tác DOM trực tiếp thành state/props/JSX. Kết quả tìm kiếm cũ được hủy khi đổi bộ lọc; trạng thái loading không hiển thị bảng cũ như thể là kết quả mới. Nút thu tiền/lưu bị khóa trong lúc request. Modal dùng dialog native để hỗ trợ focus; không đóng bằng Escape trong lúc lưu. Bộ lọc ngày báo cáo đã tách khỏi bảng nên chọn ngày trực tiếp được.

Chưa đổi quy tắc nghiệp vụ và các hạn chế backend trong README bản v1 vẫn áp dụng. Chưa có runtime schema validation response, test component tự động, hoặc kiểm thử trình duyệt đầy đủ. Chưa có migration database, NestJS, PostgreSQL hay triển khai production. Component workspace hiện đủ nhỏ để học nhưng nên tiếp tục tách hook khi thêm vé/chuyến.

## Kiểm tra

Kết quả lần triển khai này: `npm.cmd run build` thành công, gồm biên dịch, kiểm tra TypeScript và tạo trang. Phiên bản đã cài được lưu trong package-lock: Next 16.4.2, React 19.3.1, TypeScript 7.0.2. Công cụ trình duyệt bị chính sách truy cập chặn khi mở localhost, nên chưa kiểm thử trực quan hay chạy toàn bộ luồng qua trình duyệt. Không suy ra nghiệp vụ đã đạt chỉ từ build thành công.

```text
npm.cmd run typecheck
npm.cmd run build
```

Kiểm thử backend: tại `../nha-xe-v1`, chạy `python -m unittest -v test_app.py`. Bộ test dùng database tạm.

Kiểm tra tay bằng dữ liệu giả: đăng nhập SG → nhập đơn trả đầu kia → tìm SĐT → đăng xuất → TK đánh dấu đã tới → thử giao trước thu phải bị chặn → thu → giao → admin đối chiếu báo cáo đúng ngày và tải CSV. Thử cả cửa sổ điện thoại, lỗi mất backend và phiên hết hạn. Không coi checklist này là đã chạy nếu chưa có kết quả thực tế ghi lại.

Lộ trình và bài tập: đọc `../LO-TRINH-HOC-VA-LAM.md`.
