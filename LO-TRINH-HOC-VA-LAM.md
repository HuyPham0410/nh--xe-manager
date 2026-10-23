# Học bằng project Sổ nhà xe

## Mục tiêu và lựa chọn

Mục tiêu kép: hiểu và tự viết được code, đồng thời xây phần mềm giải quyết công việc hàng ngày của nhà xe. Mỗi mốc phải có một tính năng chạy được, một kiểm thử và một điều bạn giải thích được bằng lời của mình.

Hướng chính: JavaScript → TypeScript → React → Next.js → Node.js/NestJS → PostgreSQL → triển khai. Next.js xây trên React; NestJS là framework chạy trên Node.js. Không coi chúng là những ngôn ngữ độc lập phải học lại từ đầu.

Chọn TypeScript cho cả frontend và backend tương lai để dùng cùng một ngôn ngữ. PostgreSQL phù hợp các quan hệ đơn hàng, chuyến, vé và giao dịch tiền. Python/Django là một nhánh backend thay thế để tìm hiểu sau; không cần xây hai backend cùng lúc. MongoDB nên là bài thực hành riêng sau khi nắm SQL. Đây là lựa chọn cho project này, không phải kết luận công nghệ nào tốt nhất hay cam kết có việc làm.

## Trạng thái thật của code

| Phần | Hiện trạng |
|---|---|
| Bản tham chiếu Python + giao diện thuần | `nha-xe-v1/`, vẫn giữ để so sánh và cung cấp API |
| React + TypeScript + Next.js | `nha-xe-web/`, giao diện mới dùng API thật và dữ liệu cũ |
| Backend NestJS | Chưa triển khai; mốc học tiếp theo |
| PostgreSQL | Chưa triển khai; hiện vẫn là SQLite |
| Redis / BullMQ / WebSocket | Chưa triển khai; chỉ thêm khi có tính năng cần dùng |

## Mốc 0 — Hiểu đường đi của một đơn hàng

Học: biến, hàm, object, array, module, async/await, try/catch, HTTP GET/POST, JSON, Git.

Thực hành: mở bản cũ, ghi một đơn giả và tìm lại theo SĐT. Đọc đoạn xử lý `POST /api/cargo` trong `nha-xe-v1/app.py`. Vẽ đường đi: form → request → kiểm tra quyền/dữ liệu → INSERT → response → danh sách.

Hoàn thành khi: bạn giải thích được tại sao kiểm tra trong trình duyệt chưa đủ, vì sao không cho trình duyệt tự quyết định chi nhánh, và dữ liệu nằm ở đâu sau khi đóng trình duyệt.

## Mốc 1 — React và TypeScript qua giao diện hiện tại

Học: JSX, component, props, state, event, FormData, effect, union type, interface, Promise, AbortController.

Đọc theo thứ tự:

1. `nha-xe-web/lib/types.ts`: mô tả User, CargoInput, Cargo, Report.
2. `nha-xe-web/components/cargo-table.tsx`: dữ liệu đi vào qua props; JSX tạo các hàng; callback đưa hành động lên cha.
3. `nha-xe-web/components/login-form.tsx`: state loading/error và submit bất đồng bộ.
4. `nha-xe-web/components/cargo-form.tsx`: chuyển dữ liệu FormData thành CargoInput, lưu xong reset và focus.
5. `nha-xe-web/lib/api.ts`: fetch, cookie, CSRF, lỗi HTTP. Generic TypeScript không tự kiểm tra JSON nhận về.
6. `nha-xe-web/components/cargo-workspace.tsx`: state cấp màn hình, tìm kiếm chậm 250ms, hủy request cũ.
7. `nha-xe-web/components/daily-report.tsx`: effect tải dữ liệu theo ngày và trạng thái chờ/lỗi.

Ba bài tập tự làm, tăng dần:

