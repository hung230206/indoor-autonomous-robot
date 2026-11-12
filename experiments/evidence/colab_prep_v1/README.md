# Colab training preparation, not a new detector benchmark

1200 synthetic onboard-camera scenes; prepared ZIP/notebook. Full GPU training has not run.
The smoke_only folder contains a 1-epoch software smoke test on a different 60-scene dataset.
Do not report its validation scores as production test metrics or use its checkpoint in the robot.
The 180-image production test split has not been evaluated by a trained candidate.
Dataset archive is tracked once under artifacts/training, with its SHA recorded here.
