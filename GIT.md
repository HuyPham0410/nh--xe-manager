# Đưa dự án nhà xe lên Git

Kho Git đã khởi tạo tại thư mục chứa tài liệu này, nhánh `main`. Chưa có commit hoặc remote; chưa push.

Mở terminal tại `projects/nha-xe-manager/` và thực hiện:

```powershell
git status --short
git add .
git diff --cached --stat
git diff --cached --name-only
git commit -m "Initial nha xe manager project"
```

Kiểm tra danh sách trước khi commit: không có `.env`, `TAI-KHOAN.txt`, database, `node_modules`, `.next`, CV hoặc tài liệu portfolio. `.env.example` và các tệp `package-lock.json` cần được theo dõi.

Sau khi tạo repository trống trên GitHub, thay `<URL_REPOSITORY>` bằng URL thực của bạn:

```powershell
git remote add origin <URL_REPOSITORY>
git push -u origin main
```

Không khởi tạo Git tại thư mục ChatGPT bên ngoài. Không dùng `git add -f` với các tệp riêng bị loại trừ. Chưa cấu hình danh tính hoặc tài khoản Git thay bạn.

## Chạy trên máy khác

Cài Node.js 22.12+ và Python 3.11+. Chạy `npm.cmd ci`, `npm.cmd run setup`, sao chép `.env.example` thành `.env`, rồi `npm.cmd run dev`. Backend tự tạo database và tệp tài khoản khởi tạo nếu chưa có; dữ liệu cục bộ của máy cũ không nằm trong repository.

Sau khi đổi vị trí thư mục, chạy `npm.cmd run build` trước khi dùng `npm.cmd start` để tạo bản build tại đường dẫn mới.
