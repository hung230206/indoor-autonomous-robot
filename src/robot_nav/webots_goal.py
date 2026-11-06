"""Scene goal marker is a user command, never a localization measurement."""
import math


class SceneGoal:
    def __init__(self,robot):
        self.node=robot.getFromDef('GOAL_MARKER')
        self.source='GOAL_MARKER'
        if self.node is None:
            # Compatibility with already saved worlds generated before the DEF.
            children=robot.getRoot().getField('children')
            candidates=[]
            for index in range(children.getCount()):
                node=children.getMFNode(index)
                if node.getTypeName() not in ('Pose','Transform'): continue
                contents=node.getField('children')
                if contents is None or contents.getCount()!=1: continue
                shape=contents.getMFNode(0)
                if shape.getTypeName()!='Shape': continue
                geometry=shape.getField('geometry').getSFNode()
                appearance=shape.getField('appearance').getSFNode()
                if geometry is None or geometry.getTypeName()!='Cylinder' or appearance is None: continue
                color=appearance.getField('baseColor')
                if color is None: continue
                if (abs(geometry.getField('radius').getSFFloat()-.045)<1e-6 and
                    abs(geometry.getField('height').getSFFloat()-.003)<1e-6 and
                    all(abs(a-b)<1e-6 for a,b in zip(color.getSFColor(),(.85,.12,.3)))):
                    candidates.append(node)
            if len(candidates)!=1:
                raise ValueError('Expected one GOAL_MARKER/red goal marker; open a generated demo world')
            self.node=candidates[0]
            self.source='legacy_red_goal_marker'

    def read(self):
        position=self.node.getField('translation').getSFVec3f()
        goal=tuple(position[:2])
        if len(goal)!=2 or not all(math.isfinite(v) for v in goal):
            raise ValueError('Goal marker coordinates must be finite')
        return goal
