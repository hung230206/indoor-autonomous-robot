# Báo cáo giai đoạn 1 có YOLO

Kết quả kiến trúc mới được lưu riêng trong [báo cáo Markdown camera trên xe](../docs/ego-results.md), có video và bằng chứng ego.

**Phạm vi lịch sử:** Word này ghi camera trên cao. Yêu cầu mới chuyển camera lên xe được mô tả riêng ở [camera trên xe](../docs/ego-vision.md); không dùng các chỉ số của báo cáo cũ cho góc nhìn mới.

[Tải bản Word 6 trang](Bao_cao_giai_doan_1_YOLO.docx).

Ngày kiểm chứng: 06/11/2026. Phần mở rộng kết hợp camera Webots, YOLO11n fine-tune lớp `box`, phép chiếu ảnh sang mặt sàn, occupancy grid, A* và FSM. Đây là báo cáo kết quả mô phỏng, chưa có xe thật hoặc camera điện thoại thực nghiệm.

| Kiểm tra | Kết quả |
|---|---|
| Dữ liệu tổng hợp | 240 cảnh độc lập: 160 train, 40 val, 40 test |
| Test nhận diện | 40 ảnh, 70 hộp; precision 99,91%, recall 100%, mAP50–95 94,97% |
| Tích hợp YOLO | 4/4 đúng kỳ vọng: 3 đến đích, 1 mất camera dừng SAFE_STOP |
| Hồi quy Webots nền | 10/10 đúng kỳ vọng: 8 đến đích, 2 NO_PATH |
| Kiểm thử mã nguồn | 23 test qua |
| Đối chứng hộp xa | Dừng lập lại đường ở giây 1,344 với YOLO và 6,304 với cảm biến |

Một ca đối chứng không chứng minh YOLO luôn tốt hơn. Tập test cùng miền render với tập train, pose xe vẫn lý tưởng và cảm biến khoảng cách còn tham gia dừng khẩn. Bộ thử hiện tại không chứng minh khả năng an toàn ở xe thật.

Xem [hướng dẫn YOLO](../docs/yolo.md), [số liệu và provenance](../experiments/evidence/yolo_v1/report-data.json), [video camera có nhận diện](../experiments/evidence/yolo_v1/navigation/yolo_far_box/yolo-camera.mp4) và [video mô phỏng 3D](../experiments/evidence/yolo_v1/navigation/yolo_far_box/webots.mp4).