- Thêm hiển thị “Số đơn đang hiển thị” ở bảng và giải thích vì sao đó không luôn là tổng số đơn của hệ thống.
- Thêm nút xóa từ khóa tìm kiếm; không reload cả trang.
- Thêm bộ lọc trạng thái từ frontend xuống API; lọc ở máy chủ trước giới hạn 1.000 dòng. Kiểm thử với hai đơn khác trạng thái. Không chỉ lọc mảng 1.000 kết quả ở trình duyệt rồi gọi đó là toàn bộ dữ liệu.

Hoàn thành khi: tự viết được một component nhỏ nhận props; sửa form mà không copy cả màn hình; xử lý được loading, empty và error; giải thích vì sao cần key ổn định cho danh sách.

## Mốc 2 — Hiểu Next.js

Học: App Router, `page.tsx`, `layout.tsx`, Server/Client Component, metadata, dev/build/start, cùng origin và proxy.

Trong bản này `app/page.tsx` dựng trang, còn component tương tác có `'use client'`. Không thêm SSR phức tạp khi màn hình cần đăng nhập và dữ liệu thay đổi theo thao tác nhân viên.

Thực hành: tách trang hướng dẫn sử dụng thành `/huong-dan` bằng một Server Component. Sau đó tách màn hình tìm hàng thành route riêng nếu bạn đã hiểu state và routing. Không chuyển cookie hay mật khẩu vào localStorage.

Hoàn thành khi: biết vì sao state và event cần Client Component, vì sao mã proxy nằm phía Next server, và vì sao build được chưa chứng minh toàn bộ nghiệp vụ đúng.

## Mốc 3 — Node.js và NestJS: chuyển từng API

Học Node.js trước: runtime, event loop ở mức cơ bản, package.json, biến môi trường, async I/O, lỗi và HTTP. Sau đó học Nest: Module, Controller, Service/Provider, dependency injection, DTO, ValidationPipe, Guard, exception filter.

Thiết kế một ứng dụng backend duy nhất, chia module Auth, Cargo, Reports. Controller tiếp nhận yêu cầu; Service thực hiện quy tắc nghiệp vụ; lớp truy cập dữ liệu làm việc với database. Tránh dồn SQL và mọi điều kiện vào Controller.

Thứ tự chuyển:

1. Định nghĩa hợp đồng API hiện có, tạo kiểm thử theo hành vi.
2. Đăng nhập, phiên, quyền và CSRF.
3. Nhận hàng và tìm kiếm.
4. Đã tới / thu tiền / đã giao cùng audit trong transaction.
5. Báo cáo và CSV.
6. Chạy cùng bộ kiểm thử hành vi, rồi đổi proxy Next sang backend mới.

Không chạy hai backend ghi đồng thời vào hai database rồi hy vọng dữ liệu tự đồng bộ. Chỉ chuyển khi kiểm thử và đối chiếu dữ liệu đạt.

Bài tập: viết Guard để nhân viên SG không được xác nhận giao hàng SG → TK; viết test HTTP chứng minh request bị từ chối ngay cả khi gọi API trực tiếp.

## Mốc 4 — PostgreSQL và dữ liệu thật

Học: bảng, khóa chính/ngoại, UNIQUE/CHECK, JOIN, GROUP BY, index, transaction, migration. Viết SQL cơ bản trước khi phụ thuộc ORM; sau đó chọn một ORM hoặc query builder để học migration và transaction.

Chuyển users/cargo/audit trước. Dùng kiểu tiền nguyên đồng có giới hạn rõ ràng, thời gian có múi giờ, ràng buộc tại database. Thu tiền và audit phải commit hoặc rollback cùng nhau. Kiểm thử hai request thu cùng lúc: chỉ một request được phép thay đổi từ chưa thu sang đã thu.

Để chuyển dữ liệu SQLite: sao lưu → xuất → nhập vào database thử → đối chiếu số lượng đơn, tổng cước, tổng thu và quan hệ audit → diễn tập rollback → mới lên lịch chuyển dữ liệu thật. Không tự đổi mật khẩu khi di chuyển tài khoản.

