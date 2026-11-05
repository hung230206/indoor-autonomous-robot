# Kết quả triển khai giai đoạn 1

Lần kiểm chứng ban đầu: **06/11/2026**. Phạm vi là mô phỏng; chưa kiểm chứng xe thật.

Đã triển khai M1–M5: world Webots native với robot 2WD, occupancy grid và inflation, A* 8 hướng, bám waypoint, phát hiện cản bằng ba tia khoảng cách, dừng/lập lại đường, CSV/JSON và video demo.

## Kết quả trên bộ 10 kịch bản

Cả mô phỏng động học 2D và Webots R2025a đạt **10/10 kết quả đúng kỳ vọng**: **8/8 ca có đường đến đích**, **2/2 ca được thiết kế không có đường dừng với `NO_PATH`**. Không ghi nhận va chạm theo phép kiểm tra hình học bảo thủ, hoặc tâm xe đi vào ô cấm đã inflate trong các lượt này. Đây là kết quả của bộ ca cố định, không phải xác suất thành công ở môi trường tùy ý.

| Kịch bản | Kết quả Webots | Thời gian 2D (s) | Thời gian Webots (s) | Quãng đường Webots (m) | Số lần A* Webots |
|---|---|---:|---:|---:|---:|
| open | GOAL_REACHED | 25.86 | 26.02 | 2.788 | 1 |
| box | GOAL_REACHED | 25.60 | 25.76 | 2.746 | 1 |
| legs | GOAL_REACHED | 25.92 | 26.08 | 2.791 | 1 |
| corridor | GOAL_REACHED | 21.57 | 21.57 | 2.257 | 1 |
| s_curve | GOAL_REACHED | 40.58 | 41.12 | 4.054 | 2 |
| replanning | GOAL_REACHED | 28.93 | 30.11 | 2.743 | 4 |
| new_barrier | GOAL_REACHED | 32.00 | 32.48 | 2.830 | 6 |
| reverse_heading | GOAL_REACHED | 28.96 | 28.93 | 2.843 | 1 |
| no_path | NO_PATH | 0.03 | 0.03 | 0.000 | 1 |
| narrow_gap | NO_PATH | 0.03 | 0.03 | 0.000 | 1 |

Sai số đích lớn nhất trong 8 lượt Webots đến đích: **4.35 cm**, dưới ngưỡng cấu hình 4,5 cm. Thời gian thực thi A* lớn nhất của lượt benchmark: **1.83 ms**. Số này đo bằng đồng hồ thực trên laptop; thời gian đến đích trong bảng là thời gian mô phỏng.

Số lần A* bao gồm lần đầu. `replanning` có 4 lần lập đường (3 lần lập lại); `new_barrier` có 6 lần (5 lần lập lại). Bản đồ động chỉ biết các điểm chạm đã quan sát; khi thấy thêm cạnh hộp, xe có thể phải dừng và lập lại đường nhiều lần. `s_curve` cũng có một lần lập lại đường trong cấu hình này; chưa tối ưu việc tái lập kế hoạch dư thừa.

## Ca an toàn bổ sung

`dynamic_no_path` bắt đầu với cửa thông, sau 3 giây xuất hiện hộp đóng kín cửa. Cả 2D và Webots kết thúc `NO_PATH` sau khoảng **3,10 giây**, có trạng thái `OBSTACLE_STOP` trước khi lập lại đường và lệnh cuối hai bánh bằng 0. Ca này lưu riêng, không cộng vào mẫu 10 ca ở bảng.

Bộ **14 test** đã qua: kiểm tra A* so với Dijkstra trên 15 bản đồ có seed, cắt góc, inflation, ô ngoài map, khe hẹp, xác nhận/TTL cản động, pose cũ, dữ liệu cảm biến thiếu/NaN/tương lai, STOP có chốt, các ca di chuyển và thao tác giao diện chọn đích/thêm cản/STOP. Log tại `experiments/evidence/tests.txt`.

## Bằng chứng và cách chạy lại

- [Kết quả 10 ca Webots](../experiments/evidence/webots/results.csv)
- [Kết quả 10 ca động học 2D](../experiments/evidence/kinematic_batch/results.csv)
- [Video Webots thực tế, khoảng 30 giây](../experiments/evidence/webots_video/replanning/webots.mp4)
- [Quỹ đạo và bản đồ 2D của ca lập lại đường](../experiments/evidence/kinematic_replanning/trajectory.png)
- [Hình A* sàn trống](../experiments/evidence/planning_examples/open.png), [hộp cố định](../experiments/evidence/planning_examples/box.png), [không có đường](../experiments/evidence/planning_examples/no_path.png)
- Ca đóng kín cửa: `experiments/evidence/webots_safety/dynamic_no_path/` và `experiments/evidence/kinematic_safety/`.

Video lấy trực tiếp khung hình Webots và ghép bằng ffmpeg. Log CSV và `paths.json`/`events.json` trong cùng thư mục cung cấp lịch sử để đối chiếu. Video được quay trong một lượt riêng; thời gian A* đo bằng đồng hồ thực có thể khác lượt benchmark.

```powershell
python -m unittest discover -s tests -v
python run.py batch
python tools/run_webots.py --all
python tools/run_webots.py --scenario dynamic_no_path
python tools/run_webots.py --scenario replanning --record
```

## Các giả định và phần chưa chứng minh

Pose lấy lý tưởng từ Supervisor. Ba cảm biến là generic DistanceSensor một tia mỗi hướng, đáp ứng bằng khoảng cách mét và không có nhiễu. Không coi đây là mô hình đầy đủ HC-SR04. Robot có thể bỏ sót vật nằm giữa các tia; chưa kiểm tra trễ mạng/video, mất echo hoặc trượt bánh thực.

Kiểm tra va chạm dùng đường tròn bao robot so với hình chữ nhật vật cản và biên sàn; kiểm tra ô cấm dùng tâm robot so với lưới đã mở rộng. Không dùng kết quả này để khẳng định an toàn phần cứng hay tránh va chạm ở mọi tốc độ.

Bộ bám waypoint hiện quay tại chỗ, chưa so sánh với Pure Pursuit. Biên an toàn và rasterization có thể loại một số đường thực tế còn lọt được. Mọi thông số hình học xe vẫn là giả định cho mô phỏng.

Trong phạm vi các cổng nghiệm thu đề xuất của giai đoạn 1, đã có mã nguồn, 8 ca đến đích trên 10 ca kiểm soát, ca lập lại đường, dừng khi hết đường, log và video. Việc quyết định mua linh kiện nên dựa thêm trên xác nhận của người dùng/giảng viên về phạm vi và thiết kế nguồn thực tế.
