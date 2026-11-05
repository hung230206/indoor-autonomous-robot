# Robot tự hành trong nhà — giai đoạn 1

Robot 2WD đi từ A đến B trên bản đồ có sẵn, phát hiện vật cản mới bằng cảm biến mô phỏng hoặc lớp thị giác YOLO, dừng, cập nhật occupancy grid và lập lại đường A*. Mã nguồn dùng chung cho mô phỏng 2D và Webots. Chưa có phần xe thật, ArUco hay ESP32.

Đã bổ sung [YOLO11n nhận diện hộp từ camera Webots](docs/yolo.md), checkpoint và dữ liệu kiểm chứng tổng hợp. [Báo cáo Word 6 trang và kết quả](reports/README.md) giải thích kỹ thuật, FSM, huấn luyện, so sánh và giới hạn. Chế độ mặc định vẫn là bản dùng cảm biến; chạy YOLO bằng môi trường riêng và cờ `--yolo`.

Phần cứng cho các giai đoạn sau đã được người dùng chốt theo bản Word ngày 06/11/2026; xem [cấu hình đã chốt](docs/hardware-decision.md). Chưa có xác nhận đã mua hoặc lắp xe.

Đã chuẩn bị [sơ đồ nguồn, bảng GPIO và hướng dẫn lắp M6–M7](docs/hardware/wiring.md), gồm hình SVG/PNG, checklist và mẫu nhật ký đo. Cấu hình chân nằm trong `config/hardware_v1.json`; chạy `python tools/check_hardware_design.py` để kiểm tra nhất quán chân và tính bộ chia Echo. Đây là thiết kế chưa thử điện; chưa có firmware ESP32.

## Chạy nhanh trên máy hiện tại

Mở PowerShell trong thư mục project:

```powershell
cd 'C:\Users\hungt\Documents\ChatGPT\Niên luận cơ sở'
python run.py demo --gui
```

Hoặc nhấp đúp `Launch-Demo.cmd` để mở giao diện.

Giao diện chạy kịch bản `replanning`: một hộp xuất hiện sau 3 giây, chắn đường ban đầu. Đường nét đứt là A* ban đầu, xanh dương là đường hiện tại, xanh lá là quỹ đạo xe. Vùng xám là các ô cấm sau khi mở rộng vật cản theo kích thước robot.

- Chuột trái: chọn đích mới trong ô đi được, tiếp tục điều hướng.
- Chuột phải: đặt hộp chưa có trên bản đồ; robot phải tự phát hiện bằng cảm biến. Không cho đặt ngay lên xe.
- `Pause / Resume`: tạm dừng/tiếp tục mô phỏng.
- `STOP`: dừng có chốt; chọn một đích hợp lệ để bắt đầu lại.
- `Reset`: khởi động lại kịch bản.
- Đóng cửa sổ: lưu log vào `experiments/runs/demo/`.

Các phụ thuộc giao diện đã có trên máy. Trên máy mới, cài Python 3.10 trở lên, sau đó:

```powershell
python -m pip install -r requirements.txt
```

Lõi thuật toán, unit test và controller Webots chỉ dùng thư viện chuẩn Python. `matplotlib` và `Pillow` dùng cho giao diện và xuất hình/GIF. Phiên bản đã kiểm tra: Python 3.14.4, Matplotlib 3.11.1, Pillow 12.2.0, Webots R2025a.

## Mở mô phỏng Webots

Webots R2025a đã được cài cho tài khoản hiện tại tại `%LOCALAPPDATA%\Programs\Webots`; không cần mua linh kiện để chạy giai đoạn 1.

```powershell
python run.py world --scenario replanning
& "$env:LOCALAPPDATA\Programs\Webots\msys64\mingw64\bin\webots.exe" --mode=pause "$PWD\worlds\stage1.wbt"
```

Nhấn nút chạy trong Webots. Robot dùng hai motor vật lý, bánh đỡ ma sát thấp và ba DistanceSensor. Hộp màu cam xuất hiện sau 3 giây. Đường ban đầu màu xám, đường đang dùng màu xanh. Kết thúc, controller dừng motor, ghi log và chuyển Webots sang pause. Để chạy lại từ đầu, chọn **Simulation → Reset**.

