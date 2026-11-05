# YOLO11n box detector for the Webots prototype

`best.pt` is a YOLO11n checkpoint initialized from Ultralytics COCO weights and fine-tuned for **one class, `box`** on 240 procedural Webots RGB images (160 train / 40 val / 40 test). Training used 30 epochs on CPU, input size 320, batch 8, freeze=10 and seed 42. Exact arguments and per-epoch results accompany this model.

Held-out synthetic test: precision 0.9991009, recall 1.0, mAP50 0.9950, mAP50-95 0.9497050; 40 images with 70 annotated boxes. Metrics are from Ultralytics test evaluation, not real-world safety or navigation success rates.

Use only as a prototype for the fixed overhead Webots camera. The model has not been tested on real phone imagery, arbitrary objects, people, chairs, severe occlusion or a moving camera. The runtime confidence threshold is 0.5. Robot localization still uses an ideal Supervisor pose in this prototype.

`SHA256.txt` identifies the checkpoint. Dataset provenance: `experiments/evidence/yolo_v1/dataset-manifest.json`; generator and reproducible workflow: `tools/yolo_workflow.py`, `src/robot_nav/webots_vision.py`. Inference only reads RGB images; simulator object geometry is used to generate training labels and to evaluate collisions, not as a substitute detector.

Upstream model/software: [Ultralytics YOLO11](https://docs.ultralytics.com/models/yolo11/) and its [license](https://github.com/ultralytics/ultralytics/blob/main/LICENSE). This project fine-tunes and integrates the model; it does not introduce a new YOLO architecture.
