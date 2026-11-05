"""Webots controller: ideal Supervisor pose + native range sensors + motor API."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from robot_nav.webots_adapter import run

run()
