import unittest
from robot_nav.object_dataset import split_for,make_scene,visible_labels,token_color,BASE_SEEDS


class ObjectDatasetTests(unittest.TestCase):
    def test_splits_are_separate_scenes_and_counts(self):
        from collections import Counter
        self.assertEqual(Counter(split_for(i,1200) for i in range(1200)),{'train':840,'val':180,'test':180})
        seeds=[BASE_SEEDS[split_for(i,1200)]+i for i in range(1200)]
        self.assertEqual(len(set(seeds)),1200)

    def test_scene_is_reproducible_and_geometry_varies(self):
        self.assertEqual(make_scene(123,1),make_scene(123,1))
        self.assertNotEqual(make_scene(123,1),make_scene(124,1))

    def test_visible_mask_box_excludes_occluded_pixels(self):
        import numpy as np
        segment=np.zeros((480,640,3),dtype=np.uint8)
        segment[100:300,50:60]=token_color(0)
        segment[100:170,50:60]=0  # Occluder hides the upper section.
        labels,annotations=visible_labels(segment,[{'color':token_color(0),'class_id':1}])
        self.assertEqual(annotations[0]['xyxy'],[50,170,60,300])
        self.assertAlmostEqual(float(labels[0].split()[2]),235/480,places=7)
        self.assertFalse(annotations[0]['bottom_clipped'])

    def test_clipped_feet_are_retained_and_flagged_for_detection(self):
        import numpy as np
        segment=np.zeros((480,640,3),dtype=np.uint8)
        segment[420:,100:150]=token_color(0)
        _,annotations=visible_labels(segment,[{'color':token_color(0),'class_id':2}])
        self.assertTrue(annotations[0]['bottom_clipped'])
