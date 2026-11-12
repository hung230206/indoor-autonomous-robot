import math
import unittest
from robot_nav.models import Config
from robot_nav.grid import Grid
from robot_nav.scene_objects import prior_rectangles, object_contacts
from robot_nav.simulation import KinematicWorld, get_scenario
from robot_nav.webots_world import furniture_viewpoint


class SceneObjectTests(unittest.TestCase):
    def test_overview_faces_room_using_webots_positive_x_camera_axis(self):
        import re
        values=[float(v) for v in re.findall(r'-?\d+(?:\.\d+)?(?:e[+-]?\d+)?',furniture_viewpoint())]
        x,y,z,angle,px,py,pz=values
        co,si=math.cos(angle),math.sin(angle)
        direction=(co+x*x*(1-co),z*si+y*x*(1-co),-y*si+z*x*(1-co))
        target=(1.5-px,1-py,.1-pz)
        norm=math.sqrt(sum(v*v for v in target))
        self.assertGreater(sum(a*b/norm for a,b in zip(direction,target)),.99999)

    def test_unknown_geometry_is_not_a_navigation_input(self):
        for name in ('unknown_table','unknown_chair','unknown_slipper'):
            self.assertEqual(prior_rectangles(get_scenario(name)['objects']),[])

    def test_table_map_preserves_space_between_legs(self):
        obj=dict(kind='table',x_m=1.5,y_m=1.,map_known=True)
        rectangles=prior_rectangles([obj])
        self.assertEqual(len(rectangles),4)
        grid=Grid(Config.load(),rectangles)
        self.assertNotIn(grid.cell(1.5,1.),grid.static)
        self.assertFalse(grid.free(grid.cell(1.185,.745)))

    def test_rotated_slipper_map(self):
        obj=dict(kind='slipper',x_m=1.,y_m=1.,yaw_rad=math.pi/2,map_known=True)
        rect=prior_rectangles([obj])[-1]
        self.assertAlmostEqual(rect[2]-rect[0],.105)
        self.assertAlmostEqual(rect[3]-rect[1],.25)

    def test_2d_does_not_silently_flatten_3d(self):
        with self.assertRaisesRegex(ValueError,'require Webots'):
            KinematicWorld(Config.load(),get_scenario('objects_room'))

    def test_contact_evaluation_uses_props_and_keeps_identity(self):
        class Point:
            point=(1,2,.018)
        class Prop:
            def getContactPoints(self): return [Point()]
        self.assertEqual(object_contacts([('slipper',Prop())]),
                         [{'object':'slipper','point_m':[1,2,.018]}])
