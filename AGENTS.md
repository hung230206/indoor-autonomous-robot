# Ngữ cảnh làm việc

- Giao tiếp bằng tiếng Việt. Đọc `tài liệu/AGENTS.md` để hiểu phạm vi toàn dự án và `README.md`, `docs/stage1-results.md` để biết trạng thái triển khai mới nhất.
- Giai đoạn hiện tại: chuẩn bị giai đoạn 2, M6–M7 đã được người dùng yêu cầu. Đã có thiết kế đấu nối, chưa mua/lắp xe hoặc viết firmware. Không mở rộng sang SLAM, ROS 2, YOLO nếu chưa được yêu cầu.
- Người dùng đã chốt phần cứng theo bản Word ngày 06/11/2026; xem `docs/hardware-decision.md`. Đây là xác nhận cấu hình, chưa có bằng chứng mua/lắp xe. Dùng cấu hình này khi chuẩn bị giai đoạn 2.
- Sơ đồ và quy trình: `docs/hardware/wiring.md`; chân chuẩn: `config/hardware_v1.json`. Người dùng xác nhận chưa mua. GPIO là số IO, không phải header index. BMS cụ thể và dòng kẹt motor chưa biết; không tự coi sơ đồ là đã thử điện.
- Đổi cấu hình phần cứng cần đồng bộ bảng/hình bằng `python tools/build_hardware_docs.py` và kiểm tra `python tools/check_hardware_design.py`; PNG cần render lại từ SVG. Builder giữ nguyên checklist/nhật ký đo đã tồn tại, không ghi đè kết quả người dùng điền.
- Lõi Python nằm trong `src/robot_nav/`; `run.py` chạy trực tiếp từ checkout. Giữ A*, state machine, safety và controller độc lập với Webots.
- Đơn vị nội bộ: mét, giây, radian; x/y trên sàn, +z hướng lên, theta ngược chiều kim đồng hồ. Command là vận tốc tiếp tuyến hai bánh m/s.
- Thay cấu hình hoặc world generator phải tạo lại world. Không sửa world thủ công rồi để JSON lệch với hình học mô phỏng.
- Sau thay đổi hành vi, chạy `python -m unittest discover -s tests -v`, `python run.py batch`; thay đổi Webots cần chạy `python tools/run_webots.py --all` khi Webots có sẵn.
- Chỉ báo kết quả đã có trong log. Phân biệt 2D động học, Webots vật lý và xe thật. Hai ca `NO_PATH` được tính là dừng đúng, không phải đến đích.
- Giữ bằng chứng trong `experiments/evidence/`; lượt thử thường ở `experiments/runs/`. Không ghi đè bằng chứng đã báo cáo mà không cập nhật báo cáo.
