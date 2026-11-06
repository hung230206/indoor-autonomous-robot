# Goal marker synchronization regression

The old controller read the target from the scenario JSON while the red scene marker could be moved independently. A normal process exit was also easily mistaken for mission success. The new controller reads GOAL_MARKER (or the identifiable legacy red marker), reports the active goal and remaining distance, replans on changes and preserves per-frame target coordinates in CSV.

Native integration (`tools/check_goal_sync.py`) used an independent Supervisor test probe to move only the marker, never the robot pose or navigation internals:

1. JSON goal was (2.65, 1.65); the saved scene marker was (0.35, 1.45). Startup selected the scene marker.
2. At simulation t=3 s the marker moved to (0.55, 1.55), during travel. The controller changed target, reached that target with true error about 0.03875 m and did not finish at the old JSON goal.
3. After GOAL_REACHED the marker moved to (1.55, 1.55). The same interactive controller resumed planning and reached the new target with true error about 0.04025 m. No controller restart or robot teleport was used between these missions.

The point observed in the user's scene, approximately (2.13, 1.74), was checked separately with the five-box layout. It is blocked in the inflated map at cell (21,17), so the controller correctly ended NO_PATH, passed=false, with about 1.1063 m true distance remaining. This is an unfulfilled requested destination, not an arrival. The result must not be presented as success.

Compatibility with the old unlabeled marker and saved runtime state also reached the original goal (true error about 0.03963 m). 35 code tests passed, as did all ten native baseline expectations (8 arrivals, 2 NO_PATH). SAFE_STOP and TIMEOUT remain latched; moving a target does not clear safety faults. Interactive terminal states keep motors zero and wait for a new target; batch still exits normally for automation.

`integration-result.json` contains the two completed missions and startup target comparison. `trajectory.csv` stores the actual target active at each timestamp. Other folders retain the blocked user target and legacy compatibility results. This is simulation-only verification; it does not validate real hardware positioning.
