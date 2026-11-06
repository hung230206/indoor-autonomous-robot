"""Measure effective encoder odometry parameters on a separate empty world."""
import os
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from robot_nav.models import Config
from robot_nav.webots_world import generate_world
from robot_nav.simulation import get_scenario
from robot_nav.vision import configure_camera_runtime
from run_webots import locate_webots


def main():
    output=ROOT/'config/odometry_webots.json'
    if output.exists(): raise SystemExit('Calibration exists; preserve it before running again')
    configure_camera_runtime('stage1')
    world=ROOT/'worlds/odometry_calibration.wbt'
    generate_world(Config.load(),get_scenario('open'),world,vision='ego')
    env=os.environ.copy()
    env.update(ROBOT_ODOMETRY_CALIBRATION=str(output),PYTHONIOENCODING='utf-8')
    run=subprocess.run([str(locate_webots()),'--batch','--minimize','--no-rendering','--mode=fast',str(world)],env=env,cwd=ROOT,timeout=120,capture_output=True)
    if run.returncode or not output.exists(): raise RuntimeError(run.stderr.decode(errors='replace'))
    print(output.read_text())


if __name__=='__main__': main()
