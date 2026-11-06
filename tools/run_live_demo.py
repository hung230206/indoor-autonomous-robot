"""Launch a visible Webots demo and its read-only camera monitor."""
import argparse
from datetime import datetime
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from robot_nav.models import Config
from robot_nav.simulation import get_scenario
from robot_nav.vision import configure_camera_runtime
from robot_nav.webots_world import generate_world
from run_webots import locate_webots


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--scenario',default='yolo_many_boxes')
    parser.add_argument('--paused',action='store_true')
    parser.add_argument('--overhead',action='store_true',help='Legacy overhead-camera experiment')
    args=parser.parse_args()
    scenario=get_scenario(args.scenario)
    configure_camera_runtime('vision_camera' if args.overhead else 'stage1')
    output=ROOT/'experiments/runs'/('live_'+('overhead_' if args.overhead else 'ego_')+args.scenario+'_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    output.mkdir(parents=True)
    world=ROOT/'worlds'/(scenario['name']+('_yolo' if args.overhead else '_ego')+'.wbt')
    generate_world(Config.load(),scenario,world,vision=True if args.overhead else 'ego')
    env=os.environ.copy()
    env.update(ROBOT_OUTPUT=str(output),ROBOT_LIVE='1',ROBOT_BATCH='0',ROBOT_RECORD='0',ROBOT_CAMERA_MODE='overhead' if args.overhead else 'ego',
        PYTHONIOENCODING='utf-8',YOLO_CONFIG_DIR=str(ROOT/'.cache/ultralytics'),MPLBACKEND='Agg')
    env.pop('ROBOT_VISION_DATASET',None)
    env.pop('ROBOT_VISION_DROP_AFTER_S',None)
    env.pop('ROBOT_EGO_DROP_AFTER_S',None)
    if 'vision_dropout_after_s' in scenario:
        env['ROBOT_VISION_DROP_AFTER_S' if args.overhead else 'ROBOT_EGO_DROP_AFTER_S']=str(scenario['vision_dropout_after_s']+(16*Config.load().dt_s if args.overhead else 0))
    env['PATH']=str(Path(sys.executable).parent)+os.pathsep+env['PATH']
    pythonw=Path(sys.executable).with_name('pythonw.exe')
    subprocess.Popen([str(pythonw if pythonw.exists() else sys.executable),str(ROOT/'tools/live_camera_viewer.py'),str(output)],cwd=ROOT,env=env)
    with (output/'launch.log').open('w',encoding='utf-8') as log:
        subprocess.Popen([str(locate_webots()),'--mode='+('pause' if args.paused else 'realtime'),'--stdout','--stderr',str(world)],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
    (ROOT/'experiments/runs/live_yolo_latest.txt').write_text(str(output),encoding='utf-8')
    print('Output:',output)


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
