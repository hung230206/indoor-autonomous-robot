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
from .webots_episode import reset_episode, archive_previous_run
from .webots_goal import SceneGoal


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
    if os.environ.get('ROBOT_EGO_DATASET'):
        from .webots_ego import collect
        collect(robot)
        return
    if os.environ.get('ROBOT_ODOMETRY_CALIBRATION'):
        from .webots_odometry_calibration import collect
        collect(robot)
        return
    metadata = json.loads(robot.getCustomData())
    c, scenario = Config(**metadata["config"]), metadata["scenario"]
    marker=SceneGoal(robot)
    configured_goal=tuple(scenario['goal'])
    scenario['goal']=list(marker.read())
    custom_goal=math.dist(configured_goal,scenario['goal'])>1e-4
    if custom_goal:
        scenario.update(expected='GOAL_REACHED',require_replan=False)
    startup=reset_episode(robot,scenario)
    startup.update({'configured_goal_m':configured_goal,'scene_goal_m':scenario['goal'],'goal_source':marker.source})
    adapter = WebotsAdapter(robot,c)
    grid = Grid(c,scenario["obstacles"])
    nav = Navigator(grid,scenario["goal"])
    visual=None
    receiver=None
    vision_packets=0
    ego=None
    encoders=None
    imu=None
    if metadata.get('perception')=='ego_yolo':
        from .onboard import ego_config, WheelOdometry
        v=ego_config()
        encoders=[robot.getDevice(side+'_encoder') for side in ('left','right')]
        for sensor in encoders:
            sensor.enable(round(c.dt_s*1000))
        imu=robot.getDevice('imu')
        imu.enable(round(c.dt_s*1000))
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
    archive_previous_run(output)
    if encoders:
        from .webots_ego import EgoCamera
        ego=EgoCamera(robot,grid,output)
        visual=ego.layer
    movie = os.environ.get("ROBOT_RECORD") == "1"
    captured = 0
    if movie:
        (output / "frames").mkdir(parents=True,exist_ok=True)
    # Let physics and sensors settle before issuing commands.
    for _ in range(16):
        if robot.step(round(c.dt_s*1000)) == -1:
            return
    start = robot.getTime()
    if encoders:
        calibration_path=ROOT/'config/odometry_webots.json'
        calibration=json.loads(calibration_path.read_text()) if calibration_path.exists() else None
        odometry=WheelOdometry(c,scenario['start'],*[sensor.getValue() for sensor in encoders],calibration=calibration)
        if calibration:
            (output/'odometry-calibration.json').write_text(json.dumps(calibration,indent=2),encoding='utf-8')
        initial_imu_yaw=imu.getRollPitchYaw()[2]
        startup.update({'initial_encoders_rad':[sensor.getValue() for sensor in encoders],
                        'initial_imu_yaw_rad':initial_imu_yaw})
    startup['simulation_start_s']=start
    (output/'startup.json').write_text(json.dumps(startup,indent=2),encoding='utf-8')
    nav.start(0)
    distance = 0.0
    previous = Pose(*scenario['start'],0) if encoders else adapter.pose(0)
    shown_path_id = 0
    collision = violation = False
    max_pose_error=0.0
    evaluations=[]
    truth=adapter.pose(0)
    terminal_saved=False
    goal_started_s=0.0
    goal_changes=[{'time_s':0,'goal_m':list(nav.goal)}]
    batch=os.environ.get('ROBOT_BATCH')=='1'
    def publish_live_navigation(pose,now):
        if os.environ.get('ROBOT_LIVE')!='1': return
        temporary=output/'live-navigation.tmp.json'
        temporary.write_text(json.dumps({'timestamp':now,'state':nav.state,'reason':nav.reason,
            'plans':nav.path_id,'vision_cells':len(grid.vision),'x':pose.x,'y':pose.y,
            'goal_m':list(nav.goal),'goal_distance_m':math.dist((pose.x,pose.y),nav.goal)}),encoding='utf-8')
        try:
            os.replace(temporary,output/'live-navigation.json')
        except PermissionError:
            pass

    def save_result():
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
        if ego:
            summary.update({'mode':'webots_ego_yolo','range_mapping_enabled':True,
                'pose_source':'encoder_imu_odometry','camera_mount':'onboard_front',
                'max_odometry_error_m':max_pose_error,
                'true_goal_error_m':math.dist((truth.x,truth.y),nav.goal)})
            if nav.state=='GOAL_REACHED':
                summary['passed']=passed and summary['true_goal_error_m']<=c.goal_tolerance_m
            (output/'pose-evaluation.json').write_text(json.dumps(evaluations),encoding='utf-8')
        summary.update({'goal_m':list(nav.goal),'goal_source':marker.source,'goal_changes':goal_changes,
                        'goal_elapsed_s':(frames[-1].time if frames else 0)-goal_started_s})
        print('[NAV] state='+nav.state+' | task_passed='+str(summary['passed'])+' | goal_m='+str(list(nav.goal)),flush=True)
        print(json.dumps(summary),flush=True)
        if movie:
            robot.exportImage(str(output / "scene.jpg"),95)
        write_run(output,c,scenario,frames,nav,summary)
        return summary

    try:
        while robot.step(round(c.dt_s*1000)) != -1:
            now = robot.getTime()-start
            elapsed = now
            try:
                requested_goal=marker.read()
            except ValueError:
                if nav.state!='SAFE_STOP' or nav.reason!='invalid_goal_marker':
                    terminal_saved=False
                nav.transition('SAFE_STOP','invalid_goal_marker',now)
                requested_goal=nav.goal
            if math.dist(requested_goal,nav.goal)>1e-4 and nav.set_goal(requested_goal,now):
                archive_previous_run(output)
                scenario.update(goal=list(nav.goal),expected='GOAL_REACHED',require_replan=False)
                goal_changes.append({'time_s':now,'goal_m':list(nav.goal)})
                goal_started_s=now
                terminal_saved=False
                print('[NAV] New scene goal: '+str(list(nav.goal)),flush=True)
            waiting=terminal_saved and nav.state in TERMINAL
            for i,event in enumerate(scenario.get("spawn",[])):
                if i not in spawned and elapsed >= event["at_s"]:
                    robot.getRoot().getField("children").importMFNodeFromString(-1,solid_box(f"DYNAMIC_{i}",event["rect"],color="0.93 0.48 0.23"))
                    spawned.add(i)
                    obstacles.append(event["rect"])
            truth = adapter.pose(now)  # Evaluation only in ego mode.
            if encoders:
                heading=scenario['start'][2]+imu.getRollPitchYaw()[2]-initial_imu_yaw
                pose=odometry.update(*[sensor.getValue() for sensor in encoders],now,heading=heading)
            else:
                pose=truth
            max_pose_error=max(max_pose_error,math.dist((pose.x,pose.y),(truth.x,truth.y)))
            if ego and not waiting:
                evaluations.append({'time_s':now,'odometry':[pose.x,pose.y,pose.theta],
                    'ground_truth':[truth.x,truth.y,truth.theta],
                    'encoders':[sensor.getValue() for sensor in encoders]})
            ranges = adapter.ranges(pose,now)
            if ego:
                ego.update(pose,now)
                vision_packets=ego.packets
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
            if waiting:
                adapter.command(Command())
                if round(now/c.dt_s)%8==0:
                    publish_live_navigation(pose,now)
                previous=pose
                continue
            distance += math.dist((pose.x,pose.y),(previous.x,previous.y))
            previous = pose
            # Conservative footprint check independent of the planner.
            collision |= min(truth.x,truth.y,c.width_m-truth.x,c.height_m-truth.y) < c.radius_m-0.002
            collision |= any(rect_distance(truth.x,truth.y,r) < c.radius_m-0.002 for r in obstacles)
            violation |= not grid.free(grid.cell(truth.x,truth.y))
            if visual and not visual.fresh(now):
                cmd=Command()
                if elapsed>v['startup_grace_s']:
                    nav.transition('SAFE_STOP','vision_missing_or_stale',now)
            else:
                # Overhead uses visual mapping; onboard fuses vision and ranges.
                cmd = nav.tick(pose,ranges,now,update_ranges=visual is None or ego is not None)
            if nav.path_id != shown_path_id and not ego:
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
            if elapsed-goal_started_s >= c.max_time_s and nav.state not in TERMINAL:
                nav.transition("TIMEOUT","scenario_time_limit",now)
                cmd = Command()
            adapter.command(cmd)
            if os.environ.get('ROBOT_LIVE')=='1' and (len(frames)%8==0 or nav.state in TERMINAL):
                publish_live_navigation(pose,now)
            frames.append(Frame(elapsed,pose,ranges,cmd,nav.state,nav.reason,nav.path_id,collision,nav.goal))
            if movie and (len(frames) % 4 == 1 or nav.state in TERMINAL):
                robot.exportImage(str(output / "frames" / f"frame-{captured:05d}.jpg"),85)
                captured += 1
            if nav.state in TERMINAL:
                if batch:
                    break
                summary=save_result()
                terminal_saved=True
    finally:
        adapter.command(Command())
        # Allow one physics step to consume the final zero command.
        robot.step(round(c.dt_s*1000))
        if not terminal_saved:
            summary=save_result()
        if ego:
            ego.log.close()
        if batch:
            robot.simulationQuit(0 if summary['passed'] else 1)
