"""Deterministic 2D differential-drive oracle. Not a replacement for Webots physics."""
from dataclasses import dataclass
import json
import math
from .models import ROOT, Command, Pose, Ranges, sensor_mounts, sensor_ray, wrap_angle
from .grid import Grid
from .navigation import Navigator, TERMINAL


def scenarios():
    return json.loads((ROOT / "config/scenarios.json").read_text(encoding="utf-8"))


def get_scenario(name):
    extra = json.loads((ROOT / "config/safety_scenarios.json").read_text(encoding="utf-8"))
    extra += json.loads((ROOT / "config/vision_scenarios.json").read_text(encoding="utf-8"))
    for item in scenarios() + extra:
        if item["name"] == name:
            return item
    raise ValueError(f"Unknown scenario: {name}; choose from {', '.join(s['name'] for s in scenarios())}")


def rect_distance(x, y, rect):
    return math.hypot(max(rect[0] - x, 0, x - rect[2]), max(rect[1] - y, 0, y - rect[3]))


def ray_distance(x, y, yaw, rect, max_range):
    near, far = 0.0, max_range
    for origin, direction, lo, hi in ((x, math.cos(yaw), rect[0], rect[2]),
                                       (y, math.sin(yaw), rect[1], rect[3])):
        if abs(direction) < 1e-12:
            if not lo <= origin <= hi:
                return max_range
        else:
            a, b = sorted(((lo - origin) / direction, (hi - origin) / direction))
            near, far = max(near, a), min(far, b)
            if near > far:
                return max_range
    return max(0, near)


class KinematicWorld:
    def __init__(self, config, scenario):
        self.config, self.scenario = config, scenario
        self.x, self.y, self.theta = scenario["start"]
        self.obstacles = [tuple(r) for r in scenario["obstacles"]]
        self.spawned = set()
        self.last_command = Command()
        self.collision = False
        self.distance_m = 0.0

    def spawn(self, now):
        for i, event in enumerate(self.scenario.get("spawn", [])):
            if i not in self.spawned and now >= event["at_s"]:
                self.obstacles.append(tuple(event["rect"]))
                self.spawned.add(i)

    def pose(self, now):
        return Pose(self.x, self.y, self.theta, now)

    def ranges(self, pose, now):
        c = self.config
        walls = [(-0.1, -0.1, 0, c.height_m + 0.1), (c.width_m, -0.1, c.width_m + 0.1, c.height_m + 0.1),
                 (0, -0.1, c.width_m, 0), (0, c.height_m, c.width_m, c.height_m + 0.1)]
        result = {}
        for name, mount in sensor_mounts(c).items():
            x, y, yaw = sensor_ray(pose, mount)
            result[name] = min(ray_distance(x, y, yaw, r, c.sensor_max_m) for r in self.obstacles + walls)
        return Ranges(**result, timestamp=now)

    def command(self, command):
        self.last_command = command

    def step(self, dt):
        c, cmd = self.config, self.last_command
        speed = (cmd.left + cmd.right) / 2
        omega = (cmd.right - cmd.left) / c.axle_length_m
        # Exact circular-arc integration, with swept-circle collision substeps.
        count = max(1, math.ceil(abs(speed * dt) / 0.002))
        for _ in range(count):
            interval = dt / count
            theta = self.theta + omega * interval
            if abs(omega) < 1e-9:
                nx, ny = self.x + speed * interval * math.cos(self.theta), self.y + speed * interval * math.sin(self.theta)
            else:
                nx = self.x + speed / omega * (math.sin(theta) - math.sin(self.theta))
                ny = self.y - speed / omega * (math.cos(theta) - math.cos(self.theta))
            collision = min(nx, ny, c.width_m - nx, c.height_m - ny) < c.radius_m
            collision |= any(rect_distance(nx, ny, rect) < c.radius_m for rect in self.obstacles)
            if collision:
                self.collision = True
                self.command(Command())
                return
            self.distance_m += math.hypot(nx - self.x, ny - self.y)
            self.x, self.y, self.theta = nx, ny, wrap_angle(theta)


@dataclass
class Frame:
    time: float
    pose: Pose
    ranges: Ranges
    command: Command
    state: str
    reason: str
    path_id: int
    collision: bool
    goal: tuple | None = None


class Simulation:
    def __init__(self, config, scenario):
        self.config, self.scenario = config, scenario
        self.grid = Grid(config, scenario["obstacles"])
        self.navigator = Navigator(self.grid, scenario["goal"])
        self.world = KinematicWorld(config, scenario)
        self.now = 0.0
        self.frames = []
        self.grid_violation = False
        self.navigator.start()

    @property
    def done(self):
        return self.navigator.state in TERMINAL

    def tick(self):
        self.world.spawn(self.now)
        pose = self.world.pose(self.now)
        ranges = self.world.ranges(pose, self.now)
        cmd = self.navigator.tick(pose, ranges, self.now)
        if self.now >= self.config.max_time_s and not self.done:
            self.navigator.transition("TIMEOUT", "scenario_time_limit", self.now)
            cmd = Command()
        self.world.command(cmd)
        self.world.step(self.config.dt_s)
        if self.world.collision:
            self.navigator.transition("SAFE_STOP", "collision", self.now)
            cmd = Command()
        current = self.world.pose(self.now)
        if not self.grid.free(self.grid.cell(current.x, current.y)):
            self.grid_violation = True
            self.navigator.transition("SAFE_STOP", "inflated_grid_violation", self.now)
            self.world.command(Command())
            cmd = Command()
        frame = Frame(self.now, pose, ranges, cmd, self.navigator.state, self.navigator.reason,
                      self.navigator.path_id, self.world.collision)
        self.frames.append(frame)
        self.now += self.config.dt_s
        return frame

    def run(self):
        while not self.done:
            self.tick()
        return self.summary()

    def summary(self):
        nav = self.navigator
        replanned = nav.path_id > 1
        passed = (nav.state == self.scenario["expected"] and not self.world.collision and
                  not self.grid_violation and (not self.scenario.get("require_replan") or replanned))
        return {"scenario": self.scenario["name"], "mode": "kinematic_2d", "expected": self.scenario["expected"],
                "state": nav.state, "passed": passed, "time_s": round(self.now, 3),
                "distance_m": round(self.world.distance_m, 4), "plans": nav.path_id,
                "collision": self.world.collision, "inflated_grid_violation": self.grid_violation,
                "goal_error_m": math.dist((self.world.x, self.world.y), nav.goal),
                "max_planning_ms": max((p["duration_ms"] for p in nav.plans), default=0)}
