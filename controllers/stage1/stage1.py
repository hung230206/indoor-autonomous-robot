"""Webots controller: ideal Supervisor pose + native range sensors + motor API."""
from pathlib import Path
import os
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from robot_nav.webots_adapter import run

if os.environ.get('ROBOT_VISION_DATASET'):
    # Dataset collection never runs navigation; ground truth is only for labels.
    from controller import Robot
    robot=Robot()
    while robot.step(round(robot.getBasicTimeStep()))!=-1:
        pass
else:
    run()
