import math
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from robot_nav.models import Config,Pose
from robot_nav.onboard import OnboardProjection,WheelOdometry,ego_config
from robot_nav.webots_world import generate_world
from robot_nav.simulation import get_scenario


class OnboardTests(unittest.TestCase):
    def test_ground_projection_round_trip_at_multiple_ranges(self):
        projection=OnboardProjection(ego_config())
        for x,y in ((.5,-.1),(.9,.2),(1.7,-.4),(2.3,.5)):
            u,v=projection.vehicle_to_pixel(x,y)
            actual=projection.pixel_to_vehicle_ground(u,v)
            self.assertAlmostEqual(actual[0],x)
            self.assertAlmostEqual(actual[1],y)

    def test_camera_right_is_vehicle_right_and_horizon_rejected(self):
        projection=OnboardProjection(ego_config())
        x,y=projection.pixel_to_vehicle_ground(400,400)
        self.assertGreater(x,0)
        self.assertLess(y,0)
        with self.assertRaises(ValueError): projection.pixel_to_vehicle_ground(320,0)

    def test_bbox_uses_capture_pose_and_rejects_clipped_feet(self):
        projection=OnboardProjection(ego_config())
        projection.pose=Pose(1,1,math.pi/2,0)
        u0,v=projection.vehicle_to_pixel(1,.1)
        u1,_=projection.vehicle_to_pixel(1,-.1)
        rect=projection.bbox_to_rect((u0,v-50,u1,v))
        self.assertAlmostEqual(rect[0],.9)
        self.assertAlmostEqual(rect[1],2)
        self.assertAlmostEqual(rect[2],1.1)
        self.assertAlmostEqual(rect[3],2.08)
        with self.assertRaises(ValueError): projection.bbox_to_rect((100,200,300,480))

    def test_wheel_odometry_straight_turn_and_independent_arc(self):
        c=Config()
        odom=WheelOdometry(c,(.35,1.05,0),0,0)
        p=odom.update(1/c.wheel_radius_m,1/c.wheel_radius_m,1)
        self.assertAlmostEqual(p.x,1.35)
        self.assertAlmostEqual(p.y,1.05)
        arc=WheelOdometry(c,(0,0,0),0,0)
        radius=.5; angle=math.pi/2
        p=arc.update((radius-c.axle_length_m/2)*angle/c.wheel_radius_m,
                    (radius+c.axle_length_m/2)*angle/c.wheel_radius_m,1)
        self.assertAlmostEqual(p.x,.5)
        self.assertAlmostEqual(p.y,.5)
        self.assertAlmostEqual(p.theta,angle)
        self.assertFalse(arc.update(float('nan'),0,2).valid)

    def test_ego_world_has_attached_camera_encoders_and_no_external_camera(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'ego.wbt'
            generate_world(Config(),get_scenario('open'),path,vision='ego')
            source=path.read_text(encoding='utf-8')
            self.assertIn('Camera { name "front_camera"',source)
            self.assertIn('PositionSensor { name "left_encoder"',source)
            self.assertNotIn('fixed_overhead_camera',source)
            self.assertNotIn('vision_receiver',source)

    def test_imu_heading_corrects_turn_slip_and_invalid_imu_stops_pose(self):
        c=Config()
        odom=WheelOdometry(c,(0,0,0),0,0)
        # Wheels rotate by unequal amounts, but IMU reports no body turn.
        p=odom.update(1,2,1,heading=0)
        self.assertAlmostEqual(p.theta,0)
        self.assertAlmostEqual(p.y,0)
        self.assertAlmostEqual(p.x,1.5*c.wheel_radius_m)
        self.assertFalse(odom.update(1,2,2,heading=float('nan')).valid)


if __name__=='__main__': unittest.main()
