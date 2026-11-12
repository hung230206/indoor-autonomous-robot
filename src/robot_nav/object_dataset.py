"""Synthetic onboard-camera training data; never imported by perception runtime.

Per-part recognition colors generate visible-pixel labels only during collection.
Furniture seats/tops/backrests occlude legs but are not leg annotations.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import random

from .scene_objects import parts, sole_points

CLASSES=('box','furniture_leg','slipper')
BASE_SEEDS={'train':202611120000,'val':202611130000,'test':202611140000}


def split_for(index, count):
    if not 0<=index<count or count<20:
        raise ValueError('Dataset requires count >= 20 and an in-range index')
    return 'train' if index<int(count*.7) else ('val' if index<int(count*.85) else 'test')


def token_color(token):
    if not 0<=token<24:
        raise ValueError('Too many annotation instances')
    return (32+token*7,64+token*5,210-token*6)


def _mesh(points, thickness, scale):
    vertices=[(x*scale[0],y*scale[1],z*scale[2]) for z in (0,thickness) for x,y in points]
    n=len(points)
    faces=[list(reversed(range(n))),list(range(n,2*n))]
    faces += [[i,(i+1)%n,(i+1)%n+n,i+n] for i in range(n)]
    return ('IndexedFaceSet { coord Coordinate { point [ '+', '.join(' '.join(map(str,v)) for v in vertices)+
            ' ] } coordIndex [ '+', '.join(' '.join(map(str,f))+' -1' for f in faces)+' ] }')


def training_object(name, obj, token_start):
    """Same component topology as runtime props, with varied sizes/appearance."""
    children=[]; instances=[]
    scale=obj['scale']; palette=obj['colors']
    if obj['kind']=='box':
        components=[((0,0,.14),(.28,.28,.28),palette[0])]
    else:
        components=parts(obj)
    for part_id,(center,size,_) in enumerate(components):
        is_leg=obj['kind'] in ('table','chair') and part_id<4
        class_id=0 if obj['kind']=='box' else (1 if is_leg else None)
        # A slipper is annotated as one parent, not one detection per strap.
        color=palette[0 if is_leg or obj['kind']=='box' else 1]
        xyz=' '.join(str(v*s) for v,s in zip(center,scale))
        dims=[v*s for v,s in zip(size,scale)]
        if is_leg:
            dims[:2]=[v*obj['leg_width_scale'] for v in dims[:2]]
        geometry=(f'Cylinder {{ radius {min(dims[:2])/2} height {dims[2]} subdivision 16 }}'
                  if is_leg and obj['round_legs'] else 'Box { size '+' '.join(map(str,dims))+' }')
        recognition=''
        if class_id is not None:
            token=token_start+len(instances)
            rgb=token_color(token)
            recognition='recognitionColors [ '+' '.join(str(v/255) for v in rgb)+' ]'
            instances.append({'token':token,'color':rgb,'class_id':class_id,'part':part_id,'object':name})
        children.append(f'''Solid {{ translation {xyz} {recognition}
          children [ Shape {{ appearance PBRAppearance {{ baseColor {color} roughness 1 metalness 0 }} geometry {geometry} }} ]
          boundingObject {geometry} }}''')
    parent_recognition=''
    if obj['kind']=='slipper':
        # Parent recognition includes the strap and sole, with a single label.
        token=token_start; rgb=token_color(token)
        parent_recognition='recognitionColors [ '+' '.join(str(v/255) for v in rgb)+' ]'
        instances=[{'token':token,'color':rgb,'class_id':2,'part':'whole','object':name}]
        children.append('Shape { appearance PBRAppearance { baseColor '+palette[0]+
                        ' roughness 1 metalness 0 } geometry '+_mesh(sole_points(),.018,scale)+' }')
    node=f'''DEF {name} Solid {{ translation {obj['x_m']} {obj['y_m']} 0
       rotation 0 0 1 {obj['yaw_rad']} {parent_recognition}
       children [ {' '.join(children)} ] }}'''
    return node,instances


def make_scene(seed, primary_class):
    rng=random.Random(seed)
    x,y=rng.uniform(.3,2.7),rng.uniform(.3,1.7)
    pose=[x,y,math.atan2(1-y,1.5-x)+rng.uniform(-.6,.6)]
    negative=rng.random()<.10
    objects=[]
    kinds=('box',rng.choice(('table','chair')),'slipper')
    for i in range(0 if negative else rng.randint(1,3)):
        kind=kinds[primary_class] if i==0 else rng.choice(kinds)
        for _ in range(80):
            distance=rng.uniform(.50,1.9)
            angle=pose[2]+rng.uniform(-.45,.45)
            x,y=pose[0]+distance*math.cos(angle),pose[1]+distance*math.sin(angle)
            margin=.43 if kind=='table' else (.29 if kind=='chair' else .20)
            if not margin<x<3-margin or not margin<y<2-margin:
                continue
            if any(math.dist((x,y),(o['x_m'],o['y_m']))<margin+o['margin_m']+.02 for o in objects):
                continue
            colors=[' '.join(f'{rng.uniform(.06,.80):.4f}' for _ in range(3)) for _ in range(2)]
            scale=[rng.uniform(.75,1.20),rng.uniform(.75,1.20),rng.uniform(.80,1.20)]
            if kind in ('table','chair'):
                # Thin and thicker legs, independent of furniture width/height.
                # This scale varies the whole prop; round legs add shape diversity.
                scale[2]=rng.uniform(.85,1.15)
            objects.append(dict(kind=kind,x_m=x,y_m=y,yaw_rad=rng.uniform(-math.pi,math.pi),
                                scale=scale,colors=colors,round_legs=rng.random()<.35,
                                leg_width_scale=rng.uniform(.6,1.6),margin_m=margin))
            break
    return {'pose':pose,'objects':objects,'planned_negative':negative,
            'floor_color':[rng.uniform(.45,.95) for _ in range(3)],'light_intensity':rng.uniform(.65,1.25)}


def visible_labels(segmentation, instances):
    import numpy as np
    labels=[]; annotations=[]
    height,width=segmentation.shape[:2]
    for item in instances:
        mask=np.all(np.abs(segmentation.astype(int)-item['color'])<=1,axis=2)
        ys,xs=np.where(mask)
        if len(xs)<12:
            continue
        x0,x1=int(xs.min()),int(xs.max())+1
        y0,y1=int(ys.min()),int(ys.max())+1
        if x1-x0<2 or y1-y0<4:
            continue
        label=f"{item['class_id']} {(x0+x1)/(2*width):.8f} {(y0+y1)/(2*height):.8f} {(x1-x0)/width:.8f} {(y1-y0)/height:.8f}"
        labels.append(label)
        annotations.append({**item,'xyxy':[x0,y0,x1,y1],'visible_pixels':len(xs),
                            'clipped':x0==0 or y0==0 or x1==width or y1==height,
                            'bottom_clipped':y1==height})
    return labels,annotations


def collect(robot):
    import numpy as np
    from .onboard import ego_config
    from .webots_vision import camera_bgr,save_image
    output=Path(os.environ['ROBOT_OBJECT_DATASET'])
    count=int(os.environ.get('ROBOT_DATASET_COUNT','1200'))
    seed_offset=int(os.environ.get('ROBOT_DATASET_SEED_OFFSET','0'))
    split_for(0,count)  # Validate before rendering.
    camera=robot.getDevice('front_camera'); dt=round(robot.getBasicTimeStep())
    camera.enable(dt);camera.recognitionEnable(dt);camera.enableRecognitionSegmentation()
    root=robot.getRoot().getField('children')
    root.importMFNodeFromString(-1,'DEF TRAIN_OBJECTS Group { children [] }')
    objects=robot.getFromDef('TRAIN_OBJECTS').getField('children')
    vehicle=robot.getSelf()
    manifest=[]
    for split in ('train','val','test'):
        (output/'images'/split).mkdir(parents=True,exist_ok=True)
        (output/'labels'/split).mkdir(parents=True,exist_ok=True)
    for index in range(count):
        split=split_for(index,count)
        seed=BASE_SEEDS[split]+seed_offset+index
        scene=make_scene(seed,index%len(CLASSES))
        while objects.getCount():objects.removeMF(0)
        instances=[]
        for i,obj in enumerate(scene['objects']):
            node,labels=training_object(f'TRAIN_OBJ_{i}',obj,len(instances))
            objects.importMFNodeFromString(-1,node);instances.extend(labels)
        x,y,yaw=scene['pose']
        vehicle.getField('translation').setSFVec3f([x,y,.055])
        vehicle.getField('rotation').setSFRotation([0,0,1,yaw]);vehicle.resetPhysics()
        robot.getFromDef('TRAIN_FLOOR').getField('baseColor').setSFColor(scene['floor_color'])
        robot.getFromDef('TRAIN_LIGHT').getField('intensity').setSFFloat(scene['light_intensity'])
        for _ in range(5):
            if robot.step(dt)==-1:return
        bgr=camera_bgr(camera)
        segment=np.frombuffer(camera.getRecognitionSegmentationImage(),dtype=np.uint8).reshape(480,640,4)[:,:,:3][:,:,::-1]
        lines,annotations=visible_labels(segment,instances)
        image=output/'images'/split/f'{index:05d}.png'
        label=output/'labels'/split/f'{index:05d}.txt'
        save_image(image,bgr)
        label.write_text('\n'.join(lines)+('\n' if lines else ''),encoding='utf-8')
        manifest.append({'id':index,'split':split,'seed':seed,'scene':scene,'annotations':annotations,
                         'image':image.relative_to(output).as_posix(),'label':label.relative_to(output).as_posix(),
                         'image_sha256':hashlib.sha256(image.read_bytes()).hexdigest(),
                         'label_sha256':hashlib.sha256(label.read_bytes()).hexdigest()})
        if index%20==0 or index==count-1:
            (output/'progress.json').write_text(json.dumps({'completed':index+1,'total':count}),encoding='utf-8')
            print(f'[DATASET] {index+1}/{count}',flush=True)
    (output/'dataset.yaml').write_text('path: .\ntrain: images/train\nval: images/val\ntest: images/test\nnames:\n'+
        ''.join(f'  {i}: {name}\n' for i,name in enumerate(CLASSES)),encoding='utf-8')
    (output/'manifest.json').write_text(json.dumps({'schema':1,'classes':CLASSES,'camera':ego_config(),
        'source':'Webots onboard RGB; visible-pixel GT masks only for offline labels; synthetic data only',
        'label_policy':'box, individual furniture legs, whole slipper; furniture tops/seats/backrests are background occluders',
        'scenes':manifest},indent=2),encoding='utf-8')
    robot.simulationQuit(0)
