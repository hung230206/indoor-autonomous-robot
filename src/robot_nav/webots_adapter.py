import json
import math
import os
from pathlib import Path
from .models import Config, ROOT, Pose, Ranges, Command
from .grid import Grid
from .navigation import Navigator, TERMINAL
from .simulation import Frame, rect_distance
from .recording import write_run
from .webots_world import solid_box


class WebotsAdapter:
    """ENU is already x/y floor, z up. Wheel m/s -> motor rad/s conversion here."""
    def __init__(self, supervisor, config):
        self.robot, self.config = supervisor, config
        self.node = supervisor.getSelf()
        self.motors = [supervisor.getDevice(name+"_motor") for name in ("left","right")]
        for motor in self.motors:
            motor.setPosition(float("inf"))
            motor.setVelocity(0)
        self.sensors = {name: supervisor.getDevice(name) for name in ("front","left","right")}
        for sensor in self.sensors.values():
            sensor.enable(round(config.dt_s*1000))

    def pose(self, now):
        x,y,_ = self.node.getPosition()
        rotation = self.node.getOrientation()
        return Pose(x,y,math.atan2(rotation[3],rotation[0]),now)

    def ranges(self, pose, now):
        return Ranges(**{name: sensor.getValue() for name,sensor in self.sensors.items()},timestamp=now)

    def command(self, cmd):
        for motor,value in zip(self.motors,(cmd.left,cmd.right)):
            motor.setVelocity(value/self.config.wheel_radius_m)


