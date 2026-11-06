"""Reset a scripted simulation episode, without using GT as navigation pose."""
from datetime import datetime
from pathlib import Path
import shutil
from uuid import uuid4


def archive_previous_run(directory):
    directory=Path(directory)
    directory.mkdir(parents=True,exist_ok=True)
    if not (directory/'summary.json').exists():
        return
    history=directory/'history'/(datetime.now().strftime('%Y%m%d_%H%M%S_')+uuid4().hex[:8])
    history.mkdir(parents=True)
    for source in directory.iterdir():
        if source.is_file() and source.suffix in ('.json','.jsonl','.csv','.jpg','.png','.mp4','.wbt'):
            shutil.copy2(source,history/source.name)
    (directory/'summary.json').unlink()


def reset_episode(robot,scenario):
    """Restore known A and remove only scenario-owned transient nodes.

    Saved .wbt files can contain a moved robot, nonzero joint positions, and
    duplicate spawned boxes. Encoder offsets are intentionally measured after
    settling, so joints do not need to be forced to zero. This writes initial
    conditions; it does not read a GT position into the pose estimator.
    """
    owned={f'DYNAMIC_{i}' for i in range(len(scenario.get('spawn',[])))}|{'CURRENT_ROUTE'}
    children=robot.getRoot().getField('children')
    removed=[]
    for index in range(children.getCount()-1,-1,-1):
        node=children.getMFNode(index)
        name=node.getDef()
        if name in owned:
            removed.append(name)
            node.remove()
    node=robot.getSelf()
    x,y,theta=scenario['start']
    node.getField('translation').setSFVec3f([x,y,.055])
    node.getField('rotation').setSFRotation([0,0,1,theta])
    node.resetPhysics()
    return {'known_start':scenario['start'],'removed_transient_nodes':removed,
            'policy':'reset_scripted_episode_to_A_before_sensor_baselines'}
