"""Preserve actual ego experiment outputs separately from legacy evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from robot_nav.recording import write_batch


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--runs',type=Path,default=ROOT/'experiments/runs/ego_validation')
    parser.add_argument('--dataset',type=Path,default=ROOT/'experiments/runs/ego_dataset_v2')
    parser.add_argument('--output',type=Path,default=ROOT/'experiments/evidence/ego_v1')
    args=parser.parse_args()
    if args.output.exists():
        raise SystemExit('Evidence already exists; select a new output directory')
    summaries=[]
    for name in ('open','yolo_far_box','yolo_many_boxes','yolo_camera_loss'):
        source=args.runs/name
        summary=json.loads((source/'summary.json').read_text(encoding='utf-8'))
        assert summary['passed'],(name,summary)
        summaries.append(summary)
    args.output.mkdir(parents=True)
    for summary in summaries:
        shutil.copytree(args.runs/summary['scenario'],args.output/'navigation'/summary['scenario'],
                        ignore=shutil.ignore_patterns('frames','camera-frames','*.tmp.*'))
    write_batch(args.output/'navigation',summaries)
    for experiment in ('ego_preview','ego_preview_calibrated','ego_pose_diagnostic'):
        source=ROOT/'experiments/runs'/experiment/'yolo_many_boxes'
        if source.exists():
            target=args.output/'development_failures'/experiment
            target.mkdir(parents=True)
            for filename in ('summary.json','events.json','camera-calibration.json'):
                if (source/filename).exists(): shutil.copy2(source/filename,target/filename)
    for source,name in ((args.dataset/'manifest.json','dataset-manifest.json'),
        (ROOT/'experiments/runs/ego_baseline_regression/results.csv','baseline-regression.csv'),
        (ROOT/'experiments/runs/ego_tests.txt','tests.txt')):
        shutil.copy2(source,args.output/name)
    manifest=json.loads((args.dataset/'manifest.json').read_text(encoding='utf-8'))
    assert len({s['sha256'] for s in manifest['scenes']})==len(manifest['scenes'])
    selected=[s for s in manifest['scenes'] if s['split']=='test' and s['visible_boxes_xyxy']][:3]
    samples=args.output/'test-samples'; samples.mkdir()
    for scene in selected:
        stem=f"{scene['id']:04d}"
        shutil.copy2(args.dataset/'images/test'/(stem+'.png'),samples/(stem+'-rgb.png'))
        shutil.copy2(args.dataset/'labels/test'/(stem+'.txt'),samples/(stem+'-labels.txt'))
    weights=ROOT/'models/yolo_ego/best.pt'
    weight_hash=hashlib.sha256(weights.read_bytes()).hexdigest()
    for summary in summaries:
        calibration=json.loads((args.runs/summary['scenario']/'camera-calibration.json').read_text(encoding='utf-8'))
        assert calibration['weights_sha256']==weight_hash,'Run used a different checkpoint'
    (weights.parent/'SHA256.txt').write_text(weight_hash+'  best.pt\n',encoding='utf-8')
    report={'camera':'onboard_front_rgb','pose':'encoder + IMU odometry, known initial pose; no Supervisor pose correction',
        'weights_sha256':weight_hash,'dataset':{split:{'images':sum(s['split']==split for s in manifest['scenes']),
        'boxes':sum(len(s['visible_boxes_xyxy']) for s in manifest['scenes'] if s['split']==split)} for split in ('train','val','test')},
        'metrics':json.loads((weights.parent/'metrics.json').read_text(encoding='utf-8')),
        'navigation':summaries,'limits':'Synthetic images only; monocular ground-contact assumptions; simulated encoders absent from original hardware BOM; not real-time or real-robot validation'}
    (args.output/'report-data.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    hashes={p.relative_to(args.output).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(args.output.rglob('*')) if p.is_file()}
    (args.output/'sha256.json').write_text(json.dumps(hashes,indent=2)+'\n',encoding='utf-8')
    print('Saved',len(summaries),'actual ego runs to',args.output)


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
