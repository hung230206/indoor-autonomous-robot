import heapq
import math
from pathlib import Path
import random
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from robot_nav.models import Config, Command, Pose, Ranges
from robot_nav.grid import Grid
from robot_nav.planning import astar
from robot_nav.navigation import Navigator
from robot_nav.simulation import Simulation, scenarios, get_scenario, ray_distance


class PlanningTests(unittest.TestCase):
    def test_empty_optimal_cost_and_endpoints(self):
        grid = Grid(Config())
        path = astar(grid,(3,3),(25,15))
        cost = sum(math.dist(a,b) for a,b in zip(path,path[1:]))
        self.assertEqual(path[0],(3,3))
        self.assertEqual(path[-1],(25,15))
        self.assertAlmostEqual(cost,12*math.sqrt(2)+10)

    def test_no_diagonal_corner_cutting(self):
        grid = Grid(Config())
        grid.blocked.update({(4,3),(3,4),(2,3),(3,2)})
        self.assertEqual(astar(grid,(3,3),(4,4)),[])
        self.assertFalse(grid.segment_free(grid.center((3,3)),grid.center((4,4))))

    def test_bounds_and_blocked_goal(self):
        grid = Grid(Config(),[(1,0,1.2,2)])
        self.assertEqual(astar(grid,(3,3),(25,15)),[])
        self.assertEqual(astar(grid,(-1,0),(3,3)),[])
        self.assertEqual(astar(grid,(3,3),(30,3)),[])
        self.assertEqual(astar(grid,(3,3),(10,10)),[])
        self.assertEqual(astar(grid,(3,3),(3,3)),[(3,3)])

    def test_inflation_and_narrow_gap(self):
        grid = Grid(Config(),[(1,0,1.2,.95),(1,1.15,1.2,2)])
        self.assertFalse(grid.free((9,9)))
        self.assertEqual(astar(grid,(3,10),(25,10)),[])
        self.assertFalse(grid.free((0,10)))
        self.assertFalse(grid.free((29,10)))

    def test_astar_matches_independent_dijkstra_random_maps(self):
        randomizer = random.Random(42)
        for _ in range(15):
            grid = Grid(Config())
            grid.blocked.update((x,y) for x in range(2,28) for y in range(2,18) if randomizer.random()<.2)
            start, goal = (3,3),(26,16)
            grid.blocked.difference_update({start,goal})
            pending, visited = [(0,start)],set()
            optimum = math.inf
            while pending:
                cost,cell = heapq.heappop(pending)
                if cell in visited:
                    continue
                visited.add(cell)
                if cell==goal:
                    optimum=cost
                    break
                for dx in (-1,0,1):
                    for dy in (-1,0,1):
                        nxt=cell[0]+dx,cell[1]+dy
                        if not (dx or dy) or not grid.free(nxt):
                            continue
                        if dx and dy and (not grid.free((nxt[0],cell[1])) or not grid.free((cell[0],nxt[1]))):
                            continue
                        heapq.heappush(pending,(cost+math.hypot(dx,dy),nxt))
            path=astar(grid,start,goal)
            actual=sum(math.dist(a,b) for a,b in zip(path,path[1:])) if path else math.inf
            self.assertAlmostEqual(actual,optimum)


