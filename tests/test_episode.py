from pathlib import Path
import json
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from robot_nav.webots_episode import archive_previous_run


class EpisodeHistoryTests(unittest.TestCase):
    def test_restart_preserves_completed_run_and_does_not_copy_history_recursively(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'summary.json').write_text('{"state":"SAFE_STOP"}')
            (root/'pose-evaluation.json').write_text('[{"error":0.73}]')
            (root/'world.wbt').write_text('saved world snapshot')
            (root/'webots.log').write_text('launcher may hold this open')
            archive_previous_run(root)
            first=list((root/'history').iterdir())
            self.assertEqual(len(first),1)
            self.assertEqual(json.loads((first[0]/'summary.json').read_text())['state'],'SAFE_STOP')
            self.assertTrue((first[0]/'pose-evaluation.json').exists())
            self.assertEqual((first[0]/'world.wbt').read_text(),'saved world snapshot')
            self.assertFalse((root/'summary.json').exists())
            self.assertFalse((first[0]/'webots.log').exists())
            (root/'summary.json').write_text('{"state":"GOAL_REACHED"}')
            archive_previous_run(root)
            self.assertEqual(len(list((root/'history').iterdir())),2)
            self.assertFalse(any(p.name=='history' for p in (root/'history').glob('*/*')))


if __name__=='__main__': unittest.main()
