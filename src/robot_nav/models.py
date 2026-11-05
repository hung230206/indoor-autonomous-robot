from dataclasses import dataclass, fields
import json
import math
from pathlib import Path
from typing import Protocol


ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Config:
    width_m: float = 3.0
    height_m: float = 2.0
    resolution_m: float = 0.1
    body_length_m: float = 0.18
    body_width_m: float = 0.15
    wheel_radius_m: float = 0.0325
    axle_length_m: float = 0.12
    safety_margin_m: float = 0.04
    max_speed_m_s: float = 0.16
    max_angular_rad_s: float = 1.8
    max_wheel_m_s: float = 0.24
    waypoint_tolerance_m: float = 0.012
    goal_tolerance_m: float = 0.045
    data_timeout_s: float = 0.25
    stop_range_m: float = 0.10
    sensor_max_m: float = 0.8
    dynamic_ttl_s: float = 120.0
    confirmation_frames: int = 2
    dt_s: float = 0.032
    max_time_s: float = 120.0

    def __post_init__(self):
        for f in fields(self):
            value = getattr(self, f.name)
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"{f.name} must be finite and positive")
        if self.confirmation_frames != int(self.confirmation_frames):
            raise ValueError("confirmation_frames must be an integer")
        for dimension in (self.width_m, self.height_m):
            if not math.isclose(dimension / self.resolution_m, round(dimension / self.resolution_m)):
                raise ValueError("Map dimensions must be multiples of resolution_m")

    @property
    def radius_m(self):
        return math.hypot(self.body_length_m / 2, self.body_width_m / 2)

    @property
    def clearance_m(self):
        return self.radius_m + self.safety_margin_m

    @classmethod
    def load(cls, path=None):
        return cls(**json.loads(Path(path or ROOT / "config/robot.json").read_text(encoding="utf-8")))


@dataclass(frozen=True)
class Pose:
    x: float
    y: float
    theta: float
    timestamp: float
    valid: bool = True


@dataclass(frozen=True)
class Ranges:
    front: float | None
    left: float | None
    right: float | None
    timestamp: float


@dataclass(frozen=True)
class Command:
    """Wheel ground velocities in m/s, NOT PWM or angular velocity."""
    left: float = 0.0
    right: float = 0.0


class PoseProvider(Protocol):
    def pose(self, now: float) -> Pose: ...


class RangeProvider(Protocol):
    def ranges(self, pose: Pose, now: float) -> Ranges: ...


class MotionController(Protocol):
    def command(self, command: Command) -> None: ...


def wrap_angle(angle):
    return (angle + math.pi) % (2 * math.pi) - math.pi


def sensor_mounts(config):
    # x, y, yaw in robot frame. Identical in 2D and generated Webots model.
    return {
        "front": (config.body_length_m / 2 + 0.002, 0.0, 0.0),
        "left": (0.0, config.body_width_m / 2 + 0.002, math.pi / 2),
        "right": (0.0, -config.body_width_m / 2 - 0.002, -math.pi / 2),
    }


def sensor_ray(pose, mount):
    x, y, yaw = mount
    c, s = math.cos(pose.theta), math.sin(pose.theta)
    return pose.x + c * x - s * y, pose.y + s * x + c * y, pose.theta + yaw
