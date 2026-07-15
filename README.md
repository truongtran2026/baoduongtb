# Bảo dưỡng thiết bị — Tạo hồ sơ bảo dưỡng (bản thay thế công cụ Excel/VBA)

Ứng dụng web nội bộ thay thế công cụ `taofilebdV3.0.xlsm` (Excel + VBA) cũ. Vẫn dùng đúng 4 file mẫu Word
(`temp_vt.docx`, `temp_td.docx`, `temp_cm.docx`, `temp_ip.docx`) và đúng dữ liệu trạm / nhân viên / thiết bị cũ,
nhưng giao diện đẹp hơn, nhiều người dùng cùng lúc qua trình duyệt, và **đã sửa lỗi crash khi tên trạm/thiết bị/thư
mục quá dài**.

## Cài đặt lần đầu

1. Cài Python 3.10 trở lên nếu máy chưa có (tải tại python.org, nhớ tick "Add to PATH" lúc cài).
2. Double-click **`setup.bat`** — tự tạo môi trường và cài thư viện cần thiết (chỉ cần làm 1 lần).

## Chạy ứng dụng

Double-click **`run.bat`**. Trình duyệt sẽ tự mở `http://127.0.0.1:8899`.

- Máy khác trong cùng mạng LAN muốn dùng chung: mở trình duyệt, gõ `http://<địa-chỉ-IP-máy-chủ>:8899`
  (địa chỉ IP được in ra trong cửa sổ console khi khởi động). Nếu không vào được từ máy khác, kiểm tra
  Windows Firewall có đang chặn cổng 8899 không.
- Đóng cửa sổ console (hoặc Ctrl+C) để tắt máy chủ.

## Lần chạy đầu tiên — dữ liệu có sẵn

Nếu thư mục `ProjectBDTB_Old` (chứa `taofilebdV3.0.xlsm` và các file mẫu) vẫn nằm cạnh thư mục ứng dụng này,
lần khởi động đầu tiên sẽ **tự động nhập toàn bộ dữ liệu cũ** (trạm, nhân viên, mục bảo dưỡng, thiết bị, file
mẫu Word) — không cần làm gì thêm. Các lần sau sẽ không nhập lại (để không đè dữ liệu bạn đã chỉnh sửa).

## Cập nhật dữ liệu bằng Excel (Xuất / Nhập)

Ở trang **Trạm**, **Nhân viên** hoặc **Thiết bị** đều có 2 nút:

- **⬇ Xuất Excel**: tải về 1 file `.xlsx` chứa toàn bộ dữ liệu hiện tại (trạm, nhân viên, mục bảo dưỡng, thiết
  bị) — đúng định dạng file cũ, mở được bằng Excel bình thường.
- **⬆ Nhập từ Excel**: chọn lại file đó (đã sửa xong) để cập nhật vào app.

Quy trình khuyên dùng: **Xuất Excel** → sửa trực tiếp trên Excel (thêm/sửa/xoá dòng tuỳ ý) → **Nhập từ Excel**
lại chính file đó. Từ lần sau chỉ cần giữ và cập nhật tiếp file này, không cần soạn file riêng.

Lưu ý quan trọng: khi nhập, **mỗi trạm/thiết bị trong file được coi là danh sách đầy đủ, mới nhất** — dòng nào
trong app mà không còn trong file sẽ **bị xoá hẳn** (không phải ẩn đi), dòng trùng mã sẽ được cập nhật, dòng mới
sẽ được thêm. Vì vậy hãy chắc file bạn nhập là bản đầy đủ (xuất ra rồi sửa tiếp), đừng nhập một file chỉ chứa
một phần dữ liệu.

## Cách dùng

1. **Tạo hồ sơ bảo dưỡng** (trang mặc định): chọn Trạm → chọn Mục bảo dưỡng → nhập Ngày/Người thực hiện/Người
   phối hợp → chọn thiết bị cần làm (mặc định chọn hết, có thể bỏ bớt) → bấm **Tạo hồ sơ bảo dưỡng**.
2. Kết quả hiện ngay trên trang: số file thành công/cảnh báo/lỗi, có thể **Tải về (ZIP)** toàn bộ hoặc **Mở
   thư mục** (nếu đang mở trình duyệt trên chính máy chủ).