Bài tập: viết query tổng cước theo ngày tạo và query thực thu theo ngày thu. Tạo đơn hôm qua, thu hôm nay, giải thích hai báo cáo khác nhau.

## Mốc 5 — Hoàn thiện nghiệp vụ và triển khai

Ưu tiên: đổi mật khẩu, khóa tài khoản, sửa/hủy có lịch sử, idempotency khi nhận đơn, phân trang, sao lưu/khôi phục, HTTPS, cấu hình môi trường, logging tránh lộ SĐT/mật khẩu, giám sát lỗi. Sau đó thêm xe/nhân viên/chuyến rồi bán vé theo lộ trình nghiệp vụ ban đầu.

Bài tập nghiệm thu vé: hai người cùng bán chỗ cuối cùng, chỉ một giao dịch thành công; số khách không vượt sức chứa. Đây là bằng chứng năng lực có ý nghĩa hơn một màn hình đẹp nhưng bán trùng.

Hoàn thành khi: có thể triển khai trên môi trường thử, khôi phục từ bản sao lưu và để người khác sử dụng theo hướng dẫn mà không cần bạn sửa database bằng tay.

## Mốc 6 — Công nghệ mở rộng, mỗi thứ gắn với một vấn đề

| Công nghệ | Bài toán để học | Điều phải kiểm chứng |
|---|---|---|
| WebSocket | Chi nhánh TK thấy thông báo hàng mới/xe tới mà không tải lại | Mất mạng rồi kết nối lại phải tải trạng thái chuẩn từ API; phân quyền từng kết nối |
| Redis | Lưu phiên hoặc giới hạn đăng nhập dùng chung nhiều tiến trình | TTL và hành vi khi Redis lỗi; không coi cache là sổ tiền |
| BullMQ + Redis | Xuất báo cáo lớn hoặc tác vụ nền | Job retry không tạo kết quả trùng; theo dõi job thất bại; timeout |
| MongoDB | Bài tập độc lập về dữ liệu tài liệu và schema thay đổi | Giải thích khi nào mô hình tài liệu hữu ích; không thêm database thứ hai chỉ để liệt kê trên CV |
| Django | Bài tập so sánh backend sau khi hoàn thành hướng Nest | Viết một API nhỏ tương đương, so sánh auth/ORM/admin và chi phí bảo trì |

## Cách học mỗi buổi

1. Chọn đúng một hành vi nhỏ, ví dụ “chọn ngày báo cáo ngay trong tab báo cáo”.
2. Viết tiêu chí chấp nhận: chọn hôm qua phải tải đúng dữ liệu hôm qua, có trạng thái chờ và lỗi.
3. Đọc tài liệu liên quan và code hiện có khoảng 15–20 phút.
4. Tự sửa, chạy thử và đọc lỗi; nhờ trợ giúp giải thích nguyên nhân khi mắc.
5. Viết kiểm thử phù hợp nếu thay đổi nghiệp vụ hoặc dữ liệu.
6. Ghi lại: đã làm gì, vì sao, lỗi nào, cách chứng minh đã đúng. Commit nhỏ nếu đã khởi tạo Git.

Không cần cố hoàn thành theo số tuần cố định. Đi tiếp khi đạt tiêu chí của mốc. Tránh ghi vào CV những phần mới chỉ có trong lộ trình. Hiện bạn có thể mô tả trung thực một giao diện Next.js/React/TypeScript kết nối REST API Python/SQLite; chỉ thêm NestJS/PostgreSQL sau khi tự triển khai và giải thích được.

## Tài liệu gốc

- JavaScript: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide
- TypeScript: https://www.typescriptlang.org/docs/handbook/intro.html
- React: https://react.dev/learn
- Next.js: https://nextjs.org/docs/app/getting-started/installation
- NestJS: https://docs.nestjs.com/first-steps và https://docs.nestjs.com/providers
- PostgreSQL: https://www.postgresql.org/docs/current/tutorial.html
