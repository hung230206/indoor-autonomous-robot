"""Occupancy layers; conservative disk inflation against occupied cell squares."""
import math
from .models import sensor_mounts, sensor_ray


class Grid:
    def __init__(self, config, rectangles=()):
        self.config = config
        self.resolution = config.resolution_m
        self.cols = round(config.width_m / self.resolution)
        self.rows = round(config.height_m / self.resolution)
        self.static = set()
        self.dynamic = {}  # cell -> expiration in the caller's monotonic timebase
        self.vision = {}  # independent visual layer; range updates never erase it
        self.confirmations = {}
        for rect in rectangles:
            self.static.update(self.cells_in_rect(rect))
        self.blocked = set()
        self.inflate()

    def inside(self, cell):
        x, y = cell
        return 0 <= x < self.cols and 0 <= y < self.rows

    def cell(self, x, y):
        # Out-of-map coordinates stay out-of-map; never clamp an invalid goal.
        return math.floor(x / self.resolution), math.floor(y / self.resolution)

    def center(self, cell):
        return (cell[0] + 0.5) * self.resolution, (cell[1] + 0.5) * self.resolution

    def cells_in_rect(self, rect):
        x0, y0, x1, y1 = rect
        if not all(math.isfinite(v) for v in rect) or x0 >= x1 or y0 >= y1:
            raise ValueError("Rectangle must be finite [xmin,ymin,xmax,ymax]")
        lo = self.cell(x0, y0)
        hi = self.cell(x1 - 1e-9, y1 - 1e-9)
        return {(x, y) for y in range(lo[1], hi[1] + 1)
                for x in range(lo[0], hi[0] + 1) if self.inside((x, y))}

    def inflate(self):
        r, size = self.config.clearance_m, self.resolution
        occupied = self.static | self.dynamic.keys() | self.vision.keys()
        blocked = set()
        reach = math.ceil(r / size + 0.5)
        for ox, oy in occupied:
            for dy in range(-reach, reach + 1):
                for dx in range(-reach, reach + 1):
                    cell = ox + dx, oy + dy
                    # Distance from candidate cell center to occupied cell square.
                    distance = math.hypot(max(abs(dx) * size - size / 2, 0),
                                          max(abs(dy) * size - size / 2, 0))
                    if self.inside(cell) and distance <= r + 1e-9:
                        blocked.add(cell)
        for y in range(self.rows):
            for x in range(self.cols):
                wx, wy = self.center((x, y))
                if min(wx, wy, self.config.width_m - wx, self.config.height_m - wy) < r:
                    blocked.add((x, y))
        self.blocked = blocked

    def free(self, cell):
        return self.inside(cell) and cell not in self.blocked

    def segment_free(self, a, b):
        # Dense sampling plus explicit corner checks; also used by the controller.
        steps = max(1, math.ceil(math.dist(a, b) / (self.resolution / 8)))
        previous = self.cell(*a)
        if not self.free(previous):
            return False
        for i in range(1, steps + 1):
            t = i / steps
            cell = self.cell(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
            if not self.free(cell):
                return False
            if cell[0] != previous[0] and cell[1] != previous[1]:
                if not self.free((cell[0], previous[1])) or not self.free((previous[0], cell[1])):
                    return False
            previous = cell
        return True

    def observe(self, pose, ranges, now):
        before = set(self.dynamic)
        self.dynamic = {c: expiry for c, expiry in self.dynamic.items() if expiry > now}
        hits = set()
        for name, mount in sensor_mounts(self.config).items():
            distance = getattr(ranges, name)
            if distance is None or not math.isfinite(distance) or not 0 < distance < self.config.sensor_max_m - 0.005:
                continue
            x, y, yaw = sensor_ray(pose, mount)
            # Move a little into the surface, avoiding floor-at-boundary ambiguity.
            cell = self.cell(x + (distance + 0.015) * math.cos(yaw),
                             y + (distance + 0.015) * math.sin(yaw))
            if self.inside(cell) and cell not in self.static:
                hits.add(cell)
        self.confirmations = {c: self.confirmations.get(c, 0) + 1 for c in hits}
        for cell, count in self.confirmations.items():
            if count >= self.config.confirmation_frames:
                self.dynamic[cell] = now + self.config.dynamic_ttl_s
        changed = before != set(self.dynamic)
        if changed:
            self.inflate()
        return changed