Lấy pose lý tưởng từ Supervisor là lựa chọn có chủ đích của giai đoạn 1. Đây không phải kết quả định vị bằng camera. World được tạo từ cùng JSON với thuật toán, không tải PROTO từ Internet. Đổi `config/robot.json` hoặc `config/scenarios.json` thì cần chạy lại lệnh tạo world.

Chạy tự động, Webots tự đóng sau từng ca:

```powershell
python tools/run_webots.py --all
python tools/run_webots.py --scenario replanning --record
```

Lệnh `--record` chụp trực tiếp khung hình Webots, ghép MP4 bằng ffmpeg từ gói `imageio-ffmpeg` trong requirements, rồi xóa các khung hình tạm. Video được lưu cùng log của ca chạy. Nếu cài Webots ở chỗ khác, đặt biến `WEBOTS_HOME`. Launcher tự dừng tiến trình do nó tạo khi quá thời gian chờ.

## Kiểm thử và xuất bằng chứng

```powershell
python -m unittest discover -s tests -v
python run.py batch
python run.py demo --scenario replanning --export
python run.py demo --scenario no_path
python tools/run_webots.py --scenario dynamic_no_path
```

`batch` có 10 kịch bản cố định trong `config/scenarios.json`: sàn trống, hộp, chân bàn, cửa thông, hai vách so le, hộp mới, vách mới, xuất phát ngược hướng, tường bít hoàn toàn và khe quá hẹp. Tám ca kỳ vọng đến đích, hai ca kỳ vọng `NO_PATH`. Vì thế **10/10 đúng kỳ vọng** tương ứng **8 ca đến đích + 2 ca dừng đúng**, không phải 10 lần đến đích.

Unit test kiểm tra A* với Dijkstra trên 15 bản đồ ngẫu nhiên có seed, chặn cắt góc, mở rộng vật cản, khe hẹp, dữ liệu cũ/NaN/thiếu, STOP, xác nhận vật cản qua hai khung hình và tuổi thọ bản đồ động; đồng thời chạy đủ 10 kịch bản 2D.

Bằng chứng lần triển khai này nằm trong `experiments/evidence/`. Xem [báo cáo giai đoạn 1](docs/stage1-results.md) để biết số đo và giới hạn. Những lần chạy thường ngày nằm trong `experiments/runs/` và được bỏ qua bởi Git.

## Đầu vào và đầu ra

Ví dụ đầu vào kịch bản:

```json
{
  "name": "replanning",
  "start": [0.35, 1.05, 0],
  "goal": [2.65, 1.05],
  "obstacles": [],
  "spawn": [{"at_s": 3.0, "rect": [1.3, 0.85, 1.6, 1.25]}],
  "expected": "GOAL_REACHED",
  "require_replan": true
}
```

`start = [x_m, y_m, theta_rad]`; `goal = [x_m, y_m]`; hình chữ nhật là `[xmin, ymin, xmax, ymax]` theo mét. `spawn` thuộc môi trường mô phỏng; lõi điều hướng chỉ biết vật cản mới qua số đo, không được cung cấp trực tiếp tọa độ hộp.

Mỗi lần chạy tạo:

| Tệp | Nội dung |
|---|---|
| `trajectory.csv` | Thời gian, mode, pose, ba khoảng cách, đích, mã đường, lệnh bánh, trạng thái, lý do dừng, cờ va chạm |
| `paths.json` | Các lần lập đường, waypoint và thời gian thực thi A* |
| `events.json` | Lịch sử chuyển trạng thái |
| `map_static.csv`, `map_dynamic.csv`, `map_inflated.csv` | Ba lớp bản đồ cuối lượt chạy, ô chiếm = 1 |
| `summary.json` | Kết quả so với kỳ vọng, quãng đường, sai số đích, số lần lập đường |
| `config.json`, `scenario.json`, `environment.json` | Cấu hình và môi trường để tái lập |
| `trajectory.png`, `demo.gif` | Hình/quay lại 2D khi dùng `--export` |
| `scene.jpg`, `webots.mp4` | Khung hình và clip Webots khi dùng `--record` |

Ví dụ: `state = GOAL_REACHED`, `plans = 4` nghĩa là một lần lập đường đầu tiên và ba lần lập lại đường. Lệnh bánh trong CSV là **m/s**, adapter Webots đổi sang **rad/s** bằng bán kính bánh. Không gửi trực tiếp các giá trị này thành PWM cho xe thật.

