"""Portable Ultralytics training/evaluation, bundled for Colab and local QA.

No Webots/controller dependency. Never installs a candidate into the live robot.
"""
import hashlib
import json
from pathlib import Path
import platform
import shutil
import zipfile

CLASSES=['box','furniture_leg','slipper']


def train_model(dataset,project,name,epochs=60,imgsz=640,batch=16,device='0',base='yolo11n.pt',freeze=0):
    import torch
    import ultralytics
    from ultralytics import YOLO
    dataset=Path(dataset);project=Path(project)
    if (project/name).exists():raise FileExistsError('Choose a new run name; do not overwrite an earlier run')
    if device=='cpu':torch.set_num_threads(4)
    manifest=json.loads((dataset/'manifest.json').read_text(encoding='utf-8'))
    assert manifest['classes']==CLASSES,'Class order mismatch'
    model=YOLO(str(base))
    model.train(data=str(dataset/'dataset.yaml'),epochs=epochs,imgsz=imgsz,batch=batch,
        device=device,workers=0 if device=='cpu' else 2,project=str(project),name=name,
        exist_ok=False,seed=42,deterministic=True,freeze=freeze,patience=15,plots=True,
        degrees=0,translate=.05,scale=.20,fliplr=.5,flipud=0,mosaic=.30,close_mosaic=10,
        hsv_h=.015,hsv_s=.3,hsv_v=.2,cache=False,save=True,save_period=10)
    run=Path(model.trainer.save_dir)
    report={'classes':CLASSES,'dataset_manifest_sha256':hashlib.sha256((dataset/'manifest.json').read_bytes()).hexdigest(),
            'epochs_requested':epochs,'image_size':imgsz,'batch':batch,'device':str(device),'base_weights':str(base),
            'python':platform.python_version(),'torch':torch.__version__,'ultralytics':ultralytics.__version__,
            'cuda':torch.version.cuda,'gpu':torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
            'checkpoint_selection':'best validation fitness; test set not used for checkpoint selection',
            'scope':'Synthetic onboard RGB; not real-world accuracy or navigation success'}
    (run/'training-provenance.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return run


def evaluate_model(dataset,run,device='0',imgsz=640,batch=16,split='test'):
    from ultralytics import YOLO
    dataset,run=Path(dataset),Path(run)
    if split not in ('val','test'):raise ValueError('Evaluation must use val or test')
    report_path=run/(split+'-metrics.json')
    if report_path.exists():raise FileExistsError('Evaluation already recorded; retain its result')
    weights=run/'weights/best.pt'
    model=YOLO(str(weights))
    assert list(model.names.values())==CLASSES,'Checkpoint classes do not match this dataset'
    metrics=model.val(data=str(dataset/'dataset.yaml'),split=split,imgsz=imgsz,batch=batch,
                      device=device,workers=0 if device=='cpu' else 2,
                      project=str(run),name=split+'_evaluation',plots=True)
    per_class=[]
    for i,cid in enumerate(metrics.box.ap_class_index):
        per_class.append({'class_id':int(cid),'name':CLASSES[int(cid)],
            'precision':float(metrics.box.p[i]),'recall':float(metrics.box.r[i]),
            'map50':float(metrics.box.ap50[i]),'map50_95':float(metrics.box.ap[i])})
    report={'split':split,'classes':CLASSES,'weights_sha256':hashlib.sha256(weights.read_bytes()).hexdigest(),
            'dataset_manifest_sha256':hashlib.sha256((dataset/'manifest.json').read_bytes()).hexdigest(),
            'overall':{str(k):float(v) for k,v in metrics.results_dict.items()},'per_class':per_class,
            'scope':'Synthetic detector evaluation only; not comparable to the older one-class test set; no robot success claim'}
    report_path.write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


def export_results(run,destination):
    run,destination=Path(run),Path(destination)
    if destination.exists():raise FileExistsError(destination)
    with zipfile.ZipFile(destination,'x',zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(run.rglob('*')):
            if not path.is_file():continue
            if path.suffix=='.pt' and path.name not in ('best.pt','last.pt'):continue
            if path.suffix not in ('.pt','.json','.yaml','.csv','.png','.jpg','.txt'):continue
            archive.write(path,path.relative_to(run).as_posix())
    return destination
