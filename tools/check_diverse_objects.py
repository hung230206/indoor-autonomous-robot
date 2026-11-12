"""Record all four 3D object challenges; keep failures as failures."""
import argparse
import json
import os
from pathlib import Path
import sys
from datetime import datetime

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from robot_nav.models import Config
from robot_nav.simulation import get_scenario
from robot_nav.recording import write_batch
from run_webots import run_one, locate_webots


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=ROOT/'experiments/runs'/('diverse_objects_'+datetime.now().strftime('%Y%m%d_%H%M%S')))
    parser.add_argument('--vision-config',type=Path)
    args=parser.parse_args()
    if args.vision_config:os.environ['ROBOT_EGO_CONFIG']=str(args.vision_config.resolve())
    results=[]
    for name in ('objects_room','unknown_table','unknown_chair','unknown_slipper'):
        results.append(run_one(locate_webots(),Config.load(),get_scenario(name),args.output/name,
                               record=True,timeout=180,vision='ego'))
    write_batch(args.output,results)
    print('Output:',args.output)
    print('Arrivals:',sum(r['state']=='GOAL_REACHED' for r in results),'/ 4')
    # Unsafe outcomes must not be hidden by a test harness accepting any stop.
    if not all(r['passed'] for r in results):
        raise SystemExit(1)


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
