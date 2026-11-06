"""Fixed camera controller. Ground truth is read ONLY by collect_dataset()."""
from dataclasses import asdict
import hashlib
import json
import math
import os
from pathlib import Path
import random
from .models import ROOT
from .vision import FloorProjection, YoloDetector


def projection(metadata):
    v=metadata['vision']
    return FloorProjection(v['camera_width'],v['camera_height'],v['camera_z_m'],v['horizontal_fov_rad'],
                           metadata['width_m']/2,metadata['height_m']/2)


def camera_bgr(camera):
    import numpy as np
    return np.frombuffer(camera.getImage(),dtype=np.uint8).reshape(camera.getHeight(),camera.getWidth(),4)[:,:,:3].copy()


def save_image(path,bgr):
    # OpenCV imwrite on Windows does not reliably accept Vietnamese paths.
    import cv2
    ok,encoded=cv2.imencode(path.suffix,bgr)
    if not ok:
        raise RuntimeError(f'Image encoding failed: {path.name}')
    path.write_bytes(encoded.tobytes())


def publish_live_frame(output, bgr, annotated, packet):
    """Atomic snapshots for a separate viewer; never feeds navigation."""
    for name, pixels in (('live-raw.jpg', bgr), ('live-yolo.jpg', annotated)):
        target=output/name
        temporary=output/(target.stem+'.tmp.jpg')
        save_image(temporary,pixels)
        os.replace(temporary,target)
    temporary=output/'live-camera.tmp.json'
    temporary.write_text(json.dumps(packet),encoding='utf-8')
    os.replace(temporary,output/'live-camera.json')


def collect_dataset(robot,camera,metadata,timestep):
    """Synthetic labels from box geometry for supervised training/evaluation only."""
    import cv2
    from .webots_world import solid_box
    output=Path(os.environ['ROBOT_VISION_DATASET'])
    total=int(os.environ.get('ROBOT_DATASET_COUNT','240'))
    if total<30:
        raise ValueError('Use at least 30 independently generated scenes')
    for split in ('train','val','test'):
        (output/'images'/split).mkdir(parents=True,exist_ok=True)
        (output/'labels'/split).mkdir(parents=True,exist_ok=True)
    root=robot.getRoot().getField('children')
    root.importMFNodeFromString(-1,'DEF DATA_OBJECTS Group { children [] }')
    objects=robot.getFromDef('DATA_OBJECTS').getField('children')
    vehicle=robot.getFromDef('NAV_ROBOT')
    floor_color=None
    for i in range(root.getCount()):
        node=root.getMFNode(i)
        name=node.getField('name')
        if name and name.getSFString()=='floor':
            floor_color=node.getField('children').getMFNode(0).getField('appearance').getSFNode().getField('baseColor')
    calibration=projection(metadata)
    manifest=[]
    for index in range(total):
        split='train' if index<int(total*2/3) else ('val' if index<int(total*5/6) else 'test')
        # Separate scene seeds; no adjacent frames of a scene cross splits.
        seed=2026110600+index
        rng=random.Random(seed)
        while objects.getCount():
            objects.removeMF(0)
        robot_x,robot_y=rng.uniform(.3,2.7),rng.uniform(.3,1.7)
        vehicle.getField('translation').setSFVec3f([robot_x,robot_y,.055])
        vehicle.getField('rotation').setSFRotation([0,0,1,rng.uniform(-math.pi,math.pi)])
        vehicle.resetPhysics()
        if floor_color:
            shade=rng.uniform(.62,.94)
            floor_color.setSFColor([shade,shade,min(1,shade+.03)])
        boxes=[]
        count=0 if rng.random()<.17 else rng.randint(1,3)
        attempts=0
        while len(boxes)<count and attempts<100:
            attempts+=1
            w,h=rng.uniform(.16,.46),rng.uniform(.16,.46)
            x,y=rng.uniform(.25,2.75-w),rng.uniform(.25,1.75-h)
            rect=(x,y,x+w,y+h)
            if x-.2<robot_x<x+w+.2 and y-.2<robot_y<y+h+.2:
                continue
            if any(not(rect[2]+.1<r[0] or r[2]+.1<rect[0] or rect[3]+.1<r[1] or r[3]+.1<rect[1]) for r,z in boxes):
                continue
            z=rng.uniform(.12,.35)
            color=' '.join(str(rng.uniform(.15,.9)) for _ in range(3))
            objects.importMFNodeFromString(-1,solid_box(f'TRAIN_BOX_{len(boxes)}',rect,z,color))
            boxes.append((rect,z))
        for _ in range(5):
            if robot.step(timestep)==-1:
                return
        image=camera_bgr(camera)
        image_path=output/'images'/split/f'{index:04d}.png'
        save_image(image_path,image)
        labels=[]
        for (x0,y0,x1,y1),z in boxes:
            points=[calibration.world_to_pixel(x,y,height) for x in (x0,x1) for y in (y0,y1) for height in (0,z)]
            u0=max(0,min(p[0] for p in points)); u1=min(camera.getWidth(),max(p[0] for p in points))
            v0=max(0,min(p[1] for p in points)); v1=min(camera.getHeight(),max(p[1] for p in points))
            labels.append(f'0 {(u0+u1)/2/camera.getWidth():.7f} {(v0+v1)/2/camera.getHeight():.7f} {(u1-u0)/camera.getWidth():.7f} {(v1-v0)/camera.getHeight():.7f}')
        (output/'labels'/split/f'{index:04d}.txt').write_text('\n'.join(labels)+'\n' if labels else '',encoding='utf-8')
        manifest.append({'id':index,'split':split,'seed':seed,'boxes':boxes,'sha256':hashlib.sha256(image_path.read_bytes()).hexdigest()})
        if index%40==0:
            print(f'Dataset {index}/{total}',flush=True)
    (output/'dataset.yaml').write_text(f'path: {json.dumps(str(output.resolve()).replace(chr(92),"/"))}\ntrain: images/train\nval: images/val\ntest: images/test\nnames:\n  0: box\n',encoding='utf-8')
    (output/'manifest.json').write_text(json.dumps({'source':'Webots RGB camera, procedural boxes; annotations use simulator geometry only during dataset generation',
        'camera':metadata,'scenes':manifest},indent=2),encoding='utf-8')
    print(f'Collected {total} independently rendered scenes',flush=True)
    robot.simulationQuit(0)


