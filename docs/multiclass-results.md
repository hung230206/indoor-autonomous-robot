# Model ba lớp sau khi train Colab

Nhận kết quả ngày **12/11/2026**, từ ZIP `objects_v1_20261112_081430_results.zip` do người dùng gửi. Hash của dataset và checkpoint khớp notebook đã chuẩn bị; class order đúng `box`, `furniture_leg`, `slipper`. Giữ nguyên checkpoint, không train lại hoặc thay ngưỡng theo tập test.

## Huấn luyện và đánh giá ảnh

Colab Tesla T4, Ultralytics 8.4.202, PyTorch 2.14.1+cu130, Python 3.13.16. YOLO11n khởi tạo COCO, **60 epoch**, ảnh 640, batch 16, seed 42, không freeze backbone. CSV ghi 757,794 giây cho quá trình train; không tính đây là thời gian toàn bộ phiên Colab hoặc dự báo tốc độ cho máy khác.

1.200 cảnh RGB camera trên xe: 840 train / 180 validation / 180 test. Test có 114 hộp, 326 chân bàn/ghế và 104 dép. Checkpoint được chọn bằng validation. Số đo test từ Colab:

| Lớp | Precision | Recall | mAP50 | mAP50–95 |
|---|---:|---:|---:|---:|
| box | 99,11% | 98,25% | 99,23% | 98,12% |
| furniture_leg | 98,13% | 96,93% | 99,36% | 95,24% |
| slipper | 99,03% | 97,89% | 99,16% | 96,14% |
| Trung bình | 98,76% | 97,69% | 99,25% | **96,50%** |

Đây là detector trên ảnh tổng hợp cùng họ render; không gọi mAP là accuracy hoặc tỷ lệ tránh cản. Bộ test khác bộ box cũ nên không dùng hai số mAP để kết luận mức cải thiện trực tiếp. Model card và file gốc: [`models/yolo_objects_v1/`](../models/yolo_objects_v1/).

## Tích hợp điều hướng

`VisualObstacleLayer` nhận một danh sách lớp vật cản rõ ràng, giữ tương thích `class_name: box` của bản cũ. Cả ba lớp mới phải qua xác nhận hai timestamp, kiểm tra confidence, biên ảnh, phép chiếu mặt sàn và inflation như trước. Bbox chân bị cắt đáy không được chấp nhận để đo khoảng cách. Cự ly, A*, FSM, encoder/IMU và ngưỡng an toàn giữ nguyên.

Phiên bản cấu hình nằm ở `config/vision_objects.json`: checkpoint mới, ảnh inference 640, confidence 0,5, cùng intrinsics/độ cao/pitch camera cũ. Viewer hiển thị tên và số lượng từng lớp, không gộp mọi detection thành box. Summary lưu lớp detector, lớp được map, hash checkpoint và kích thước inference.

**Lỗi phát hiện khi tích hợp:** bốn lượt đầu đều NO_PATH vì model nhận nhầm chấm đỏ điều khiển đích thành dép, rồi map chặn đích. Đây là lỗi thật, được giữ ở `development_failures` trong bằng chứng mới.

