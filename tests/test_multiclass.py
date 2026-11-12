import os
import sys
from pathlib import Path
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from robot_nav.models import Config,Pose
from robot_nav.grid import Grid
from robot_nav.onboard import OnboardProjection,ego_config
from robot_nav.vision import Detection,VisualObstacleLayer,obstacle_classes,vision_config


class MulticlassTests(unittest.TestCase):
    def test_new_obstacles_require_two_distinct_frames_and_unknown_labels_stay_out(self):
        for label in ('box','furniture_leg','slipper'):
            with self.subTest(label=label):
                config=vision_config();config.pop('class_name')
                config['class_names']=['box','furniture_leg','slipper']
                class Projection:
                    def bbox_to_rect(self,bbox):return (1.3,.85,1.6,1.25)
                grid=Grid(Config());layer=VisualObstacleLayer(grid,Projection(),config)
                target=Detection((10,10,20,20),.9,label)
                excluded=Detection((10,10,20,20),.99,'person')
                layer.update([excluded],0,0);layer.update([excluded],.256,.256)
                self.assertFalse(grid.vision)
                layer.update([target],.512,.512)
                self.assertFalse(grid.vision)
                layer.update([target],.768,.768)
                self.assertTrue(grid.vision)

    def test_multiclass_does_not_bypass_clipped_ground_contact_rejection(self):
        with patch.dict(os.environ,{'ROBOT_EGO_CONFIG':'config/vision_objects.json'}):
            config=ego_config()
        projection=OnboardProjection(config);projection.pose=Pose(.35,1.05,0,0)
        grid=Grid(Config());layer=VisualObstacleLayer(grid,projection,config)
        for now in (0,.256):
            layer.update([Detection((250,200,280,480),.99,'furniture_leg')],now,now)
        self.assertFalse(grid.vision)

    def test_allowlist_validation_and_legacy_configuration(self):
        self.assertEqual(obstacle_classes({'class_name':'box'}),['box'])
        for names in ([],['box','box'],['box',None],'box'):
            with self.subTest(names=names),self.assertRaises(ValueError):
                obstacle_classes({'class_names':names})

    def test_explicit_config_keeps_camera_calibration_while_selecting_new_weights(self):
        with patch.dict(os.environ,{'ROBOT_EGO_CONFIG':'config/vision_ego_box_legacy.json'}):old=ego_config()
        with patch.dict(os.environ,{'ROBOT_EGO_CONFIG':'config/vision_objects.json'}):new=ego_config()
        self.assertEqual(obstacle_classes(new),['box','furniture_leg','slipper'])
        for key in ('camera_height_m','offset_x_m','pitch_down_rad','horizontal_fov_rad','camera_width','camera_height'):
            self.assertEqual(old[key],new[key])
        self.assertNotEqual(old['model'],new['model'])
