# Ngữ cảnh làm việc

- Kết quả ego cuối: `docs/ego-results.md`, `experiments/evidence/ego_v1/`; 29 test qua, 4 ca ego đúng kỳ vọng (3 đến đích, 1 SAFE_STOP), 10 ca Webots nền vẫn đúng kỳ vọng. Model ego test 60 ảnh/37 hộp, mAP50–95 94,93%. Có các lượt encoder-only bị SAFE_STOP ở development_failures; không xóa hoặc tính chúng là thành công. Heading cuối dùng IMU, encoder đo quãng đường; cấu hình hiệu chuẩn riêng `config/odometry_webots.json` dùng GT đo offline trên sàn trống, không lấy từ quỹ đạo test.

- Yêu cầu mới nhất 06/11/2026: camera trước **gắn trên xe**, thay kiến trúc điện thoại trên cao. Xem `docs/ego-vision.md`. `tools/run_live_demo.py` mặc định ego; `--overhead` giữ bản cũ. `vision_ego.json`, `onboard.py`, `webots_ego.py` triển khai camera RGB trên thân xe, checkpoint riêng, phép chiếu mép chân bbox xuống sàn, fusion range và pose odometry encoder + IMU. Không dùng pose Supervisor để điều hướng ego; GT chỉ tạo nhãn và đánh giá. Pose đầu phải biết trước; chưa có SLAM hay relocalization.
- Báo cáo Word và số mAP 94,97%/4 ca cũ bên dưới chỉ áp dụng camera trên cao. Không dùng chúng cho model ego. Encoder và IMU mới là thiết bị mô phỏng: motor TT/nguồn định vị thực chưa được chọn bổ sung; không tự coi cấu hình phần cứng ban đầu có encoder.

- Giao tiếp bằng tiếng Việt. Đọc `tài liệu/AGENTS.md` để hiểu phạm vi toàn dự án và `README.md`, `docs/stage1-results.md` để biết trạng thái triển khai mới nhất.
- Công việc hiện tại: mở rộng giai đoạn 1 với YOLO theo yêu cầu người dùng ngày 06/11/2026. Đã fine-tune YOLO11n một lớp box bằng ảnh camera Webots và tích hợp vào grid/A*/FSM; xem `docs/yolo.md`, `reports/README.md`. Không tự mở rộng sang SLAM/ROS 2. M6–M7 mới có thiết kế đấu nối, chưa mua/lắp xe hoặc viết firmware.
- Phân biệt số liệu: detector test trên 40 ảnh tổng hợp (70 hộp); 4 ca YOLO (3 đến đích, 1 SAFE_STOP); 10 ca Webots nền (8 đến đích, 2 NO_PATH). Chưa có ảnh thật, pose vẫn Supervisor. Không gọi fine-tune/tích hợp là kiến trúc YOLO mới hoặc bảo đảm an toàn thời gian thực.
- `config/vision.json` quy định camera/model **bản trên cao**, tắt range mapping. `config/vision_ego.json` quy định **camera trên xe**, kết hợp range mapping. `Grid.vision` tách lớp thị giác khỏi lớp cự ly. Không dùng tọa độ hộp của simulator để giả làm dự đoán. GT chỉ để tạo nhãn dữ liệu và đánh giá.
- YOLO dùng `.venv-yolo`, `requirements-yolo.txt`; launcher chọn interpreter camera bằng runtime.ini tại máy (Git bỏ qua). Giữ nguyên tập test/provenance khi phát triển model mới. Báo cáo Word dựng bằng bundled Python/docx, render QA đã dùng Word native vì máy không có LibreOffice.
- Người dùng đã chốt phần cứng theo bản Word ngày 06/11/2026; xem `docs/hardware-decision.md`. Đây là xác nhận cấu hình, chưa có bằng chứng mua/lắp xe. Dùng cấu hình này khi chuẩn bị giai đoạn 2.
- Sơ đồ và quy trình: `docs/hardware/wiring.md`; chân chuẩn: `config/hardware_v1.json`. Người dùng xác nhận chưa mua. GPIO là số IO, không phải header index. BMS cụ thể và dòng kẹt motor chưa biết; không tự coi sơ đồ là đã thử điện.
- Đổi cấu hình phần cứng cần đồng bộ bảng/hình bằng `python tools/build_hardware_docs.py` và kiểm tra `python tools/check_hardware_design.py`; PNG cần render lại từ SVG. Builder giữ nguyên checklist/nhật ký đo đã tồn tại, không ghi đè kết quả người dùng điền.
- Lõi Python nằm trong `src/robot_nav/`; `run.py` chạy trực tiếp từ checkout. Giữ A*, state machine, safety và controller độc lập với Webots.
- Đơn vị nội bộ: mét, giây, radian; x/y trên sàn, +z hướng lên, theta ngược chiều kim đồng hồ. Command là vận tốc tiếp tuyến hai bánh m/s.
- Thay cấu hình hoặc world generator phải tạo lại world. Không sửa world thủ công rồi để JSON lệch với hình học mô phỏng.
- Sau thay đổi hành vi, chạy `python -m unittest discover -s tests -v`, `python run.py batch`; thay đổi Webots cần chạy `python tools/run_webots.py --all` khi Webots có sẵn.
- Chỉ báo kết quả đã có trong log. Phân biệt 2D động học, Webots vật lý và xe thật. Hai ca `NO_PATH` được tính là dừng đúng, không phải đến đích.
- Giữ bằng chứng trong `experiments/evidence/`; lượt thử thường ở `experiments/runs/`. Không ghi đè bằng chứng đã báo cáo mà không cập nhật báo cáo.
