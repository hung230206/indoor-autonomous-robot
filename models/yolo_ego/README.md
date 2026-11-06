# YOLO11n for the onboard RGB camera

This is the **front camera attached to the robot** model, separate from the legacy overhead `models/yolo_box/` checkpoint. It is COCO-initialized YOLO11n fine-tuned for one class, `box`, for 30 CPU epochs, input size 320, batch 8 and seed 42. The camera is 640×480, 0.32 m above the floor, pitched down 0.30 rad. It moves with the robot.

The procedural dataset contains 360 independent rendered scenes: 240 train images with 127 visible boxes, 60 validation images with 38 boxes, and 60 test images with 37 boxes. Visible segmentation masks generate labels **only during dataset creation**. Recognition ground truth is not enabled in the inference/navigation runtime. Test images include 28 positive scenes and 32 empty scenes; all 360 image SHA-256 values are unique.

Ultralytics held-out synthetic test metrics: precision 0.9983438, recall 0.9729730, mAP50 0.9750 and mAP50–95 0.9492712. These detection metrics do not describe navigation success or real-world safety. Runtime confidence is separately configured at 0.5.

The inference input is RGB/BGR camera pixels, not simulator object locations. Ground-contact projection is calibrated geometry with assumptions, not learned depth. Runtime uses encoder + ideal simulated IMU odometry, known initial pose, range fusion, A* and FSM. Real hardware currently lacks the encoder/IMU and camera streaming implementation needed for this path. No real images or real robot were evaluated.

See `training-args.yaml`, `training-results.csv`, `metrics.json`, `SHA256.txt`, `experiments/evidence/ego_v1/` and `docs/ego-vision.md`. The old overhead model's metrics must not be used for this model.

Upstream architecture/weights: [Ultralytics YOLO11](https://docs.ultralytics.com/models/yolo11/) under the [upstream license](https://github.com/ultralytics/ultralytics/blob/main/LICENSE). This project fine-tunes and integrates YOLO; it does not propose a new YOLO architecture.