3. **Lịch sử tạo file**: xem lại mọi lượt đã tạo, tải lại từng file hoặc cả đợt. Tick chọn (nhiều dòng cùng lúc
   được) rồi **Xoá đã chọn** để dọn bớt lượt cũ — xoá luôn cả file Word đã tạo trên máy chủ, có hỏi xác nhận
   trước khi xoá.
4. **Trạm**: bấm vào mã/tên trạm để vào "trang riêng" của trạm đó — xem và quản lý luôn nhân viên + thiết bị
   của trạm ngay tại đây (thêm/sửa/xoá), không cần qua lại giữa nhiều trang.
5. **Nhân viên / Thiết bị**: thêm, sửa, xoá trực tiếp. Ở trang Thiết bị có thể tick chọn nhiều dòng rồi
   **Xoá đã chọn** (có hỏi xác nhận trước khi xoá).
6. **Mục bảo dưỡng & mẫu Word**: thêm một loại thiết bị hoàn toàn mới (ví dụ "Nguồn điện") bằng cách bấm
   *+ Thêm mục bảo dưỡng*, đặt tên thư mục lưu / tiền tố tên file, rồi tải lên file `.docx` mẫu — **không cần
   sửa code** như công cụ VBA cũ (trước đây thêm loại thiết bị mới phải sửa macro).
7. **Cài đặt**: đổi thư mục gốc lưu hồ sơ đã tạo.

## File mẫu Word (.docx) — cách viết thẻ

Mẫu dùng đúng cú pháp thẻ `[[ten_bien]]` như file cũ, Word Find/Replace kiểu cũ vẫn hoạt động tương tự:

| Thẻ | Ý nghĩa |
|---|---|
| `[[matram]]` | Mã trạm |
| `[[tentram]]` | Tên trạm — Đài |
| `[[diachi]]` | Địa chỉ trạm |
| `[[toado]]` | Toạ độ trạm |
| `[[mucbaoduong]]` | Tên mục bảo dưỡng |
| `[[thietbi]]` | Tên thiết bị |
| `[[sohs]]` | Số hồ sơ |
| `[[cauhinh]]` | Cấu hình thiết bị |
| `[[ngaybaoduong]]` | Ngày bảo dưỡng (dd/mm/yyyy) |
| `[[thangbaoduong]]` | Tháng bảo dưỡng (mm/yyyy) |
| `[[nguoithuchien]]` | Người thực hiện |
| `[[nguoiphoihop]]` | Người phối hợp |

## Lỗi "crash khi tên quá dài" đã được sửa thế nào

Công cụ Excel cũ ghép tên file lưu theo dạng `<thư mục gốc>\<Vô tuyến|...>\VT-C3-M<tháng>-<ngày>-<tên thiết
bị>_<mã trạm>.docx`. Nếu thư mục cài đặt nằm sâu (nhiều cấp thư mục) cộng thêm tên thiết bị dài, tổng đường dẫn
vượt quá giới hạn 260 ký tự của Windows khiến Word.SaveAs báo lỗi/crash.

Ứng dụng mới xử lý theo 3 lớp, không phụ thuộc vào việc bạn đặt tên thư mục dài hay ngắn:

1. Luôn ghi file qua chế độ đường dẫn mở rộng của Windows (`\\?\...`), bỏ qua hẳn giới hạn 260 ký tự cũ.
2. Tên thiết bị quá dài trong tên file sẽ tự động được rút gọn (giữ phần đầu + mã băm ngắn để không trùng
   nhau), kèm cảnh báo rõ ràng thay vì crash.
3. Trang **Cài đặt** cho phép chọn một thư mục gốc ngắn gọn để danh sách file trong Explorer luôn dễ nhìn.

## Cấu trúc dữ liệu

Toàn bộ dữ liệu nằm trong `app/data/`:
- `app.db` — cơ sở dữ liệu (trạm, nhân viên, thiết bị, mục bảo dưỡng, lịch sử tạo file)
- `word_templates/` — các file mẫu .docx đã tải lên
- `output/` — hồ sơ Word đã tạo (mặc định; có thể đổi ở trang Cài đặt)

Sao lưu định kỳ bằng cách copy cả thư mục `app/data/`.