class SafetyTests(unittest.TestCase):
    def setUp(self):
        self.config=Config()
        self.nav=Navigator(Grid(self.config),(2.65,1.05))
        self.nav.start()

    def test_stale_and_invalid_data_stop(self):
        for pose,ranges,now in (
            (Pose(.35,1.05,0,0),Ranges(.8,.8,.8,0),1),
            (Pose(.35,1.05,0,0,False),Ranges(.8,.8,.8,0),0),
            (Pose(.35,1.05,0,0),Ranges(None,.8,.8,0),0),
            (Pose(.35,1.05,0,0),Ranges(float('nan'),.8,.8,0),0),
            (Pose(.35,1.05,0,0),Ranges(.8,.8,.8,2),0),
            (Pose(.35,1.05,0,0),Ranges(0,.8,.8,0),0),
        ):
            with self.subTest(pose=pose,ranges=ranges):
                self.nav.start(now)
                self.assertEqual(self.nav.tick(pose,ranges,now),Command())
                self.assertEqual(self.nav.state,"SAFE_STOP")

    def test_emergency_and_user_stop_are_latched(self):
        p=Pose(.35,1.05,0,0)
        self.assertEqual(self.nav.tick(p,Ranges(.05,.8,.8,0),0),Command())
        self.assertEqual(self.nav.state,"SAFE_STOP")
        self.assertEqual(self.nav.tick(p,Ranges(.8,.8,.8,0),0),Command())
        self.nav.start()
        self.nav.stop()
        self.assertEqual(self.nav.tick(p,Ranges(.8,.8,.8,0),0),Command())

    def test_dynamic_confirmation_and_expiry(self):
        grid=Grid(self.config)
        p=Pose(.35,1.05,0,0)
        r=Ranges(.5,.8,.8,0)
        self.assertFalse(grid.observe(p,r,0))
        self.assertTrue(grid.observe(p,r,.032))
        self.assertTrue(grid.dynamic)
        self.assertTrue(grid.observe(p,Ranges(.8,.8,.8,121),121))
        self.assertFalse(grid.dynamic)

    def test_missing_hit_resets_confirmation(self):
        grid=Grid(self.config)
        p=Pose(.35,1.05,0,0)
        grid.observe(p,Ranges(.5,.8,.8,0),0)
        grid.observe(p,Ranges(.8,.8,.8,.032),.032)
        grid.observe(p,Ranges(.5,.8,.8,.064),.064)
        self.assertFalse(grid.dynamic)

    def test_invalid_config(self):
        for kwargs in ({"dt_s":0},{"resolution_m":.13},{"max_speed_m_s":float('nan')},{"confirmation_frames":1.5}):
            with self.assertRaises(ValueError):
                Config(**kwargs)


class ScenarioTests(unittest.TestCase):
    def test_new_obstacle_closes_only_door_and_stops_no_path(self):
        sim=Simulation(Config(),get_scenario("dynamic_no_path"))
        self.assertTrue(sim.run()["passed"])
        self.assertEqual(sim.navigator.state,"NO_PATH")
        self.assertGreater(sim.navigator.path_id,1)
        self.assertTrue(any(f.state=="OBSTACLE_STOP" for f in sim.frames))
        self.assertEqual(sim.frames[-1].command,Command())

    def test_all_ten_scenarios_and_replanning_stop(self):
        for scenario in scenarios():
            with self.subTest(scenario=scenario['name']):
                sim=Simulation(Config(),scenario)
                result=sim.run()
                self.assertTrue(result["passed"],result)
                self.assertLessEqual(abs(sim.frames[-1].command.left),1e-9)
                self.assertLessEqual(abs(sim.frames[-1].command.right),1e-9)
                for frame in sim.frames:
                    if frame.state in {"OBSTACLE_STOP","NO_PATH","SAFE_STOP","GOAL_REACHED"}:
                        self.assertEqual(frame.command,Command())
                    self.assertLessEqual(abs(frame.command.left),sim.config.max_wheel_m_s)
                    self.assertLessEqual(abs(frame.command.right),sim.config.max_wheel_m_s)
                if scenario.get('require_replan'):
                    self.assertTrue(any(f.state=="OBSTACLE_STOP" for f in sim.frames))
                    self.assertNotEqual(sim.navigator.plans[0]['cells'],sim.navigator.plans[-1]['cells'])

    def test_sensor_raycast_geometry(self):
        self.assertAlmostEqual(ray_distance(.5,.5,0,(1,0,1.2,1),.8),.5)
        self.assertEqual(ray_distance(.5,1.5,0,(1,0,1.2,1),.8),.8)


if __name__=="__main__":
    unittest.main()
