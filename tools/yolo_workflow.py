"""Collect native Webots RGB data, fine-tune, and evaluate held-out scenes."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT/'tools'))
os.environ.setdefault('YOLO_CONFIG_DIR',str(ROOT/'.cache/ultralytics'))
os.environ.setdefault('MPLBACKEND','Agg')
from robot_nav.models import Config
from robot_nav.simulation import get_scenario
from robot_nav.webots_world import generate_world
from run_webots import locate_webots


def collect(args):
    from robot_nav.vision import configure_camera_runtime
    configure_camera_runtime()
    output=args.output.resolve()
    if (output/'manifest.json').exists():
        raise SystemExit('Dataset exists; choose a new output directory to preserve its split/provenance')
    output.mkdir(parents=True,exist_ok=True)
    world=ROOT/'worlds/yolo_dataset.wbt'
    generate_world(Config.load(),get_scenario('open'),world,vision=True)
    env=os.environ.copy()
    env.update({'ROBOT_VISION_DATASET':str(output),'ROBOT_DATASET_COUNT':str(args.count),
                'PYTHONIOENCODING':'utf-8','PATH':str(Path(sys.executable).parent)+os.pathsep+env['PATH']})
    with (output/'collection.log').open('w',encoding='utf-8') as log:
        process=subprocess.Popen([str(locate_webots()),'--batch','--minimize','--mode=fast','--stdout','--stderr',str(world)],
            cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        try:
            code=process.wait(timeout=240)
        except subprocess.TimeoutExpired:
            if os.name=='nt': subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True)
            else: process.kill()
            raise RuntimeError('Dataset collection timed out; inspect collection.log')
    if code or not (output/'manifest.json').exists():
        raise RuntimeError('Dataset collection failed; inspect collection.log')
    print('Dataset:',output)


def train(args):
    import torch
    from ultralytics import YOLO
    torch.set_num_threads(4)
    output=args.output.resolve()
    output.mkdir(parents=True,exist_ok=True)
    base=ROOT/'models/downloads/yolo11n.pt'
    base.parent.mkdir(parents=True,exist_ok=True)
    if not base.exists():
        downloaded=YOLO('yolo11n.pt')
        shutil.move('yolo11n.pt',base)
    model=YOLO(str(base))
    result=model.train(data=str(args.dataset.resolve()/'dataset.yaml'),epochs=args.epochs,imgsz=320,batch=8,
        device='cpu',workers=0,project=str(ROOT/'experiments/runs/yolo_training'),name=args.name,
        exist_ok=False,seed=42,deterministic=True,freeze=10,patience=15,plots=True,
        degrees=10,translate=.05,scale=.15,fliplr=.5,flipud=.5,mosaic=.3,close_mosaic=5,
        hsv_h=.015,hsv_s=.3,hsv_v=.2,cache=True)
    best=Path(model.trainer.best)
    shutil.copy2(best,output/'best.pt')
    evaluated=YOLO(str(output/'best.pt')).val(data=str(args.dataset.resolve()/'dataset.yaml'),split='test',
        imgsz=320,batch=8,device='cpu',workers=0,project=str(ROOT/'experiments/runs/yolo_eval'),name=args.name,plots=True)
    report={'model':'YOLO11n, COCO initialized, fine-tuned on procedural Webots box images',
            'dataset':str(args.dataset.resolve()),'epochs_requested':args.epochs,
            'training_dir':str(model.trainer.save_dir),'evaluation_split':'test',
            'metrics':{str(k):float(v) for k,v in evaluated.results_dict.items()},
            'scope':'Synthetic fixed-camera box detection only; not validated on real images or arbitrary obstacles'}
    (output/'metrics.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    shutil.copy2(model.trainer.save_dir/'args.yaml',output/'training-args.yaml')
    shutil.copy2(model.trainer.save_dir/'results.csv',output/'training-results.csv')
    print(json.dumps(report,indent=2))


def main():
    parser=argparse.ArgumentParser()
    sub=parser.add_subparsers(dest='action',required=True)
    c=sub.add_parser('collect'); c.add_argument('--count',type=int,default=240)
    c.add_argument('--output',type=Path,default=ROOT/'experiments/runs/yolo_dataset')
    t=sub.add_parser('train'); t.add_argument('--epochs',type=int,default=30)
    t.add_argument('--dataset',type=Path,default=ROOT/'experiments/runs/yolo_dataset')
    t.add_argument('--output',type=Path,default=ROOT/'models/yolo_box')
    t.add_argument('--name',default='box_v1')
    args=parser.parse_args()
    (collect if args.action=='collect' else train)(args)


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
