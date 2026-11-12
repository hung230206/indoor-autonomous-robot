# Huấn luyện YOLO đa lớp trên Colab GPU

Chuẩn bị ngày 12/11/2026 theo lựa chọn của người dùng. **Bộ dữ liệu và notebook đã sẵn sàng; chưa chạy lượt train đầy đủ trên GPU Colab, chưa có mAP test của model mới.** Model đang dùng trong demo vẫn là `models/yolo_ego/best.pt`, chỉ có lớp box.

Các model box trước đây được train trực tiếp trên CPU laptop bằng Python, Ultralytics YOLO và PyTorch. Colab là môi trường máy ảo có thể cấp GPU; không phải một mô hình hoặc thuật toán train khác. Máy hiện tại có Intel UHD và Torch CPU, `torch.cuda.is_available() == False`. Ultralytics cho phép chọn [thiết bị train CPU/GPU](https://docs.ultralytics.com/modes/train/); GPU Colab có [quota và phụ thuộc tài nguyên](https://research.google.com/colaboratory/faq.html).

## Chạy trên Colab

1. Mở **[notebook train_robot_objects trên Colab](https://colab.research.google.com/github/hung230206/indoor-autonomous-robot/blob/main/notebooks/train_robot_objects.ipynb)**.
2. Chọn **Runtime → Change runtime type → GPU** (T4 nếu được cấp), rồi chạy các ô từ trên xuống hoặc Run all. Ô đầu kiểm tra CUDA, không âm thầm chuyển sang CPU.
3. Notebook tự tải ZIP dữ liệu từ repo, kiểm tra SHA-256, train, đánh giá test và tải ZIP kết quả về máy. Giữ ZIP kết quả gồm `best.pt`, `last.pt`, tham số, biểu đồ, số đo từng lớp và provenance để tích hợp sau.

Không cần cài Webots trong Colab, không cần tự gán nhãn hoặc upload ảnh thủ công. Nếu tải GitHub không được, đổi `USE_LOCAL_UPLOAD=True` và chọn `artifacts/training/robot_objects_v1_dataset.zip` tại máy. Notebook cũng có bản local tại `notebooks/train_robot_objects.ipynb` để upload vào Colab.

Mặc định checkpoint nằm trong máy ảo Colab; tải kết quả trước khi phiên kết thúc. Có thể bật `SAVE_TO_DRIVE=True`; bạn tự cấp quyền Drive khi Colab yêu cầu. Nếu GPU báo hết bộ nhớ, giảm `BATCH` từ 16 xuống 8. Notebook dùng Ultralytics **8.4.202**, giữ Torch CUDA của Colab thay vì cài bản Torch CPU trong requirements của laptop.

## Bộ dữ liệu mới

**1.200 ảnh RGB 640 × 480**, từ camera trước trên xe ở cùng chiều cao/pitch/FOV của demo. Mỗi ảnh là một cảnh có seed riêng, không chia khung liền kề của cùng lượt chạy qua train/val/test. Không sửa hoặc trộn lại tập test box cũ.

| Tập | Ảnh | Hộp `box` | Chân `furniture_leg` | Dép `slipper` | Ảnh không có nhãn |
|---|---:|---:|---:|---:|---:|
| Train | 840 | 479 | 1.633 | 446 | 93 |
| Validation | 180 | 112 | 330 | 101 | 14 |
| Test | 180 | 114 | 326 | 104 | 19 |
| Tổng | 1.200 | 705 | 2.289 | 651 | 126 |

Thứ tự lớp cố định: **0 box, 1 furniture_leg, 2 slipper**. Mỗi chân bàn/ghế có một mask màu nhận diện riêng, từ đó lấy bbox phần pixel nhìn thấy. Mặt bàn, mặt ghế và tựa lưng chỉ che khuất, không được gán thành chân. Dép được gán cả đế và quai thành một đối tượng. Recognition ground truth chỉ được bật trong chế độ thu thập dữ liệu; không thay YOLO khi điều hướng.

Có biến thiên kích thước, chân vuông/tròn, độ mảnh chân, màu vật, màu sàn, ánh sáng, hướng nhìn, vật che khuất và vật cắt biên. Chân/dép bị cắt ảnh vẫn có nhãn detection và cờ `bottom_clipped` trong manifest; điều đó không bảo đảm phép chiếu chân bbox xuống sàn hợp lệ. Cùng họ hình học procedural xuất hiện ở cả ba tập, nên đây chưa phải kiểm tra trên đồ nội thất thực hoặc thiết kế hoàn toàn mới.

ZIP **13.597.250 byte** (khoảng 13,6 MB):

```text
artifacts/training/robot_objects_v1_dataset.zip
SHA-256: ed4877d4ca019968d0f09a77e531aef36c72bf91ccd8ffbcd1717004592418f5
```

ZIP gồm ảnh, nhãn YOLO, manifest seed/hash/hình học/annotation, YAML portable, ảnh xem nhãn và hai script train/kiểm tra độc lập với repo. Kiểm tra gồm hash ảnh/nhãn, kích thước ảnh, định dạng và biên bbox, khớp annotation, seed duy nhất, không có ảnh giống hệt giữa các tập, đủ cả ba lớp ở mỗi tập. Đây là kiểm tra tính toàn vẹn dữ liệu, không phải số đo detector.

## Cấu hình và đánh giá

Notebook fine-tune **YOLO11n từ trọng số COCO**, 60 epoch, `imgsz=640`, batch 16, seed 42, không freeze backbone, early stopping patience 15. Augmentation giữ hướng trọng lực (không lật dọc hoặc xoay ảnh), có lật ngang và thay đổi màu/kích thước/mosaic. Ảnh 640 nhằm giữ chi tiết chân mảnh; khi đưa về laptop phải đo lại chất lượng và độ trễ, không giả định tốc độ của cấu hình 320 cũ.

Checkpoint `best.pt` được chọn bằng validation trong train. Sau đó mới đánh giá một lần trên 180 ảnh test, ghi precision, recall, mAP50, mAP50–95 theo lớp. Không dùng test để chọn epoch hoặc điều chỉnh cấu hình. Không so ngang mAP bộ ba lớp mới với mAP bộ box cũ; không suy từ mAP sang tỷ lệ robot đến đích.

Đã kiểm tra syntax của mọi ô notebook, tính portable của ZIP sau giải nén, và chạy thử hàm train/validation/export bằng **1 epoch, 42 ảnh train + 9 ảnh val** từ một bộ smoke riêng có namespace seed khác. Không chạy test của bộ 1.200 ảnh trong bước thử pipeline. Checkpoint smoke chỉ để xác minh chương trình chạy, không được cài vào demo hoặc gọi là model đã huấn luyện xong. Phiên Colab/CUDA thực chưa được thực thi trong bước chuẩn bị này.

45 unit test qua; 10 ca 2D và 10 ca Webots nền vẫn đúng kỳ vọng (8 đến đích, 2 NO_PATH). Bằng chứng chuẩn bị tại `experiments/evidence/colab_prep_v1/`. Hai lỗi bàn/ghế trong `diverse_objects_v1` vẫn là lỗi đã ghi nhận; chưa có model mới hay thử điều hướng mới để tuyên bố khắc phục.

## Tái tạo tại máy có Webots

```powershell
.\.venv-yolo\Scripts\python.exe tools/collect_object_dataset.py --count 1200 --output experiments/runs/my_objects_dataset
.\.venv-yolo\Scripts\python.exe tools/validate_object_dataset.py experiments/runs/my_objects_dataset --minimum-class-images 30 --sheet experiments/runs/my_objects_dataset/labels-preview.jpg
.\.venv-yolo\Scripts\python.exe tools/build_colab_bundle.py experiments/runs/my_objects_dataset --output experiments/runs/my_colab_bundle
```

Bộ sinh từ chối thư mục dữ liệu đã có nội dung; builder tạo ZIP theo chế độ exclusive. `--reuse-archive` chỉ được dùng nếu nội dung ZIP khớp hoàn toàn nguồn hiện có, để tái tạo notebook/metadata. Không ghi đè ZIP đã công bố khi đổi dữ liệu/script đóng gói: tạo phiên bản mới và cập nhật hash/notebook tương ứng.

Sau khi có kết quả Colab, cần kiểm tra thứ tự lớp, checkpoint và số đo; cập nhật bộ nhận nhiều lớp, rồi chạy lại các ca bàn/ghế/dép không có prior map, ca box cũ và lỗi camera. Hiện `VisualObstacleLayer` vẫn lọc một lớp box; chỉ đổi đường dẫn checkpoint chưa đủ để tích hợp ba lớp. Phép chiếu mép dưới bbox còn phụ thuộc chân nhìn thấy và sàn phẳng, nên train detector không tự bảo đảm sửa được lỗi mapping hoặc tránh chân mảnh.
