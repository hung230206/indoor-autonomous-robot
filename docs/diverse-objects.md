# Thử bàn, ghế và dép trong Webots

**Báo cáo lượt đầu dùng model box.** Phiên bản ba lớp sau khi train Colab có [kết quả riêng](multiclass-results.md), giữ nguyên các thất bại lịch sử bên dưới. Shortcut hiện chọn model ba lớp.

Ngày kiểm chứng: 12/11/2026. Chỉ là mô phỏng, chưa có xe thật.

Chạy `demo_vat_the_da_dang.cmd` để mở phòng có **1 bàn, 2 ghế, 2 dép**, kèm màn hình RGB/YOLO từ camera trước trên xe. Cảnh này đánh dấu cả 5 vật là **đã có trong bản đồ**. Robot lập đường vòng qua dép bằng bản đồ đó; không coi đây là bằng chứng detector đã học dép.

```powershell
.\.venv-yolo\Scripts\python.exe tools/run_live_demo.py --scenario objects_room
.\.venv-yolo\Scripts\python.exe tools/run_live_demo.py --scenario unknown_chair
```

Dời chấm đỏ để đổi đích. `SAFE_STOP` giữ chốt, cần Reload World. Launcher tạo world runtime riêng, không ghi đè world người dùng đã lưu.

## Hình học và bản đồ

Các vật được sinh bằng mã native, không tải mô hình bên ngoài:

| Vật | Kích thước chính | Hình học va chạm |
|---|---|---|
| Bàn | Mặt 72 × 60 cm, cao 70 cm | 4 chân vuông 4,5 cm và mặt bàn riêng |
| Ghế | Mặt 40 × 40 cm, cao 44 cm | 4 chân vuông 3 cm, mặt ghế, tựa lưng |
| Dép | Dài 25 cm, rộng khoảng 10 cm | Đế đa giác bo tròn, dày 1,8 cm; quai xấp xỉ bằng 3 đoạn, cao tối đa 5 cm |

Vật thể cố định, chưa mô phỏng dép mềm, vật bị đẩy, hoặc ghế đổ. Xe và cảm biến vẫn đơn giản hóa: ba tia cự ly lý tưởng quanh độ cao 5,5 cm; cụm camera có hình hiển thị nhưng chưa có khối va chạm/cột gá riêng. Không dùng kết quả này xác nhận khả năng chui dưới đồ nội thất của xe thật.

Định nghĩa tại `config/object_scenarios.json`; `scene_objects.py` sinh cả hình nhìn thấy và boundingObject. Với `map_known: true`, bản đồ nhận AABB bảo thủ của từng phần thấp; không tô kín cả vùng dưới mặt bàn/ghế. Đây là thông tin bản đồ cho trước, tương tự tường tĩnh. Bỏ `map_known` thì vật không được nạp vào bản đồ; phải dựa vào RGB/YOLO và đo cự ly. Sửa JSON rồi chạy lại launcher để tạo world khớp cấu hình.

Không chạy các cảnh này bằng bộ 2D: chiều cao vật cản và khoảng trống dưới bàn không thể biểu diễn đúng bằng tia 2D. Chương trình báo lỗi rõ nếu thử dùng bộ 2D.

## Kết quả của bốn cảnh cố định

| Ca | Bản đồ biết trước | Kết quả | Thời gian mô phỏng | Đánh giá |
|---|---|---|---:|---|
| `objects_room` | 5/5 vật | GOAL_REACHED | 24,736 s | Đạt, không ghi nhận va chạm; sai số đích thật 4,05 cm |
| `unknown_table` | Không | SAFE_STOP | 7,904 s | Không đạt: tâm xe vào ô bị inflate sau cập nhật bản đồ; không ghi nhận contact vật lý |
| `unknown_chair` | Không | SAFE_STOP | 10,144 s | Không đạt: contact vật lý với chân ghế rồi bộ đánh giá dừng xe |
| `unknown_slipper` | Không | GOAL_REACHED | 29,280 s | Đạt điều hướng trong ca này; YOLO gán sai nhãn dép thành `box` |

**Chỉ 2/4 ca đến đích.** Ca ghế không được gọi là tránh cản thành công hoặc dừng an toàn trước va chạm. Chưa sửa cảm nhận để khắc phục hai ca thất bại trong lần mở rộng hình học này.

Detector giữ checkpoint ego cũ, chỉ có lớp **box**, không fine-tune lại và không có số mAP mới cho bàn/ghế/dép. Ca dép có dự đoán `box` ngay khung đầu (confidence khoảng 0,595), sau đó tạo lớp thị giác và lập lại đường. Một lần đi vòng thành công dựa vào nhãn sai không chứng minh khả năng nhận diện dép. Chân ghế mảnh và vật thấp vẫn là điểm yếu cần dữ liệu mới và kiểm tra cảm biến.

Va chạm với vật mới được đánh giá bằng contact points của các Solid vật thể trong Webots. Trong bốn cảnh này, chúng là vật tĩnh, xe là vật động duy nhất. Dữ liệu contact/pose thật chỉ dùng đánh giá và dừng lượt thử khi vi phạm; không biến thành đầu vào nhận diện hoặc định vị điều hướng. Log ghi `collision=true` và `passed=false` khi đã va chạm. Với hộp/tường cũ vẫn giữ phép đánh giá hình học bảo thủ trước đây.

Pose điều hướng tiếp tục dùng encoder + IMU mô phỏng, biết trước pose xuất phát; không có SLAM. Camera RGB vẫn gắn trên xe. Chỉ góc nhìn quan sát bên ngoài chuyển sang xiên để thấy chân bàn/ghế; overlay camera native được ẩn trong cảnh mới để không che cảnh 3D, ảnh RGB/YOLO có cửa sổ và video riêng.

## Chạy lại và bằng chứng

```powershell
python -m unittest discover -s tests -v
python run.py batch
python tools/run_webots.py --all
.\.venv-yolo\Scripts\python.exe tools/check_diverse_objects.py
```

Lệnh cuối ghi bốn lượt, giữ cả lượt thất bại và trả exit code 1 nếu có ca không đạt; không đổi kỳ vọng thành SAFE_STOP để làm đẹp kết quả. Mỗi thư mục chứa summary, CSV, lớp bản đồ, dự đoán detector, world snapshot, video toàn cảnh và video camera trên xe.

41 unit test qua; 10 ca 2D và 10 ca Webots nền vẫn đúng kỳ vọng (8 đến đích, 2 NO_PATH). Bằng chứng mới tại [`experiments/evidence/diverse_objects_v1/`](../experiments/evidence/diverse_objects_v1/); không cộng bốn cảnh này vào số mAP hoặc bộ ca ego cũ.

Bước phát triển tiếp phù hợp là tạo dữ liệu camera trên xe cho chân bàn/ghế và vật thấp, đánh giá theo từng loại, rồi sửa cảm nhận/quy hoạch cho hai ca lỗi. Nhãn đồ nội thất toàn bộ không tự bảo đảm phép chiếu chân bbox xuống sàn đúng với từng chân mảnh.
