from pathlib import Path
import math
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from robot_nav.models import Config,Pose,Ranges
from robot_nav.grid import Grid
from robot_nav.vision import Detection,FloorProjection,VisualObstacleLayer,YoloDetector,vision_config


class ProjectionTests(unittest.TestCase):
    def test_wrong_frame_size_rejected_before_inference(self):
        detector=object.__new__(YoloDetector)
        detector.config=vision_config()
        class WrongImage:
            shape=(240,320,3)
        with self.assertRaises(ValueError):
            detector.detect(WrongImage())

    def test_roundtrip_ground_calibration(self):
        p=FloorProjection(640,480,3.4,1.0,1.5,1)
        for point in ((0,0),(.35,1.05),(3,2),(1.5,1)):
            actual=p.pixel_to_floor(*p.world_to_pixel(*point))
            self.assertAlmostEqual(actual[0],point[0])
            self.assertAlmostEqual(actual[1],point[1])

    def test_known_camera_bbox_coordinates(self):
        p=FloorProjection(640,480,3,math.pi/2,1.5,1)
        expected=(0,.25,1.5,1.75)
        for actual,want in zip(p.bbox_to_rect((160,160,320,320)),expected):
            self.assertAlmostEqual(actual,want)

    def test_invalid_bbox_rejected(self):
        p=FloorProjection(640,480,3.4,1,1.5,1)
        for box in ((float('nan'),0,30,30),(-1,0,30,30),(10,10,5,20),(0,0,650,480)):
            with self.assertRaises(ValueError):
                p.bbox_to_rect(box)


class VisualMapTests(unittest.TestCase):
    def setUp(self):
        self.grid=Grid(Config())
        self.p=FloorProjection(640,480,3.4,1,1.5,1)
        self.mapper=VisualObstacleLayer(self.grid,self.p)
        u0,v1=self.p.world_to_pixel(1.3,.85)
        u1,v0=self.p.world_to_pixel(1.6,1.25)
        self.box=Detection((u0,v0,u1,v1),.9,'box')

    def test_confirmation_inflation_and_expiry(self):
        self.assertFalse(self.mapper.update([self.box],0,0))
        self.assertFalse(self.grid.vision)
        self.assertTrue(self.mapper.update([self.box],.256,.256))
        self.assertIn((14,10),self.grid.vision)
        self.assertFalse(self.grid.free((12,10)))
        self.assertTrue(self.mapper.update([],3,3))
        self.assertFalse(self.grid.vision)

    def test_duplicate_detections_and_replayed_frame_do_not_confirm(self):
        self.mapper.update([self.box,self.box],0,0)
        self.mapper.update([self.box],0,.1)
        self.assertFalse(self.grid.vision)
        self.assertTrue(self.mapper.update([self.box],.256,.256))

    def test_low_confidence_wrong_class_and_stale_images_ignored(self):
        wrong=Detection(self.box.xyxy,.99,'chair')
        low=Detection(self.box.xyxy,.2,'box')
        nan=Detection(self.box.xyxy,float('nan'),'box')
        for t in (0,.256,.512):
            self.mapper.update([wrong,low,nan],t,t)
        self.assertFalse(self.grid.vision)
        self.assertFalse(self.mapper.update([self.box],.6,3))
        self.assertFalse(self.mapper.update([self.box],4,3))
        self.assertFalse(self.mapper.fresh(3))

    def test_empty_frame_resets_confirmation(self):
        self.mapper.update([self.box],0,0)
        self.mapper.update([],.256,.256)
        self.mapper.update([self.box],.512,.512)
        self.assertFalse(self.grid.vision)

    def test_range_updates_cannot_erase_visual_layer(self):
        self.mapper.update([self.box],0,0)
        self.mapper.update([self.box],.256,.256)
        cells=set(self.grid.vision)
        self.grid.observe(Pose(.35,1.05,0,.5),Ranges(.8,.8,.8,.5),.5)
        self.assertEqual(cells,set(self.grid.vision))


if __name__=='__main__': unittest.main()
