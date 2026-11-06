from dataclasses import asdict
import csv
import json
import platform
from pathlib import Path


FIELDS = ["timestamp_s", "mode", "robot_x_m", "robot_y_m", "theta_rad", "pose_valid",
          "front_m", "left_m", "right_m", "goal_x_m", "goal_y_m", "planned_path_id",
          "command_left_m_s", "command_right_m_s", "state", "stop_reason", "collision_flag"]


def frame_row(frame, goal, mode):
    p, r, c = frame.pose, frame.ranges, frame.command
    return [frame.time, mode, p.x, p.y, p.theta, p.valid, r.front, r.left, r.right,
            *goal, frame.path_id, c.left, c.right, frame.state, frame.reason, frame.collision]


def write_run(directory, config, scenario, frames, navigator, summary):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "trajectory.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(FIELDS)
        writer.writerows(frame_row(f, f.goal if f.goal is not None else navigator.goal, summary["mode"]) for f in frames)
    for name, data in (("summary.json", summary), ("paths.json", navigator.plans),
                       ("events.json", navigator.events), ("scenario.json", scenario),
                       ("config.json", asdict(config)),
                       ("environment.json", {"python": platform.python_version(), "platform": platform.platform()})):
        (directory / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    # CSV layers are integer occupancy (rows indexed from bottom / +y).
    for name, cells in (("static", navigator.grid.static), ("dynamic", navigator.grid.dynamic),
                        ("vision", navigator.grid.vision),
                        ("inflated", navigator.grid.blocked)):
        with (directory / f"map_{name}.csv").open("w", newline="", encoding="utf-8") as stream:
            csv.writer(stream).writerows([int((x, y) in cells) for x in range(navigator.grid.cols)]
                                        for y in range(navigator.grid.rows))


def write_batch(directory, summaries):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "results.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(summaries[0]))
        writer.writeheader()
        writer.writerows(summaries)