## Thiết kế thuật toán

- Sàn 3 × 2 m; lưới 0,10 m/ô. Hàng 0 ở dưới; x tăng sang phải, y tăng lên trên; góc ngược chiều kim đồng hồ từ +x. Webots dùng ENU, z hướng lên.
- Robot dài 0,18 m, rộng 0,15 m. Bán kính bao khoảng 0,117 m; thêm khoảng hở 0,04 m. Lưới mở rộng bảo thủ theo khoảng cách từ tâm ô đến hình vuông của ô bị chiếm, cả biên sàn.
- A* 8 hướng, heuristic octile, không đi chéo qua hai ô chắn góc. Không tìm được đường trả về danh sách rỗng và giữ motor bằng 0.
- Bộ bám waypoint quay tại chỗ trước khi tiến, giảm tốc gần waypoint. Chưa dùng Pure Pursuit hay làm mượt đường. Tốc độ tiến tối đa đề xuất 0,16 m/s, giới hạn từng bánh 0,24 m/s.
- Cảm biến trước/trái/phải là ba tia lý tưởng, tầm 0,8 m. Điểm chạm được đổi sang tọa độ map qua pose và vị trí lắp. Phải thấy cùng ô ở hai lần đo liên tiếp mới xác nhận; ô động hết hạn sau 120 giây nếu không được quan sát lại.
- Đường bị chặn: trả lệnh 0 ở trạng thái `OBSTACLE_STOP`, chu kỳ sau mới lập lại đường. Dữ liệu thiếu/lỗi/quá 0,25 giây, khoảng cách dưới 0,10 m hoặc STOP dẫn đến `SAFE_STOP` có chốt.

Các ngưỡng trên đã chọn cho **bản mô phỏng đầu tiên**; chưa được xác nhận phù hợp với phần cứng thật.

## Cấu trúc mã nguồn

```text
config/                  Hình học, ngưỡng điều khiển, 10 kịch bản
src/robot_nav/
  models.py              Dữ liệu pose/range/command và interface adapter
  grid.py                Static/dynamic grid, inflation, chuyển số đo lên map
  planning.py            A*
  navigation.py          State machine, an toàn, waypoint controller
  simulation.py          Động học vi sai 2D, raycast, đánh giá kịch bản
  webots_world.py        Tạo world và robot 2WD native
  webots_adapter.py      Supervisor pose, DistanceSensor, motor, ghi bằng chứng
  recording.py           CSV/JSON
  viewer.py              Giao diện 2D, PNG/GIF
controllers/stage1/       Entry point controller Webots
worlds/                  Các world được tạo từ cấu hình
tests/                   Unit test và scenario test
tools/run_webots.py       Launcher và xuất MP4
experiments/evidence/     Bằng chứng mô phỏng đã chạy
```

## Giới hạn đã biết

Hai bộ mô phỏng dùng pose hoàn hảo và cảm biến không nhiễu, một tia mỗi hướng. Không mô phỏng đầy đủ hình nón siêu âm, giao thoa, mất echo, trễ camera/Wi-Fi, trượt bánh và nguồn yếu. Vật cản mảnh hoặc nằm giữa các tia vẫn có thể bị bỏ sót. Bộ thử hữu hạn không chứng minh tránh va chạm trong mọi bố trí.

Không cho phép tự khôi phục sau lỗi cảm biến/STOP; người dùng phải bắt đầu lại. `NO_PATH` là kết quả trên bản đồ đã biết ở thời điểm đó, không phải thuật toán khám phá phòng. Bản đồ động chỉ thêm điểm chạm có thời hạn, chưa suy luận đầy đủ hình dạng vật cản. Một vật cản mới có thể cần nhiều lần lập lại đường khi xe quan sát thêm cạnh của nó.

GPU Intel trên máy được Webots đánh giá dưới cấu hình khuyến nghị. Các bài kiểm tra tự động tắt render để chạy nhanh; xem trực tiếp dùng đồ họa đơn giản, không cần bật bóng đổ/khử răng cưa.

Tài liệu API sử dụng: [DistanceSensor](https://cyberbotics.com/doc/reference/distancesensor), [Supervisor](https://cyberbotics.com/doc/reference/supervisor), [tham số khởi động Webots](https://cyberbotics.com/doc/guide/starting-webots).
