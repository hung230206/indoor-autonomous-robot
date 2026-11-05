# Ngữ cảnh làm việc

- Giao tiếp bằng tiếng Việt. Đọc `tài liệu/AGENTS.md` để hiểu phạm vi toàn dự án và `README.md`, `docs/stage1-results.md` để biết trạng thái triển khai mới nhất.
- Giai đoạn hiện tại: 1, mô phỏng. Không mở rộng sang xe thật, SLAM, ROS 2, YOLO nếu chưa được yêu cầu.
- Người dùng đã chốt phần cứng theo bản Word ngày 06/11/2026; xem `docs/hardware-decision.md`. Đây là xác nhận cấu hình, chưa có bằng chứng mua/lắp xe. Dùng cấu hình này khi chuẩn bị giai đoạn 2.
- Lõi Python nằm trong `src/robot_nav/`; `run.py` chạy trực tiếp từ checkout. Giữ A*, state machine, safety và controller độc lập với Webots.
- Đơn vị nội bộ: mét, giây, radian; x/y trên sàn, +z hướng lên, theta ngược chiều kim đồng hồ. Command là vận tốc tiếp tuyến hai bánh m/s.
- Thay cấu hình hoặc world generator phải tạo lại world. Không sửa world thủ công rồi để JSON lệch với hình học mô phỏng.
- Sau thay đổi hành vi, chạy `python -m unittest discover -s tests -v`, `python run.py batch`; thay đổi Webots cần chạy `python tools/run_webots.py --all` khi Webots có sẵn.
- Chỉ báo kết quả đã có trong log. Phân biệt 2D động học, Webots vật lý và xe thật. Hai ca `NO_PATH` được tính là dừng đúng, không phải đến đích.
- Giữ bằng chứng trong `experiments/evidence/`; lượt thử thường ở `experiments/runs/`. Không ghi đè bằng chứng đã báo cáo mà không cập nhật báo cáo.
