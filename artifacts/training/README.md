# Bộ train Colab đã đóng gói

Mở [notebook Colab](https://colab.research.google.com/github/hung230206/indoor-autonomous-robot/blob/main/notebooks/train_robot_objects.ipynb), chọn GPU rồi chạy các ô. Notebook tự tải `robot_objects_v1_dataset.zip` tại đây và kiểm tra SHA-256. File ZIP là dữ liệu tổng hợp đã gán nhãn, không chứa model đã train.

1.200 ảnh, ba lớp `box`, `furniture_leg`, `slipper`. Xem [`package.json`](package.json) và [hướng dẫn đầy đủ](../../docs/colab-training.md). Giữ nguyên ZIP đã công bố; đổi dữ liệu cần phiên bản/hash mới.
