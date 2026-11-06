import math
import time
from .models import Command, wrap_angle
from .planning import astar


TERMINAL = {"GOAL_REACHED", "NO_PATH", "SAFE_STOP", "TIMEOUT"}


class Navigator:
    def __init__(self, grid, goal):
        self.grid, self.config = grid, grid.config
        self.goal = tuple(goal)
        self.state = "IDLE"
        self.reason = ""
        self.path = []
        self.waypoints = []
        self.index = 0
        self.path_id = 0
        self.plans = []
        self.events = []

    def transition(self, state, reason, now):
        if (self.state, self.reason) != (state, reason):
            self.events.append({"time_s": now, "state": state, "reason": reason})
        self.state, self.reason = state, reason

    def start(self, now=0):
        self.transition("LOCALIZING", "start", now)

    def stop(self, now=0):
        self.transition("SAFE_STOP", "user_stop", now)

    def set_goal(self,goal,now):
        if len(goal)!=2 or not all(math.isfinite(v) for v in goal):
            self.transition('SAFE_STOP','invalid_goal',now)
            return False
        goal=tuple(goal)
        if goal==self.goal or self.state in ('SAFE_STOP','TIMEOUT'):
            return False
        self.goal=goal
        self.path=[]
        self.waypoints=[]
        self.index=0
        self.transition('REPLANNING','goal_changed',now)
        self.events[-1]['goal_m']=list(goal)
        return True

    def _plan(self, pose, now):
        self.transition("PLANNING" if self.path_id == 0 else "REPLANNING", "plan", now)
        started = time.perf_counter()
        cells = astar(self.grid, self.grid.cell(pose.x, pose.y), self.grid.cell(*self.goal))
        self.path_id += 1
        self.path = cells
        self.waypoints = [self.grid.center(c) for c in cells]
        # Preserve the user's exact metric goal; validate the last in-cell segment.
        if cells and self.grid.segment_free(self.waypoints[-1], self.goal):
            self.waypoints.append(self.goal)
        self.index = 0
        self.plans.append({"id": self.path_id, "time_s": now,
                           "duration_ms": (time.perf_counter() - started) * 1000,
                           "cells": cells, "waypoints": self.waypoints[:]})
        if not cells or not self.grid.segment_free((pose.x, pose.y), self.waypoints[0]):
            self.transition("NO_PATH", "start_or_goal_blocked_or_disconnected", now)
        else:
            self.transition("FOLLOWING", "path_ready", now)

    def _valid_data(self, pose, ranges, now):
        if not pose.valid or not all(math.isfinite(v) for v in (pose.x, pose.y, pose.theta, pose.timestamp)):
            return "invalid_pose"
        for timestamp in (pose.timestamp, ranges.timestamp):
            if not math.isfinite(timestamp) or not -1e-6 <= now - timestamp <= self.config.data_timeout_s:
                return "stale_or_future_data"
        for value in (ranges.front, ranges.left, ranges.right):
            if value is None or not math.isfinite(value) or not 0 < value <= self.config.sensor_max_m + 1e-6:
                return "invalid_range"
        return ""

    def tick(self, pose, ranges, now, update_ranges=True):
        if self.state in TERMINAL or self.state == "IDLE":
            return Command()
        error = self._valid_data(pose, ranges, now)
        if error:
            self.transition("SAFE_STOP", error, now)
            return Command()
        if update_ranges:
            self.grid.observe(pose, ranges, now)
        if min(ranges.front, ranges.left, ranges.right) < self.config.stop_range_m:
            self.transition("SAFE_STOP", "range_danger", now)
            return Command()
        if self.state in ("LOCALIZING","OBSTACLE_STOP","REPLANNING"):
            self._plan(pose, now)
            return Command()  # Planning never issues motion in the same cycle.
        remaining = [(pose.x, pose.y)] + self.waypoints[self.index:]
        if any(not self.grid.segment_free(a, b) for a, b in zip(remaining, remaining[1:])):
            self.transition("OBSTACLE_STOP", "path_blocked", now)
            return Command()
        if math.dist((pose.x, pose.y), self.goal) <= self.config.goal_tolerance_m:
            self.transition("GOAL_REACHED", "goal_tolerance", now)
            return Command()
        while self.index < len(self.waypoints) - 1 and math.dist((pose.x, pose.y), self.waypoints[self.index]) <= self.config.waypoint_tolerance_m:
            self.index += 1
        target = self.waypoints[self.index]
        distance = math.dist((pose.x, pose.y), target)
        angle = wrap_angle(math.atan2(target[1] - pose.y, target[0] - pose.x) - pose.theta)
        omega = max(-self.config.max_angular_rad_s, min(self.config.max_angular_rad_s, 5 * angle))
        # Turn in place before advancing; conservative baseline for short grid edges.
        speed = 0.0 if abs(angle) > 0.18 else min(self.config.max_speed_m_s, 2.5 * distance) * max(0, math.cos(angle))
        left = speed - omega * self.config.axle_length_m / 2
        right = speed + omega * self.config.axle_length_m / 2
        scale = max(1, abs(left) / self.config.max_wheel_m_s, abs(right) / self.config.max_wheel_m_s)
        return Command(left / scale, right / scale)
