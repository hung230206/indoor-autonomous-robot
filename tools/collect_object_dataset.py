"""Collect a fresh multi-class dataset without overwriting old data or worlds."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from robot_nav.models import Config
from robot_nav.simulation import get_scenario
from robot_nav.webots_world import generate_world
from robot_nav.vision import configure_camera_runtime
from run_webots import locate_webots


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--count',type=int,default=1200)
    parser.add_argument('--seed-offset',type=int,default=0)
    parser.add_argument('--timeout',type=int,default=900)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.count<20:parser.error('--count must be >= 20')
    output=args.output.resolve()
    if output.exists() and any(output.iterdir()):
        raise SystemExit('Output must be empty/new; never overwrite a dataset')
    output.mkdir(parents=True,exist_ok=True)
    configure_camera_runtime('stage1')
    world=ROOT/'worlds'/('runtime_object_dataset_'+uuid4().hex+'.wbt')
    generate_world(Config.load(),get_scenario('open'),world,vision='ego')
    text=world.read_text(encoding='utf-8')
    text=text.replace('appearance PBRAppearance { baseColor 0.88 0.90 0.93',
                      'appearance DEF TRAIN_FLOOR PBRAppearance { baseColor 0.88 0.90 0.93')
    text=text.replace('DirectionalLight {','DEF TRAIN_LIGHT DirectionalLight {',1)
    world.write_text(text,encoding='utf-8')
    (output/'world.wbt').write_bytes(world.read_bytes())
    env=os.environ.copy()
    for key in ('ROBOT_EGO_DATASET','ROBOT_VISION_DATASET','ROBOT_ODOMETRY_CALIBRATION'):
        env.pop(key,None)
    env.update(ROBOT_OBJECT_DATASET=str(output),ROBOT_DATASET_COUNT=str(args.count),
               ROBOT_DATASET_SEED_OFFSET=str(args.seed_offset),PYTHONIOENCODING='utf-8')
    with (output/'collection.log').open('w',encoding='utf-8') as log:
        process=subprocess.Popen([str(locate_webots()),'--batch','--minimize','--mode=fast','--stdout','--stderr',str(world)],
                                 env=env,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        try:code=process.wait(timeout=args.timeout)
        except subprocess.TimeoutExpired:
            if os.name=='nt':subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True)
            else:process.kill()
            raise RuntimeError('Collection timed out; partial data retained at '+str(output))
    if code or not (output/'manifest.json').exists():
        raise SystemExit('Collection failed; inspect '+str(output/'collection.log'))
    print('Dataset:',output,flush=True)


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
