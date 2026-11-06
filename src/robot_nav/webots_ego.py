"""Onboard camera runtime. Recognition ground truth is ONLY used in collect()."""
from dataclasses import asdict
import hashlib
import json
import math
import os
from pathlib import Path
import random
from .models import ROOT
from .onboard import ego_config, OnboardProjection
from .vision import YoloDetector, VisualObstacleLayer
from .webots_vision import camera_bgr, save_image, publish_live_frame


class EgoCamera:
    def __init__(self,robot,grid,output):
        import torch
        torch.set_num_threads(4)
        self.robot,self.output=robot,output
        self.config=ego_config()
        self.camera=robot.getDevice('front_camera')
        self.camera.enable(round(robot.getBasicTimeStep()))
        # Recognition is never enabled for inference or navigation.
        self.detector=YoloDetector(ROOT/self.config['model'],self.config)
        self.projection=OnboardProjection(self.config)
        self.layer=VisualObstacleLayer(grid,self.projection,self.config)
        self.index=0
        self.packets=0
        self.output.mkdir(parents=True,exist_ok=True)
        self.log=(output/'detections.jsonl').open('w',encoding='utf-8')
        (output/'camera-calibration.json').write_text(json.dumps({'mode':'onboard_rgb','pose_source':'encoder_imu_odometry',
            'weights_sha256':hashlib.sha256((ROOT/self.config['model']).read_bytes()).hexdigest(),**self.config},indent=2),encoding='utf-8')

    def update(self,pose,now):
        if self.index%self.config['sample_steps']==0 and now<float(os.environ.get('ROBOT_EGO_DROP_AFTER_S','inf')):
            bgr=camera_bgr(self.camera)
            detections,latency,result=self.detector.detect(bgr)
            self.projection.pose=pose
            self.layer.update(detections,now,now)
            self.packets+=1
            packet={'timestamp':now,'detections':[asdict(d) for d in detections],
                    'latency_ms':latency,'mode':'onboard_rgb','pose_source':'encoder_imu_odometry',
                    'capture_pose':asdict(pose),'mapped_rects':self.layer.accepted_rects}
            self.log.write(json.dumps(packet)+'\n'); self.log.flush()
            annotated=result.plot()
            if os.environ.get('ROBOT_LIVE')=='1':
                try:
                    publish_live_frame(self.output,bgr,annotated,packet)
                except PermissionError:
                    pass
            if os.environ.get('ROBOT_RECORD')=='1':
                target=self.output/'camera-frames'; target.mkdir(exist_ok=True)
                save_image(target/f'frame-{self.packets-1:05d}.jpg',annotated)
            if detections:
                save_image(self.output/'latest-detection.jpg',annotated)
                if not (self.output/'first-detection.jpg').exists():
                    save_image(self.output/'first-detection.jpg',annotated)
        self.index+=1


def collect(robot):
    """Render independent ego scenes, labels from visible GT segmentation masks."""
    import numpy as np
    from .webots_world import solid_box
    camera=robot.getDevice('front_camera')
    dt=round(robot.getBasicTimeStep())
    camera.enable(dt); camera.recognitionEnable(dt); camera.enableRecognitionSegmentation()
    output=Path(os.environ['ROBOT_EGO_DATASET'])
    total=int(os.environ.get('ROBOT_DATASET_COUNT','360'))
    for split in ('train','val','test'):
        (output/'images'/split).mkdir(parents=True,exist_ok=True)
        (output/'labels'/split).mkdir(parents=True,exist_ok=True)
    root=robot.getRoot().getField('children')
    root.importMFNodeFromString(-1,'DEF EGO_TRAIN_OBJECTS Group { children [] }')
    objects=robot.getFromDef('EGO_TRAIN_OBJECTS').getField('children')
    vehicle=robot.getSelf()
    manifest=[]
    for index in range(total):
        rng=random.Random(2026110700+index)
        split='train' if index<int(total*2/3) else ('val' if index<int(total*5/6) else 'test')
        while objects.getCount(): objects.removeMF(0)
        # Scene pose varies independently; no adjacent frames across splits.
        x,y=rng.uniform(.25,2.75),rng.uniform(.25,1.75)
        yaw=rng.uniform(-math.pi,math.pi)
        vehicle.getField('translation').setSFVec3f([x,y,.055])
        vehicle.getField('rotation').setSFRotation([0,0,1,yaw])
        vehicle.resetPhysics()
        colors=[]; boxes=[]
        for k in range(0 if rng.random()<.15 else rng.randint(1,5)):
            distance=rng.uniform(.45,2.5); bearing=yaw+rng.uniform(-.65,.65)
            cx,cy=x+distance*math.cos(bearing),y+distance*math.sin(bearing)
            w,h=rng.uniform(.16,.40),rng.uniform(.16,.4)
            rect=[cx-w/2,cy-h/2,cx+w/2,cy+h/2]
            if not (.12<rect[0]<rect[2]<2.88 and .12<rect[1]<rect[3]<1.88): continue
            if any(not(rect[2]+.05<r[0] or r[2]+.05<rect[0] or rect[3]+.05<r[1] or r[3]+.05<rect[1]) for r in boxes): continue
            color=(40+35*k,70+27*k,210-25*k)
            appearance=' '.join(str(rng.uniform(.15,.95)) for _ in range(3))
            node=solid_box(f'EGO_BOX_{k}',rect,rng.uniform(.12,.32),appearance)
            node=node.replace('Solid {','Solid { recognitionColors [ '+' '.join(str(a/255) for a in color)+' ]',1)
            objects.importMFNodeFromString(-1,node)
            colors.append(color); boxes.append(rect)
        for _ in range(5):
            if robot.step(dt)==-1: return
        bgr=camera_bgr(camera)
        segment=np.frombuffer(camera.getRecognitionSegmentationImage(),dtype=np.uint8).reshape(480,640,4)[:,:,:3][:,:,::-1]
        labels=[]; visible=[]
        for color in colors:
            mask=np.all(np.abs(segment.astype(int)-color)<=1,axis=2)
            ys,xs=np.where(mask)
            if len(xs)<40: continue
            u0,u1=int(xs.min()),int(xs.max())+1; v0,v1=int(ys.min()),int(ys.max())+1
            if u1-u0<5 or v1-v0<5: continue
            labels.append(f'0 {(u0+u1)/1280:.7f} {(v0+v1)/960:.7f} {(u1-u0)/640:.7f} {(v1-v0)/480:.7f}')
            visible.append([u0,v0,u1,v1])
        image=output/'images'/split/f'{index:04d}.png'
        save_image(image,bgr)
        (output/'labels'/split/f'{index:04d}.txt').write_text('\n'.join(labels)+('\n' if labels else ''),encoding='utf-8')
        manifest.append({'id':index,'seed':2026110700+index,'split':split,'pose':[x,y,yaw],
            'boxes':boxes,'visible_boxes_xyxy':visible,'sha256':hashlib.sha256(image.read_bytes()).hexdigest()})
    (output/'dataset.yaml').write_text('path: '+json.dumps(str(output.resolve()).replace('\\','/'))+'\ntrain: images/train\nval: images/val\ntest: images/test\nnames:\n  0: box\n',encoding='utf-8')
    (output/'manifest.json').write_text(json.dumps({'source':'Onboard Webots RGB, labels from visible GT segmentation ONLY during dataset generation','camera':ego_config(),'scenes':manifest},indent=2),encoding='utf-8')
    robot.simulationQuit(0)
