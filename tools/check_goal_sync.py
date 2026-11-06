"""Native integration: moved initial marker, mid-route change, change after arrival."""
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from robot_nav.models import Config
from robot_nav.simulation import get_scenario
from robot_nav.webots_world import generate_world
from run_webots import locate_webots


PROBE='''from controller import Supervisor
from pathlib import Path
import json,os
robot=Supervisor()
out=Path(os.environ['ROBOT_OUTPUT'])
marker=robot.getFromDef('GOAL_MARKER').getField('translation')
stage=0
results=[]
while robot.step(32)!=-1:
    if stage==0 and robot.getTime()>=3:
        marker.setSFVec3f([.55,1.55,.002]);stage=1
    try:
        summary=json.loads((out/'summary.json').read_text())
    except (OSError,ValueError): summary={}
    if stage==1 and summary.get('goal_m')==[.55,1.55]:
        results.append(summary)
        marker.setSFVec3f([1.55,1.55,.002]);stage=2
    elif stage==2 and summary.get('goal_m')==[1.55,1.55]:
        results.append(summary)
        startup=json.loads((out/'startup.json').read_text())
        passed=all(r['passed'] and r['state']=='GOAL_REACHED' for r in results) and startup['scene_goal_m']==[.35,1.45]
        (out/'integration-result.json').write_text(json.dumps({'passed':passed,'startup':startup,'missions':results},indent=2))
        robot.simulationQuit(0 if passed else 1)
        break
    if robot.getTime()>140:
        (out/'integration-error.txt').write_text('Goal synchronization timed out at stage '+str(stage))
        robot.simulationQuit(1);break
'''


def main():
    project=ROOT/'experiments/runs'/('goal_sync_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    project.mkdir(parents=True)
    for name,source in (('stage1',"from robot_nav.webots_adapter import run\nrun()\n"),('probe',PROBE)):
        folder=project/'controllers'/name;folder.mkdir(parents=True)
        (folder/(name+'.py')).write_text('import sys\nsys.path.insert(0,'+repr(str(ROOT/'src'))+')\n'+source,encoding='utf-8')
        (folder/'runtime.ini').write_text('[python]\nCOMMAND = "'+str(Path(sys.executable)).replace('\\','/')+'"\n',encoding='utf-8')
    scenario=get_scenario('open')
    world=project/'worlds/test.wbt'
    generate_world(Config.load(),scenario,world,vision='ego')
    text=world.read_text(encoding='utf-8')
    old='DEF GOAL_MARKER Transform { translation '+str(scenario['goal'][0])+' '+str(scenario['goal'][1])+' 0.002'
    assert old in text
    text=text.replace(old,'DEF GOAL_MARKER Transform { translation 0.35 1.45 0.002')
    text+='\nRobot { name "goal_change_test_probe" controller "probe" supervisor TRUE }\n'
    world.write_text(text,encoding='utf-8')
    env=os.environ.copy()
    env.update(ROBOT_OUTPUT=str(project/'output'),ROBOT_BATCH='0',ROBOT_RECORD='0',PYTHONIOENCODING='utf-8',
        YOLO_CONFIG_DIR=str(ROOT/'.cache/ultralytics'),MPLBACKEND='Agg')
    with (project/'webots.log').open('w',encoding='utf-8') as log:
        result=subprocess.run([str(locate_webots()),'--batch','--minimize','--mode=fast','--stdout','--stderr',str(world)],
            cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=180)
    print('Output:',project)
    if result.returncode: raise SystemExit('Goal synchronization integration failed; inspect webots.log')
    report=json.loads((project/'output/integration-result.json').read_text())
    assert report['passed']
    print(json.dumps(report,indent=2))
    (ROOT/'experiments/runs/goal_sync_latest.txt').write_text(str(project),encoding='utf-8')


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