def run():
    from controller import Supervisor
    robot = Supervisor()
    metadata = json.loads(robot.getCustomData())
    c, scenario = Config(**metadata["config"]), metadata["scenario"]
    adapter = WebotsAdapter(robot,c)
    grid = Grid(c,scenario["obstacles"])
    nav = Navigator(grid,scenario["goal"])
    visual=None
    receiver=None
    vision_packets=0
    if metadata.get('perception')=='yolo':
        from .vision import FloorProjection, VisualObstacleLayer, Detection, vision_config
        v=vision_config()
        visual=VisualObstacleLayer(grid,FloorProjection(v['camera_width'],v['camera_height'],v['camera_z_m'],
            v['horizontal_fov_rad'],c.width_m/2,c.height_m/2),v)
        receiver=robot.getDevice('vision_receiver')
        receiver.enable(round(c.dt_s*1000))
    frames, spawned = [], set()
    obstacles = list(scenario["obstacles"])
    output = Path(os.environ.get("ROBOT_OUTPUT", str(ROOT / "experiments/runs/webots" / scenario["name"])))
    output.mkdir(parents=True,exist_ok=True)
    movie = os.environ.get("ROBOT_RECORD") == "1"
    captured = 0
    if movie:
        (output / "frames").mkdir(parents=True,exist_ok=True)
    # Let physics and sensors settle before issuing commands.
    for _ in range(16):
        if robot.step(round(c.dt_s*1000)) == -1:
            return
    start = robot.getTime()
    nav.start(0)
    distance = 0.0
    previous = adapter.pose(0)
    shown_path_id = 0
    collision = violation = False
    try:
        while robot.step(round(c.dt_s*1000)) != -1:
            now = robot.getTime()-start
            elapsed = now
            for i,event in enumerate(scenario.get("spawn",[])):
                if i not in spawned and elapsed >= event["at_s"]:
                    robot.getRoot().getField("children").importMFNodeFromString(-1,solid_box(f"DYNAMIC_{i}",event["rect"],color="0.93 0.48 0.23"))
                    spawned.add(i)
                    obstacles.append(event["rect"])
            pose = adapter.pose(now)
            ranges = adapter.ranges(pose,now)
            if receiver:
                while receiver.getQueueLength():
                    try:
                        packet=json.loads(receiver.getString())
                        detections=[Detection(tuple(d['xyxy']),d['confidence'],d['label']) for d in packet['detections']]
                        visual.update(detections,packet['timestamp']-start,now)
                        vision_packets+=1
                    except (ValueError,KeyError,TypeError):
                        nav.transition('SAFE_STOP','invalid_vision_packet',now)
                    finally:
                        receiver.nextPacket()
            distance += math.dist((pose.x,pose.y),(previous.x,previous.y))
            previous = pose
            # Conservative footprint check independent of the planner.
            collision |= min(pose.x,pose.y,c.width_m-pose.x,c.height_m-pose.y) < c.radius_m-0.002
            collision |= any(rect_distance(pose.x,pose.y,r) < c.radius_m-0.002 for r in obstacles)
            violation |= not grid.free(grid.cell(pose.x,pose.y))
            if visual and not visual.fresh(now):
                cmd=Command()
                if elapsed>v['startup_grace_s']:
                    nav.transition('SAFE_STOP','vision_missing_or_stale',now)
            else:
                # In YOLO mode, ranges remain an emergency stop, not a mapper.
                cmd = nav.tick(pose,ranges,now,update_ranges=visual is None)
            if nav.path_id != shown_path_id:
                root_children = robot.getRoot().getField("children")
                old_route = robot.getFromDef("CURRENT_ROUTE")
                if old_route:
                    old_route.remove()
                coords = ', '.join(f"{x} {y} 0.012" for x,y in nav.waypoints)
                indices = ' '.join(str(i) for i in range(len(nav.waypoints))) + ' -1'
                if nav.waypoints:
                    root_children.importMFNodeFromString(-1,f'''DEF CURRENT_ROUTE Shape {{
                      appearance Appearance {{ material Material {{ emissiveColor 0.1 0.35 0.9 }} }}
                      geometry IndexedLineSet {{ coord Coordinate {{ point [ {coords} ] }} coordIndex [ {indices} ] }}
                    }}''')
                    if shown_path_id == 0:
                        root_children.importMFNodeFromString(-1,f'''Shape {{
                          appearance Appearance {{ material Material {{ emissiveColor 0.6 0.65 0.7 }} }}
                          geometry IndexedLineSet {{ coord Coordinate {{ point [ {coords} ] }} coordIndex [ {indices} ] }}
                        }}''')
                shown_path_id = nav.path_id
            if movie:
                robot.setLabel(0,f"{scenario['name']} | {nav.state} | t={elapsed:.1f}s | A*: {nav.path_id}",.02,.02,.045,0x203247,0,"Arial")
            if collision or violation:
                nav.transition("SAFE_STOP","collision_or_inflated_grid_violation",now)
                cmd = Command()
            if elapsed >= c.max_time_s and nav.state not in TERMINAL:
                nav.transition("TIMEOUT","scenario_time_limit",now)
                cmd = Command()
            adapter.command(cmd)
            frames.append(Frame(elapsed,pose,ranges,cmd,nav.state,nav.reason,nav.path_id,collision))
            if movie and (len(frames) % 4 == 1 or nav.state in TERMINAL):
                robot.exportImage(str(output / "frames" / f"frame-{captured:05d}.jpg"),85)
                captured += 1
            if nav.state in TERMINAL:
                break
    finally:
        adapter.command(Command())
        # Allow one physics step to consume the final zero command.
        robot.step(round(c.dt_s*1000))
        passed = (nav.state == scenario["expected"] and not collision and not violation and
                  (not scenario.get("require_replan") or nav.path_id > 1))
        summary = {"scenario":scenario["name"],"mode":"webots", "expected":scenario["expected"],
                   "state":nav.state,"passed":passed,"time_s":frames[-1].time if frames else 0,
                   "distance_m":distance,"plans":nav.path_id,"collision":collision,
                   "inflated_grid_violation":violation,"goal_error_m":math.dist((previous.x,previous.y),nav.goal),
                   "max_planning_ms":max((p["duration_ms"] for p in nav.plans),default=0),
                   "webots_version":(Path(os.environ["WEBOTS_HOME"])/"resources/version.txt").read_text().strip()}
        if visual:
            summary.update({'mode':'webots_yolo','vision_packets':vision_packets,
                            'visual_occupied_cells':len(grid.vision),'range_mapping_enabled':False})
        write_run(output,c,scenario,frames,nav,summary)
        print(json.dumps(summary),flush=True)
        if movie:
            robot.exportImage(str(output / "scene.jpg"),95)
        if os.environ.get("ROBOT_BATCH") == "1":
            robot.simulationQuit(0 if passed else 1)
        else:
            robot.simulationSetMode(Supervisor.SIMULATION_MODE_PAUSE)
