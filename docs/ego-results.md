# Kết quả camera trước trên xe — 06/11/2026

Đã thay camera trên cao bằng camera RGB gắn trước thân xe, train checkpoint YOLO11n riêng, chuyển tiếp xúc ảnh xuống sàn, ghép cự ly và odometry encoder + IMU. Không có camera trên cao trong world ego. Supervisor pose chỉ dùng đánh giá độc lập; pose điều hướng khởi tạo ở A đã biết rồi tích phân encoder với hướng IMU.

## Kết quả đã chạy bằng checkpoint cuối

| Ca Webots ego | Kết quả | Giây mô phỏng | Số lần A* | Sai số đích thật |
|---|---|---:|---:|---:|
| Sàn trống | GOAL_REACHED | 26,016 | 1 | 3,79 cm |
| Hộp xa xuất hiện | GOAL_REACHED | 30,624 | 3 | 3,89 cm |
| 5 hộp xuất hiện | GOAL_REACHED | 29,600 | 4 | 4,16 cm |
| Ngắt khung camera sau 2 s | SAFE_STOP | 2,496 | 1 | Không áp dụng |

Cả 4 ca đúng kỳ vọng: **3 đến đích và 1 dừng do camera cũ/mất**, không ghi nhận va chạm hay tâm xe đi vào ô cấm đã inflate trong các lượt cuối này. Tổng số lần A* gồm lần đầu. Sai số vị trí odometry lớn nhất trong các ca này khoảng 6,3 mm; đây là encoder/IMU lý tưởng của simulator, không phải mức chính xác đã đo trên xe thật.

Ca hộp xa dừng `OBSTACLE_STOP` lần đầu ở giây **1,312**, trước khi cảm biến phía trước đo được hộp ngoài tầm 0,8 m. Lớp thị giác sau lượt còn 18 ô, ca 5 hộp còn 40 ô. YOLO thực sự cập nhật map, không chỉ vẽ khung. Chế độ trên xe kết hợp range mapping nên kết quả đến đích là của hệ thống ghép cảm biến, không phải chỉ YOLO.

29 test mã nguồn qua; 10 ca Webots nền vẫn đúng kỳ vọng (8 đến đích, 2 NO_PATH). Chi tiết ở [bằng chứng ego](../experiments/evidence/ego_v1/report-data.json), [bảng lượt chạy](../experiments/evidence/ego_v1/navigation/results.csv), các file trajectory/events/map và pose-evaluation trong từng ca. Mỗi lượt ghi hash checkpoint; exporter đối chiếu với model trước khi lưu bằng chứng.

## Nhận diện trên tập test mới

360 ảnh độc lập, 360 SHA khác nhau: 240 train / 60 val / 60 test; số hộp có nhãn lần lượt 127 / 38 / 37. Tập test có 28 ảnh dương tính và 32 ảnh âm tính. Ultralytics trả precision 99,83%, recall 97,30%, mAP50 97,50%, mAP50–95 94,93%. Đánh giá trên ảnh tổng hợp cùng miền render, chưa có ảnh điện thoại thật; không dùng các chỉ số này làm tỷ lệ robot đến đích hoặc an toàn vật lý.

Nhãn từ segmentation ground truth **chỉ ở bước tạo dữ liệu**; runtime không bật recognition và không lấy vị trí hộp từ simulator để thay detection. Model card/tham số/metrics: [models/yolo_ego](../models/yolo_ego/README.md).

## Những lỗi đã gặp và giới hạn

Các lượt phát triển chỉ dùng encoder đã SAFE_STOP do odometry trôi và phép kiểm tra ô cấm phát hiện lệch vị trí; chúng không được tính là các lượt thành công. Đã lưu summary/events/checkpoint tương ứng ở `development_failures/`. Hiệu chuẩn bánh riêng chưa đủ khử trượt quay; bản cuối thêm hướng IMU. Đây là lịch sử sửa lỗi, không phải phép so sánh có kiểm soát giữa hai phương pháp ở cùng checkpoint.

Ước lượng tiếp xúc sàn phụ thuộc nhìn rõ chân hộp, sàn phẳng và camera hiệu chuẩn. Bbox bị cắt mép/đáy ảnh không được chiếu. IMU chưa có bias/noise; chưa tự xác định pose ban đầu, chưa stream điện thoại/Wi-Fi/ESP32 và chưa đồng bộ timestamp cảm biến thật. Danh mục phần cứng trước đây chưa có encoder/IMU, cần cập nhật trước khi mua. Bài ngắt camera chỉ xác minh FSM trong Webots đồng bộ, chưa thay watchdog độc lập trên ESP32.

## Xem và chạy lại

Mở `demo_camera_tren_xe.cmd` hoặc chạy:

```powershell
.\.venv-yolo\Scripts\python.exe tools/run_live_demo.py
```

Ảnh gốc bên trái, ảnh YOLO bên phải, kèm FSM/confidence/thời gian suy luận. Camera chỉ thấy phía trước và quay theo xe. [Video camera trước có YOLO](../experiments/evidence/ego_v1/navigation/yolo_many_boxes/yolo-camera.mp4), [video thế giới 3D](../experiments/evidence/ego_v1/navigation/yolo_many_boxes/webots.mp4). Xem [kiến trúc và giới hạn](ego-vision.md). Bản Word trước đây vẫn được giữ với phạm vi camera trên cao, không đại diện cho kết quả mới này.
