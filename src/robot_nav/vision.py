"""Image-only box detector and calibrated projection; no simulator object access."""
from dataclasses import dataclass
import json
import math
import time
import sys
from .models import ROOT


def vision_config():
    return json.loads((ROOT/'config/vision.json').read_text(encoding='utf-8'))


def configure_camera_runtime():
    """Webots preferences can override PATH; explicitly select this interpreter."""
    runtime=ROOT/'controllers/vision_camera/runtime.ini'
    runtime.write_text('; Generated local interpreter selection; ignored by Git.\n[python]\nCOMMAND = "'+
                       str(sys.executable).replace('\\','/')+'"\n',encoding='utf-8')


@dataclass(frozen=True)
class Detection:
    xyxy: tuple
    confidence: float
    label: str


@dataclass(frozen=True)
class FloorProjection:
    """Fixed vertical camera; x image-right, +y image-up; SI ground coordinates.

    Calibrated geometry is known, not inferred from YOLO. General phone cameras
    will require an independently measured homography/extrinsic calibration.
    """
    width: int
    height: int
    camera_z: float
    hfov: float
    center_x: float
    center_y: float

    def __post_init__(self):
        if not (self.width>0 and self.height>0 and math.isfinite(self.camera_z) and self.camera_z>0 and 0<self.hfov<math.pi):
            raise ValueError('Invalid camera calibration')

    @property
    def focal_px(self):
        return self.width/(2*math.tan(self.hfov/2))

    def pixel_to_floor(self,u,v):
        return (self.center_x+(u-self.width/2)*self.camera_z/self.focal_px,
                self.center_y-(v-self.height/2)*self.camera_z/self.focal_px)

    def world_to_pixel(self,x,y,z=0):
        if z>=self.camera_z:
            raise ValueError('Point is behind/at camera plane')
        return (self.width/2+(x-self.center_x)*self.focal_px/(self.camera_z-z),
                self.height/2-(y-self.center_y)*self.focal_px/(self.camera_z-z))

    def bbox_to_rect(self,bbox):
        if len(bbox)!=4 or not all(math.isfinite(v) for v in bbox):
            raise ValueError('Invalid bbox')
        u0,v0,u1,v1=bbox
        if not (0<=u0<u1<=self.width and 0<=v0<v1<=self.height):
            raise ValueError('Bbox is outside calibrated image')
        x0,y1=self.pixel_to_floor(u0,v0)
        x1,y0=self.pixel_to_floor(u1,v1)
        return x0,y0,x1,y1


class YoloDetector:
    def __init__(self,weights,config=None):
        from ultralytics import YOLO
        self.config=config or vision_config()
        if not weights.is_file():
            raise FileNotFoundError(f'Model missing: {weights}; see docs/yolo.md')
        self.model=YOLO(str(weights))

    def detect(self,bgr):
        if len(bgr.shape)!=3 or tuple(bgr.shape)!=(self.config['camera_height'],self.config['camera_width'],3):
            raise ValueError('RGB frame does not match the calibrated camera dimensions')
        started=time.perf_counter()
        result=self.model.predict(bgr,imgsz=self.config['image_size'],conf=self.config['confidence'],
                                  device='cpu',verbose=False)[0]
        detections=[Detection(tuple(map(float,box.xyxy[0].tolist())),float(box.conf[0]),
                              result.names[int(box.cls[0])]) for box in result.boxes]
        return detections,(time.perf_counter()-started)*1000,result


class VisualObstacleLayer:
    def __init__(self,grid,projection,config=None):
        self.grid,self.projection=grid,projection
        self.config=config or vision_config()
        self.pending={}
        self.last_frame=None
        self.accepted_rects=[]

    def update(self,detections,timestamp,now):
        # A replay, duplicate or stale image cannot add evidence or refresh TTL.
        if not math.isfinite(timestamp) or not -1e-6<=now-timestamp<=self.config['frame_timeout_s']:
            return False
        if self.last_frame is not None and timestamp<=self.last_frame:
            return False
        self.last_frame=timestamp
        observed=set()
        self.accepted_rects=[]
        pad=self.config['bbox_padding_m']
        for detection in detections:
            if detection.label!=self.config['class_name'] or not math.isfinite(detection.confidence) or not self.config['confidence']<=detection.confidence<=1:
                continue
            try:
                x0,y0,x1,y1=self.projection.bbox_to_rect(detection.xyxy)
            except ValueError:
                continue
            rect=(max(0,x0-pad),max(0,y0-pad),min(self.grid.config.width_m,x1+pad),min(self.grid.config.height_m,y1+pad))
            if rect[0]>=rect[2] or rect[1]>=rect[3]:
                continue
            self.accepted_rects.append(rect)
            observed.update(self.grid.cells_in_rect(rect)-self.grid.static)
        self.pending={cell:self.pending.get(cell,0)+1 for cell in observed}
        before=set(self.grid.vision)
        self.grid.vision={c:t for c,t in self.grid.vision.items() if t>now}
        for cell,count in self.pending.items():
            if count>=self.config['confirmation_frames']:
                self.grid.vision[cell]=now+self.config['obstacle_ttl_s']
        changed=before!=set(self.grid.vision)
        if changed:
            self.grid.inflate()
        return changed

    def fresh(self,now):
        return self.last_frame is not None and 0<=now-self.last_frame<=self.config['frame_timeout_s']