def _run(robot):
    metadata=json.loads(robot.getCustomData())
    v=metadata['vision']
    timestep=round(robot.getBasicTimeStep())
    camera=robot.getDevice('overhead')
    camera.enable(timestep)
    if os.environ.get('ROBOT_VISION_DATASET'):
        collect_dataset(robot,camera,metadata,timestep)
        return
    import torch
    torch.set_num_threads(4)
    detector=YoloDetector(ROOT/v['model'],v)
    emitter=robot.getDevice('vision_emitter')
    output=Path(os.environ.get('ROBOT_OUTPUT',str(ROOT/'experiments/runs/yolo')))
    output.mkdir(parents=True,exist_ok=True)
    (output/'camera-calibration.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    index=0
    camera_frames=0
    if os.environ.get('ROBOT_RECORD')=='1':
        (output/'camera-frames').mkdir(parents=True,exist_ok=True)
    with (output/'detections.jsonl').open('w',encoding='utf-8') as log:
        while robot.step(timestep)!=-1:
            if robot.getTime()>=float(os.environ.get('ROBOT_VISION_DROP_AFTER_S','inf')):
                continue  # Controlled fault-injection test, never a fallback detector.
            if index%v['sample_steps']==0:
                bgr=camera_bgr(camera)
                detections,latency,result=detector.detect(bgr)
                packet={'timestamp':robot.getTime(),'detections':[asdict(d) for d in detections],'latency_ms':latency}
                emitter.send(json.dumps(packet).encode('utf-8'))
                log.write(json.dumps(packet)+'\n'); log.flush()
                if os.environ.get('ROBOT_LIVE')=='1':
                    try:
                        publish_live_frame(output,bgr,result.plot(),packet)
                    except PermissionError:
                        # Windows may briefly hold a snapshot open in the viewer.
                        # Skip this display update; perception/navigation must continue.
                        pass
                if os.environ.get('ROBOT_RECORD')=='1':
                    save_image(output/'camera-frames'/f'frame-{camera_frames:05d}.jpg',result.plot())
                    camera_frames+=1
                if detections:
                    import cv2
                    save_image(output/'latest-detection.jpg',result.plot())
                    if not (output/'first-detection.jpg').exists():
                        save_image(output/'first-detection.jpg',result.plot())
            index+=1


def run():
    from controller import Supervisor
    import traceback
    robot=Supervisor()
    try:
        _run(robot)
    except Exception:
        output=Path(os.environ.get('ROBOT_VISION_DATASET',os.environ.get('ROBOT_OUTPUT',str(ROOT/'experiments/runs/yolo'))))
        output.mkdir(parents=True,exist_ok=True)
        (output/'vision-error.txt').write_text(traceback.format_exc(),encoding='utf-8')
        robot.simulationQuit(1)
        raise