Chấm đỏ là annotation giao diện, không có boundingObject vật lý. Đã đặt `exclude_goal_overlay: true` để chỉ ẩn node lệnh đích khỏi camera RGB; nó vẫn hiện trong góc nhìn 3D và vẫn là nguồn lệnh đích. Dùng [API setVisibility của Supervisor](https://github.com/cyberbotics/webots/blob/R2025a/docs/reference/supervisor.md#wb_supervisor_node_set_visibility) theo từng camera. Không lọc detection bằng tọa độ đích, không loại vật đỏ thật và không lấy vị trí vật cản từ simulator để tạo map. Bộ ảnh test và checkpoint vẫn nguyên bản, không che dấu đích trong ảnh test khi báo mAP.

Một lượt triển khai hàm lấy node camera đã timeout trước khi tạo summary do dùng sai kiểu tham số API; lượt đó cũng được lưu riêng, không coi là một lần robot chạy thành công.

## Bốn ca vật thể sau sửa annotation

| Ca Webots ego | Có prior map vật thể? | Kết quả | Giây mô phỏng | Số lần A* | Sai số đích thật |
|---|---|---|---:|---:|---:|
| objects_room | Có, 5 vật | GOAL_REACHED | 30,976 | 3 | 3,57 cm |
| unknown_table | Không | GOAL_REACHED | 29,248 | 2 | 4,29 cm |
| unknown_chair | Không | GOAL_REACHED | 26,304 | 2 | 4,13 cm |
| unknown_slipper | Không | GOAL_REACHED | 29,216 | 2 | 3,92 cm |

**4/4 đến đích**, không ghi nhận contact vật lý với vật thể hoặc tâm xe vào ô cấm đã inflate trong các lượt này. Ba ca unknown không nạp vị trí vật thể vào map. Đây là kết quả của cả hệ thống RGB/YOLO + cự ly + A*/FSM; không phải phép thử YOLO đơn độc. Bản cũ có hai ca lỗi bàn/ghế; bản mới còn thay cách hiển thị annotation camera, nên không gọi bảng này là ablation chỉ thay model.

## Kiểm tra hồi quy và tái lập

| Ca ego với model mới | Kết quả | Giây mô phỏng |
|---|---|---:|
| Sàn trống | GOAL_REACHED | 26,016 |
| Hộp xa xuất hiện | GOAL_REACHED | 34,016 |
| Năm hộp xuất hiện | GOAL_REACHED | 28,288 |
| Mất camera sau 2 s | SAFE_STOP | 2,496 |

4/4 ca ego hồi quy đúng kỳ vọng (3 đến đích, 1 dừng do mất camera). Cả 10 ca Webots nền và 10 ca 2D đúng kỳ vọng (8 đến đích, 2 NO_PATH); đây là các bộ riêng. 49 unit test qua. Native probe xác nhận marker khác JSON lúc mở world, đổi đích giữa đường và sau khi đến đích vẫn hoạt động khi marker bị ẩn khỏi RGB.

Đánh giá lại đúng 180 ảnh test, cùng checkpoint, trên Torch 2.14.0 CPU tại laptop cho mAP50–95 **0,965032164**, gần như trùng **0,965032099** từ Colab. Không chọn hoặc chỉnh checkpoint qua lượt tái lập này. Ảnh/nhãn test giữ nguyên hash.

Trong bốn ca vật thể, thời gian `detect()` sau bỏ khung warm-up đầu có median khoảng **166–173 ms**, p95 từng ca khoảng **231–261 ms** ở ảnh inference 640. Số này không gồm toàn bộ vẽ/lưu ảnh hoặc truyền mạng; kết quả val theo batch không được dùng thay độ trễ camera từng khung.

Bằng chứng, video, CPU test, log đổi đích và cả lỗi phát triển được giữ tại [`experiments/evidence/multiclass_v1/`](../experiments/evidence/multiclass_v1/).

## Chạy lại

```powershell
.\.venv-yolo\Scripts\python.exe tools/run_live_demo.py --scenario objects_room --vision-config config/vision_objects.json
.\.venv-yolo\Scripts\python.exe tools/run_live_demo.py --scenario unknown_chair --vision-config config/vision_objects.json
.\.venv-yolo\Scripts\python.exe tools/check_diverse_objects.py --vision-config config/vision_objects.json
```

Model mới là mặc định của `config/vision_ego.json`; `config/vision_objects.json` giữ cấu hình ba lớp đã kiểm chứng. `demo_vat_the_da_dang.cmd` chọn cấu hình mới. Cấu hình box lịch sử được giữ tại `config/vision_ego_box_legacy.json`; muốn chạy lại bằng checkpoint cũ thì dùng `--vision-config config/vision_ego_box_legacy.json`. Mỗi lượt sinh runtime world riêng, giữ nguyên world người dùng đã lưu.

Các giới hạn vẫn còn: ảnh tổng hợp; sàn phẳng, camera lý tưởng; chân phải nhìn thấy mới chiếu khoảng cách đáng tin; pose đầu biết trước, encoder/IMU mô phỏng; chưa SLAM, ảnh điện thoại thật hoặc xe thật. Cụm gá camera chưa có đầy đủ hình học va chạm nên chưa xác nhận khả năng chui dưới đồ nội thất thực. Inference 640 tốn CPU hơn bản 320; Webots đồng bộ có thể chạy chậm theo đồng hồ thực, không thay watchdog trên ESP32.
