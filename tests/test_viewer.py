from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backend_bases import MouseEvent
    from robot_nav.viewer import interactive
    AVAILABLE=True
except ImportError:
    AVAILABLE=False
from robot_nav.models import Config
from robot_nav.simulation import Simulation, get_scenario


@unittest.skipUnless(AVAILABLE,"Optional matplotlib dependency is missing")
class ViewerTests(unittest.TestCase):
    def test_mouse_controls_goal_unknown_obstacle_and_stop(self):
        sim=Simulation(Config(),get_scenario("open"))

        def interact():
            fig=plt.gcf()
            fig.canvas.draw()
            ax=fig.axes[0]

            def mouse(x,y,button):
                for kind in ("button_press_event","button_release_event"):
                    event=MouseEvent(kind,fig.canvas,x,y,button=button)
                    fig.canvas.callbacks.process(kind,event)

            gx,gy=ax.transData.transform((.6,.7))
            # Axes bounds are installed on the first animation tick.
            ax.set(xlim=(0,3),ylim=(0,2))
            gx,gy=ax.transData.transform((.6,.7))
            mouse(gx,gy,1)
            self.assertAlmostEqual(sim.navigator.goal[0],.6)
            self.assertAlmostEqual(sim.navigator.goal[1],.7)
            ox,oy=ax.transData.transform((1.5,1.1))
            mouse(ox,oy,3)
            self.assertEqual(len(sim.world.obstacles),1)
            self.assertFalse(sim.grid.dynamic,"UI must not reveal unknown obstacles directly to the planner")
            sx,sy=fig.transFigure.transform((.51,.077))
            mouse(sx,sy,1)
            self.assertEqual(sim.navigator.state,"SAFE_STOP")
            plt.close(fig)

        with patch("matplotlib.pyplot.show",side_effect=interact):
            interactive(sim)


if __name__=="__main__":
    unittest.main()
