# Cấu hình phần cứng đã chốt

Ngày xác nhận: **06/11/2026**. Người dùng chốt cấu hình theo `tài liệu/Ke_hoach_robot_tu_hanh_kem_so_do_kien_truc.docx`.

Trạng thái: **đã chọn cấu hình**, chưa có xác nhận đã mua, lắp hoặc kiểm tra linh kiện thật. Quyết định này không thay thế kết quả kiểm thử mô phỏng hoặc thông số điện của từng sản phẩm.

## Kiến trúc

- Xe 2WD: hai motor TT giảm tốc, hai bánh 65 mm, một bánh tự do.
- ESP32 NodeMCU-32S điều khiển motor qua TB6612FNG và nhận lệnh Wi-Fi từ laptop.
- Laptop chạy Python, OpenCV, ArUco, A* và bộ bám đường.
- Điện thoại sẵn có đặt cố định trên cao để định vị marker trên xe.
- Ba HC-SR04 ở trước/trái/phải, tích hợp tránh cản ở giai đoạn 3.
- Nguồn theo danh mục Word: hai pin 18650, hộp pin, bảo vệ 2S, bộ sạc hai khe và hai mạch hạ áp LM2596.

## Danh mục theo bản Word

Các số tiền dưới đây là **dự toán trong kế hoạch**, không phải báo giá hoặc xác nhận tồn kho hiện tại.

| Linh kiện | Số lượng | Thành tiền dự toán (đ) | Giai đoạn |
|---|---:|---:|---|
| ESP32 NodeMCU-32S | 1 | 190.000 | 2 |
| Bộ motor TT kèm bánh 65 mm | 2 | 70.000 | 2 |
| Bánh tự do 25 mm | 1 | 15.000 | 2 |
| TB6612FNG | 1 | 45.000 | 2 |
| Pin 18650 | 2 | 70.000 | 2 |
| Hộp hai pin có công tắc | 1 | 20.000 | 2 |
| Mạch bảo vệ Li-ion 2S | 1 | 20.000 | 2 |
| Bộ sạc 18650 hai khe | 1 | 45.000 | 2 |
| LM2596 | 2 | 40.000 | 2 |
| Bộ dây jumper | 1 | 25.000 | 2 |
| Tấm khung tự chế | 1 | 20.000 | 2 |
| Điện trở, ốc vít, dây nguồn, đầu nối | 1 lô | 20.000 | 2 |
| HC-SR04 | 3 | 81.000 | 3 |
| **Tổng giai đoạn 2** | | **580.000** | |
| **Tổng giai đoạn 3** | | **81.000** | |
| **Tổng linh kiện** | | **661.000** | |

Ngân sách kế hoạch gồm dự phòng: **730.000–760.000đ**, cộng vận chuyển; tận dụng laptop và điện thoại sẵn có.

## Các chi tiết còn cần hoàn thiện khi lắp

Giữ cấu hình trên làm cơ sở thiết kế. Sơ đồ nguồn, điện áp từng nhánh, dòng chạy/kẹt của đúng motor mua, giới hạn driver, GPIO, điện trở hạ mức Echo, cách nối bảo vệ pin và quy trình sạc vẫn cần xác minh trước khi đấu điện. Không coi BMS là bộ sạc. Nếu phát hiện linh kiện cụ thể không tương thích, ghi rõ lý do và trao đổi thay đổi cấu hình với người dùng.

Kích thước thân xe, khoảng cách bánh, vận tốc và các ngưỡng trong mô phỏng vẫn là giả định; phải đo và hiệu chỉnh theo xe sau khi lắp.

Bước chuẩn bị tiếp theo: lập sơ đồ đấu nối và bảng GPIO cho ESP32, driver, motor và nguồn theo cấu hình đã chốt.
