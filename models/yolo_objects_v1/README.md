# YOLO11n đa lớp từ Colab

Nhập từ `objects_v1_20261112_081430_results.zip` do người dùng cung cấp ngày 12/11/2026. Trọng số giữ nguyên từ Colab, không train lại hoặc chỉnh theo test tại máy.

- Ultralytics 8.4.202, PyTorch 2.14.1+cu130, Tesla T4, 60 epoch, ảnh 640, batch 16.
- Bộ 1.200 cảnh RGB Webots trên xe: 840 train / 180 val / 180 test.
- Lớp: `0 box`, `1 furniture_leg`, `2 slipper`.
- SHA trọng số, ZIP nguồn và dataset: `import.json`; môi trường: `training-provenance.json`.
- `metrics.json` là đánh giá 180 ảnh test từ Colab, không phải kết quả điều hướng.

| Lớp | Precision | Recall | mAP50 | mAP50–95 |
|---|---:|---:|---:|---:|
| box | 99,11% | 98,25% | 99,23% | 98,12% |
| furniture_leg | 98,13% | 96,93% | 99,36% | 95,24% |
| slipper | 99,03% | 97,89% | 99,16% | 96,14% |
| Trung bình | 98,76% | 97,69% | 99,25% | 96,50% |

Các tỉ lệ là số đo detector trên ảnh tổng hợp cùng họ render. Không gọi mAP là accuracy, không suy thành xác suất tránh cản hoặc số đo trên xe thật. Chọn checkpoint bằng validation, không chọn theo test. Model box cũ tại `models/yolo_ego/` được giữ nguyên để tái lập kết quả cũ.
