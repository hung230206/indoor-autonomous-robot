"""Onboard RGB ground-contact projection and encoder odometry; no object GT."""
import json
import math
from .models import ROOT, Pose, wrap_angle


def ego_config():
    return json.loads((ROOT/'config/vision_ego.json').read_text(encoding='utf-8'))


def camera_rotation(pitch):
    # Webots Camera looks along local +X, image right is -Y and up is +Z.
    return (0,1,0),pitch


class WheelOdometry:
    def __init__(self,config,start,left,right,calibration=None):
        self.config=config
        self.radius=(calibration or {}).get('wheel_radius_m',config.wheel_radius_m)
        self.axle=(calibration or {}).get('axle_length_m',config.axle_length_m)
        self.x,self.y,self.theta=start
        self.left,self.right=left,right

    def update(self,left,right,now,heading=None):
        if not all(math.isfinite(v) for v in (left,right,now)) or (heading is not None and not math.isfinite(heading)):
            return Pose(self.x,self.y,self.theta,now,False)
        dl=(left-self.left)*self.radius
        dr=(right-self.right)*self.radius
        self.left,self.right=left,right
        distance=(dl+dr)/2
        angle=(dr-dl)/self.axle
        if heading is not None:
            angle=wrap_angle(heading-self.theta)
        scale=1 if abs(angle)<1e-9 else math.sin(angle/2)/(angle/2)
        self.x+=distance*scale*math.cos(self.theta+angle/2)
        self.y+=distance*scale*math.sin(self.theta+angle/2)
        self.theta=wrap_angle(self.theta+angle)
        return Pose(self.x,self.y,self.theta,now)


class OnboardProjection:
    def __init__(self,config):
        self.config=config
        self.pose=None

    @property
    def focal(self):
        return self.config['camera_width']/(2*math.tan(self.config['horizontal_fov_rad']/2))

    def pixel_to_vehicle_ground(self,u,v):
        c=self.config
        a=(u-c['camera_width']/2)/self.focal
        b=(v-c['camera_height']/2)/self.focal
        cp,sp=math.cos(c['pitch_down_rad']),math.sin(c['pitch_down_rad'])
        ray_x,ray_y,ray_z=cp-b*sp,-a,-sp-b*cp
        if ray_z>=-1e-6:
            raise ValueError('Ground contact is above the horizon')
        t=-c['camera_height_m']/ray_z
        x,y=t*ray_x,t*ray_y
        if not c['min_projection_m']<=x<=c['max_projection_m']:
            raise ValueError('Ground contact is outside calibrated range')
        return x+c['offset_x_m'],y

    def vehicle_to_pixel(self,x,y,z=0):
        c=self.config
        x-=c['offset_x_m']; z-=c['camera_height_m']
        cp,sp=math.cos(c['pitch_down_rad']),math.sin(c['pitch_down_rad'])
        depth=x*cp-z*sp
        if depth<=.01:
            raise ValueError('Point behind camera')
        return (c['camera_width']/2-y*self.focal/depth,
                c['camera_height']/2+(-x*sp-z*cp)*self.focal/depth)

    def bbox_to_rect(self,bbox):
        c=self.config
        if self.pose is None or not self.pose.valid:
            raise ValueError('No valid capture-time pose')
        if len(bbox)!=4 or not all(math.isfinite(v) for v in bbox):
            raise ValueError('Invalid box')
        u0,v0,u1,v1=bbox
        # Clipped feet cannot be assumed to touch the floor at the image border.
        if not (1<u0<u1<c['camera_width']-1 and 0<=v0<v1<c['camera_height']-2):
            raise ValueError('Clipped box or invalid ground-contact edge')
        points=[]
        cp,sp=math.cos(self.pose.theta),math.sin(self.pose.theta)
        for u in (u0,u1):
            x,y=self.pixel_to_vehicle_ground(u,v1)
            for delta in (0,c['surface_depth_m']):
                points.append((self.pose.x+(x+delta)*cp-y*sp,self.pose.y+(x+delta)*sp+y*cp))
        return min(p[0] for p in points),min(p[1] for p in points),max(p[0] for p in points),max(p[1] for p in points)
