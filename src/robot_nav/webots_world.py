"""Native, self-contained Webots geometry: no remote PROTO downloads."""
import json
import math
from pathlib import Path
from .models import ROOT, sensor_mounts


def solid_box(name, rect, height=.28, color="0.22 0.29 0.37"):
    x0,y0,x1,y1 = rect
    return f'''DEF {name} Solid {{
  translation {(x0+x1)/2} {(y0+y1)/2} {height/2}
  children [ Shape {{ appearance PBRAppearance {{ baseColor {color} roughness 1 metalness 0 }} geometry Box {{ size {x1-x0} {y1-y0} {height} }} }} ]
  name "{name}"
  boundingObject Box {{ size {x1-x0} {y1-y0} {height} }}
}}'''


def generate_world(c, scenario, path, vision=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    metadata = {"scenario":scenario, "config":c.__dict__}
    if vision:
        metadata['perception']='ego_yolo' if vision=='ego' else 'yolo'
    ego=vision=='ego'
    # Controller reads exact config from customData, so map and world cannot drift.
    encoded = json.dumps(json.dumps(metadata))
    pieces = ['#VRML_SIM R2025a utf8', f'''WorldInfo {{
  basicTimeStep {round(c.dt_s*1000)}
  coordinateSystem "ENU"
  contactProperties [
    ContactProperties {{ material1 "wheel" material2 "floor" coulombFriction [ 1 ] }}
    ContactProperties {{ material1 "caster" material2 "floor" coulombFriction [ 0.005 ] }}
  ]
}}
Viewpoint {{ orientation -0.577350269 0.577350269 0.577350269 2.094395102 position {c.width_m/2} {c.height_m/2} 5.5 }}
Background {{ skyColor [ 0.94 0.96 0.98 ] }}
DirectionalLight {{ direction -0.3 -0.5 -1 intensity 1 }}
Solid {{
  translation {c.width_m/2} {c.height_m/2} -0.025
  children [ Shape {{ appearance PBRAppearance {{ baseColor 0.88 0.90 0.93 roughness 1 metalness 0 }} geometry Box {{ size {c.width_m} {c.height_m} 0.05 }} }} ]
  name "floor" contactMaterial "floor"
  boundingObject Box {{ size {c.width_m} {c.height_m} 0.05 }}
}}''']
    for i, rect in enumerate([(-.05,-.05,0,c.height_m+.05),(c.width_m,-.05,c.width_m+.05,c.height_m+.05),
                               (0,-.05,c.width_m,0),(0,c.height_m,c.width_m,c.height_m+.05)]):
        pieces.append(solid_box(f"WALL_{i}",rect))
    for i, rect in enumerate(scenario["obstacles"]):
        pieces.append(solid_box(f"STATIC_{i}",rect))
    gx, gy = scenario["goal"]
    pieces.append(f'''DEF GOAL_MARKER Transform {{ translation {gx} {gy} 0.002 children [ Shape {{ appearance PBRAppearance {{ baseColor 0.85 0.12 0.3 roughness 1 metalness 0 }} geometry Cylinder {{ radius 0.045 height 0.003 }} }} ] }}''')
    sx, sy, theta = scenario["start"]
    children = [f'''Shape {{ appearance PBRAppearance {{ baseColor 0.06 0.58 0.47 roughness 0.6 metalness 0 }} geometry Box {{ size {c.body_length_m} {c.body_width_m-.05} 0.035 }} }}
      Transform {{ translation 0.065 0 0.022 children [ Shape {{ appearance PBRAppearance {{ baseColor 0.95 0.55 0.2 }} geometry Box {{ size 0.025 0.07 0.009 }} }} ] }}''']
    for side, sign in (("left",1),("right",-1)):
        y = sign*c.axle_length_m/2
        encoder_device=(' PositionSensor { name "'+side+'_encoder" }') if ego else ''
        children.append(f'''HingeJoint {{
      jointParameters HingeJointParameters {{ axis 0 1 0 anchor 0 {y} -0.0225 dampingConstant 0.0001 }}
      device [ RotationalMotor {{ name "{side}_motor" maxVelocity 20 maxTorque 0.2 }}{encoder_device} ]
      endPoint Solid {{
        translation 0 {y} -0.0225
        rotation 1 0 0 1.57079632679
        children [ Shape {{ appearance PBRAppearance {{ baseColor 0.07 0.09 0.12 roughness 1 metalness 0 }} geometry Cylinder {{ radius {c.wheel_radius_m} height 0.02 }} }} ]
        name "{side}_wheel" contactMaterial "wheel"
        boundingObject Cylinder {{ radius {c.wheel_radius_m} height 0.02 }}
        physics Physics {{ density -1 mass 0.035 }}
      }}
    }}''')
    children.append('''Solid {
      translation -0.065 0 -0.040
      children [ Shape { appearance PBRAppearance { baseColor 0.4 0.4 0.4 } geometry Sphere { radius 0.015 } } ]
      name "caster" contactMaterial "caster"
      boundingObject Sphere { radius 0.015 }
      physics Physics { density -1 mass 0.01 }
    }''')
    for name,(x,y,yaw) in sensor_mounts(c).items():
        children.append(f'''DistanceSensor {{
      translation {x} {y} 0
      rotation 0 0 1 {yaw}
      name "{name}" type "generic" numberOfRays 1 aperture 0.001
      lookupTable [ 0 0 0, {c.sensor_max_m} {c.sensor_max_m} 0 ]
    }}''')
    if ego:
        from .onboard import ego_config, camera_rotation
        v=ego_config()
        children.append('InertialUnit { name "imu" }')
        axis,angle=camera_rotation(v['pitch_down_rad'])
        children.append(f'''Camera {{ name "front_camera" translation {v['offset_x_m']} 0 {v['camera_height_m']-.055}
          rotation {' '.join(map(str,axis))} {angle}
          width {v['camera_width']} height {v['camera_height']} fieldOfView {v['horizontal_fov_rad']}
          recognition Recognition {{ segmentation TRUE frameThickness 0 occlusion 2 }}
        }}''')
        children.append(f'''Transform {{ translation {v['offset_x_m']} 0 {v['camera_height_m']-.055}
          children [ Shape {{ appearance PBRAppearance {{ baseColor 0.08 0.1 0.15 }} geometry Box {{ size .025 .07 .04 }} }} ] }}''')
    elif vision:
        from .vision import vision_config
        v=vision_config()
        children.append(f'Receiver {{ name "vision_receiver" channel {v["channel"]} }}')
        pieces.append(f'''Robot {{
  translation {c.width_m/2} {c.height_m/2} {v['camera_z_m']}
  children [
    Camera {{ name "overhead" rotation -0.577350269 0.577350269 0.577350269 2.094395102
      width {v['camera_width']} height {v['camera_height']} fieldOfView {v['horizontal_fov_rad']} }}
    Emitter {{ name "vision_emitter" channel {v['channel']} }}
  ]
  name "fixed_overhead_camera"
  controller "vision_camera"
  supervisor TRUE
  customData {json.dumps(json.dumps({'vision':v,'width_m':c.width_m,'height_m':c.height_m}))}
}}''')
    pieces.append(f'''DEF NAV_ROBOT Robot {{
  translation {sx} {sy} 0.055
  rotation 0 0 1 {theta}
  children [ {chr(10).join(children)} ]
  name "mini_2wd"
  controller "stage1"
  customData {encoded}
  supervisor TRUE
  boundingObject Box {{ size {c.body_length_m} {c.body_width_m-.05} 0.035 }}
  physics Physics {{ density -1 mass 0.35 centerOfMass [ -0.01 0 0 ] }}
}}''')
    path.write_text('\n\n'.join(pieces)+'\n', encoding="utf-8")
