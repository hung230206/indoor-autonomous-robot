# Saved-world startup regression

The reported failure occurred after saving/reloading the simulated scene. The saved robot was at approximately (0.30728, 0.31982) m with heading 0.93412 rad, while scenario A and the odometry initial pose remained (0.35, 1.05, 0). The saved wheel angles were approximately 78.86 and 105.18 rad. Ten persisted DYNAMIC nodes (two copies of each of five boxes) were also present.

Before the fix, the first evaluation sample already had about 0.7314 m pose error and the run SAFE_STOPped at 0.096 s. This was an inconsistent episode initialization, not evidence of a camera/model inference failure.

After the fix, the controller resets the simulator's initial conditions to the configured A before baselining encoders and IMU, and removes only the scenario-owned transient nodes. Nonzero wheel offsets remain valid and are subtracted. Ground truth is not fed into the running odometry. The launcher generates a unique runtime world and preserves an output snapshot, so it does not overwrite the user's edited canonical world.

The exact saved-state fixture was launched twice. Both runs reached GOAL_REACHED at 29.632 simulation seconds, with no collision/inflated-grid violation, true goal error about 0.03963 m and maximum odometry error about 0.00672 m. Startup telemetry confirms ten old box nodes were removed and the nonzero encoder angles were retained as baselines. The second run archived the first summary under history instead of overwriting its only copy.

31 code tests passed. The kinematic batch passed all ten expectations; the retained native baseline CSV also has 10/10 expected outcomes (8 arrivals and 2 NO_PATH). Previous `ego_v1` and overhead evidence were preserved. These remain simulation-only results.

For a native regression, copy `saved-state-fixture.wbt` into this repository's `worlds/` directory under an ignored `runtime_*.wbt` filename, configure the stage1 interpreter, and launch Webots against that copy with `ROBOT_BATCH=1` and a fresh `ROBOT_OUTPUT`. This fixture intentionally contains saved runtime state; do not use it as the canonical scenario definition.
