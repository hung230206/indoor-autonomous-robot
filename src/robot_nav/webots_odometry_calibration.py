"""Dedicated empty-floor calibration. GT measurements never run in navigation."""
import json
import math
import os
from pathlib import Path
from .models import Config,wrap_angle


def collect(robot):
    c=Config(**json.loads(robot.getCustomData())['config'])
    motors=[robot.getDevice(s+'_motor') for s in ('left','right')]
    enc=[robot.getDevice(s+'_encoder') for s in ('left','right')]
    dt=round(robot.getBasicTimeStep())
    for m in motors: m.setPosition(float('inf')); m.setVelocity(0)
    for s in enc: s.enable(dt)
    for _ in range(16): robot.step(dt)
    phases=[]
    node=robot.getSelf()

    def measure(left,right,steps):
        before=node.getPosition()[:2]
        e0=[s.getValue() for s in enc]
        last=math.atan2(node.getOrientation()[3],node.getOrientation()[0])
        turn=0
        for m,speed in zip(motors,(left,right)): m.setVelocity(speed/c.wheel_radius_m)
        for _ in range(steps):
            robot.step(dt)
            angle=math.atan2(node.getOrientation()[3],node.getOrientation()[0])
            turn+=wrap_angle(angle-last); last=angle
        for m in motors: m.setVelocity(0)
        for _ in range(8):
            robot.step(dt)
            angle=math.atan2(node.getOrientation()[3],node.getOrientation()[0])
            turn+=wrap_angle(angle-last); last=angle
        item={'commands_m_s':[left,right],'steps':steps,'distance_m':math.dist(before,node.getPosition()[:2]),
              'true_angle_rad':turn,'encoder_deltas_rad':[s.getValue()-e for s,e in zip(enc,e0)]}
        phases.append(item)
        return item
    straight=measure(.08,.08,80)
    radius=straight['distance_m']/(sum(straight['encoder_deltas_rad'])/2)
    turns=[measure(-.06,.06,100),measure(.06,-.06,100)]
    axle=sum(radius*(t['encoder_deltas_rad'][1]-t['encoder_deltas_rad'][0])/t['true_angle_rad'] for t in turns)/2
    result={'wheel_radius_m':radius,'axle_length_m':axle,
            'source':'Offline dedicated straight/turn Webots calibration using encoder and measured GT motion, not navigation/test trajectories',
            'phases':phases,'scope':'This Webots contact model only; real robot must be calibrated separately'}
    Path(os.environ['ROBOT_ODOMETRY_CALIBRATION']).write_text(json.dumps(result,indent=2),encoding='utf-8')
    robot.simulationQuit(0)
