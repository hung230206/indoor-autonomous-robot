"""Retain measured ML/navigation results and figures for the stage-1 report."""
import csv
import hashlib
import json
from pathlib import Path
import shutil
import statistics
import sys
import os

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
os.environ.setdefault('MPLBACKEND','Agg')
os.environ.setdefault('YOLO_CONFIG_DIR',str(ROOT/'.cache/ultralytics'))


def load(path): return json.loads(path.read_text(encoding='utf-8'))


def first_stop(directory):
    return next((e['time_s'] for e in load(directory/'events.json') if e['state']=='OBSTACLE_STOP'),None)


def main():
    import matplotlib.pyplot as plt
    import cv2
    import numpy as np
    import torch,ultralytics
    from robot_nav.vision import YoloDetector
    from robot_nav.webots_vision import save_image
    evidence=ROOT/'experiments/evidence/yolo_v1'
    dataset=ROOT/'experiments/runs/yolo_dataset'
    manifest=load(dataset/'manifest.json')
    scenes=manifest['scenes']
    assert len({s['sha256'] for s in scenes})==len(scenes),'Duplicate rendered images'
    runs=[]
    for name in ('yolo_far_box','replanning','open','yolo_camera_loss'):
        directory=evidence/'navigation'/name
        result=load(directory/'summary.json')
        assert result['passed'],result
        result['first_obstacle_stop_s']=first_stop(directory)
        assert result['range_mapping_enabled'] is False
        runs.append(result)
    fault_events=load(evidence/'navigation/yolo_camera_loss/events.json')
    assert fault_events[-1]['reason']=='vision_missing_or_stale'
    reference=evidence/'range_reference/yolo_far_box'
    baseline=load(reference/'summary.json')
    assert baseline['passed']
    baseline['first_obstacle_stop_s']=first_stop(reference)
    rows=list(csv.DictReader((ROOT/'experiments/runs/vision_baseline_regression/results.csv').open()))
    assert len(rows)==10 and all(r['passed']=='True' for r in rows)
    shutil.copy2(ROOT/'experiments/runs/vision_baseline_regression/results.csv',evidence/'baseline-regression.csv')
    shutil.copy2(dataset/'manifest.json',evidence/'dataset-manifest.json')
    metrics=load(ROOT/'models/yolo_box/metrics.json')
    timing=[json.loads(line)['latency_ms'] for line in (evidence/'navigation/yolo_far_box/detections.jsonl').read_text().splitlines()]
    report={'date':'2026-11-06','dataset':{'source':'Native Webots RGB camera with procedural 3D boxes',
        'images':len(scenes),'unique_sha256':len({s['sha256'] for s in scenes}),
        'splits':{k:{'images':sum(s['split']==k for s in scenes),'instances':sum(len(s['boxes']) for s in scenes if s['split']==k)} for k in ('train','val','test')}},
        'model':metrics,'weights_sha256':hashlib.sha256((ROOT/'models/yolo_box/best.pt').read_bytes()).hexdigest(),
        'navigation':runs,'range_reference':baseline,'baseline_regression_passed':10,
        'inference_wall_time_ms':{'first_call':timing[0],'median_after_first':statistics.median(timing[1:]),
            'max_including_warmup':max(timing),'calls':len(timing)},
        'environment':{'python':sys.version.split()[0],'torch':torch.__version__,'ultralytics':ultralytics.__version__,
                       'opencv':cv2.__version__,'training_device':'CPU'},
        'limitations':['Synthetic fixed overhead camera only','One learned class: box','Ideal Supervisor robot pose',
                       'Range sensors retained for emergency stop','Synchronous simulation is not a physical real-time safety proof',
                       'No real-camera training/validation and no ESP32 firmware']}
    (evidence/'report-data.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    detector=YoloDetector(ROOT/'models/yolo_box/best.pt')
    samples=evidence/'test-samples'; samples.mkdir(exist_ok=True)
    selected=[s for s in scenes if s['split']=='test' and s['boxes']][:3]
    for scene in selected:
        name=f"{scene['id']:04d}"
        image=dataset/'images/test'/(name+'.png')
        bgr=cv2.imdecode(np.fromfile(image,dtype=np.uint8),cv2.IMREAD_COLOR)
        det,latency,result=detector.detect(bgr)
        shutil.copy2(image,samples/(name+'-rgb.png'))
        shutil.copy2(dataset/'labels/test'/(name+'.txt'),samples/(name+'-labels.txt'))
        save_image(samples/(name+'-prediction.jpg'),result.plot())
    with (ROOT/'models/yolo_box/training-results.csv').open() as stream:
        rows=list(csv.DictReader(stream))
    epochs=[float(r['epoch']) for r in rows]
    fig,axes=plt.subplots(1,2,figsize=(10,3.5),dpi=160)
    for key,label in [('metrics/mAP50(B)','Validation mAP50'),('metrics/mAP50-95(B)','Validation mAP50-95')]:
        axes[0].plot(epochs,[float(r[key]) for r in rows],label=label,linewidth=2)
    for key,label in [('train/box_loss','Train box loss'),('train/cls_loss','Train class loss')]:
        axes[1].plot(epochs,[float(r[key]) for r in rows],label=label,linewidth=2)
    for ax in axes:
        ax.set_xlabel('Epoch'); ax.grid(alpha=.2); ax.legend(fontsize=8)
    axes[0].set_ylim(0,1.05); axes[0].set_ylabel('mAP'); axes[1].set_ylabel('Loss')
    fig.tight_layout(); fig.savefig(evidence/'training-curves.png'); plt.close(fig)
    labels=[('Camera RGB','640 × 480'),('YOLO11n','nhãn box'),('Ảnh → mét','hiệu chuẩn'),('Grid + inflate','vật cản'),('A*','tìm đường'),('FSM + lái','waypoint'),('Hai motor','Webots')]
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1510" height="410" viewBox="0 0 1510 410">',
         '<rect width="1510" height="410" fill="#f8fafc"/><style>text{font-family:Arial,sans-serif;fill:#203047}</style>',
         '<defs><marker id="a" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0L8 4L0 8" fill="#2860a7"/></marker></defs>',
         '<text x="35" y="55" font-size="36" font-weight="bold">Kiến trúc điều hướng có nhận diện thị giác</text>']
    for i,(title,sub) in enumerate(labels):
        x=25+i*212
        svg += [f'<rect x="{x}" y="110" width="185" height="130" rx="12" fill="{("#e7f4ee" if i in (1,3) else "#edf3ff")}" stroke="#8da7c4"/>',
                f'<text x="{x+92}" y="163" font-size="23" text-anchor="middle" font-weight="bold">{title.replace("&","&amp;")}</text>',
                f'<text x="{x+92}" y="204" font-size="23" text-anchor="middle">{sub}</text>']
        if i<6: svg.append(f'<path d="M{x+185} 175H{x+210}" stroke="#2860a7" stroke-width="3" marker-end="url(#a)"/>')
    svg += ['<text x="35" y="306" font-size="25">Pose xe: Supervisor lý tưởng. Hiệu chuẩn camera: hình học cố định đã biết.</text>',
            '<text x="35" y="355" font-size="25">Trong chế độ YOLO, cảm biến khoảng cách chỉ tham gia dừng nguy hiểm, không dựng bản đồ.</text>','</svg>']
    (evidence/'architecture.svg').write_text('\n'.join(svg),encoding='utf-8')
    (ROOT/'models/yolo_box/SHA256.txt').write_text(report['weights_sha256']+'  best.pt\n',encoding='utf-8')
    print(json.dumps({'dataset':report['dataset'],'metrics':metrics['metrics'],'runs':len(runs),
        'first_stop_yolo_s':runs[0]['first_obstacle_stop_s'],'first_stop_range_s':baseline['first_obstacle_stop_s']},indent=2))


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
