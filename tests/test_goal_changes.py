import csv
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from robot_nav.models import Config,Pose,Ranges,Command
from robot_nav.grid import Grid
from robot_nav.navigation import Navigator
from robot_nav.simulation import Frame
from robot_nav.recording import write_run


class GoalChangesTests(unittest.TestCase):
    def test_new_goal_does_not_finish_at_previous_target(self):
        nav=Navigator(Grid(Config()),(2.65,1.05))
        nav.start(0)
        p=Pose(.35,1.05,0,0); ranges=Ranges(.8,.8,.8,0)
        nav.tick(p,ranges,0)
        self.assertTrue(nav.set_goal((.35,1.6),1))
        self.assertEqual(nav.tick(Pose(2.65,1.05,0,1),Ranges(.8,.8,.8,1),1),Command())
        self.assertEqual(nav.state,'FOLLOWING')
        self.assertEqual(nav.waypoints[-1],(.35,1.6))
        self.assertNotEqual(nav.state,'GOAL_REACHED')

    def test_goal_reached_and_no_path_can_receive_new_targets_but_faults_stay_latched(self):
        for state,allowed in (('GOAL_REACHED',True),('NO_PATH',True),('SAFE_STOP',False),('TIMEOUT',False)):
            nav=Navigator(Grid(Config()),(2.65,1.05)); nav.state=state
            self.assertEqual(nav.set_goal((.35,1.6),1),allowed)
            if allowed:
                self.assertEqual(nav.state,'REPLANNING')
            else:
                self.assertEqual(nav.state,state)
                self.assertEqual(nav.goal,(2.65,1.05))

    def test_outside_goal_is_not_clamped_or_reported_reached(self):
        nav=Navigator(Grid(Config()),(2.65,1.05)); nav.start(0)
        nav.set_goal((4,1),0)
        nav.tick(Pose(.35,1.05,0,0),Ranges(.8,.8,.8,0),0)
        self.assertEqual(nav.state,'NO_PATH')

    def test_log_retains_goal_that_was_active_for_each_frame(self):
        nav=Navigator(Grid(Config()),(.35,1.6))
        frames=[Frame(0,Pose(.35,1.05,0,0),Ranges(.8,.8,.8,0),Command(),'FOLLOWING','',1,False,(2.65,1.05)),
                Frame(1,Pose(.35,1.05,0,1),Ranges(.8,.8,.8,1),Command(),'REPLANNING','goal_changed',1,False,(.35,1.6))]
        with tempfile.TemporaryDirectory() as directory:
            write_run(directory,Config(),{},frames,nav,{'mode':'test'})
            with (Path(directory)/'trajectory.csv').open() as stream: rows=list(csv.DictReader(stream))
            self.assertEqual(float(rows[0]['goal_x_m']),2.65)
            self.assertEqual(float(rows[1]['goal_y_m']),1.6)


if __name__=='__main__': unittest.main()
