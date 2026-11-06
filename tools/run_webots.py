"""Generate and execute Webots scenarios; each process has a bounded timeout."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT / "src"))
from robot_nav.models import Config
from robot_nav.simulation import scenarios, get_scenario
from robot_nav.webots_world import generate_world
from robot_nav.recording import write_batch


def locate_webots():
    choices = [os.environ.get("WEBOTS_HOME"),
               str(Path(os.environ.get("LOCALAPPDATA","")) / "Programs/Webots"),
               "C:/Program Files/Webots"]
    binary = shutil.which("webots")
    if binary:
        return Path(binary)
    for home in choices:
        if home:
            for suffix in ("msys64/mingw64/bin/webots.exe","msys64/ucrt64/bin/webots.exe","webots","Contents/MacOS/webots"):
                path=Path(home)/suffix
                if path.is_file():
                    return path
    raise SystemExit("Webots not found. Install R2025a or set WEBOTS_HOME.")


def run_one(binary,config,scenario,output,record=False,timeout=180,vision=False):
    output=output.resolve()
    world=ROOT/"worlds"/(scenario["name"]+('_ego' if vision=='ego' else '_yolo' if vision else '')+".wbt")
    generate_world(config,scenario,world,vision=vision)
    output.mkdir(parents=True,exist_ok=True)
    # A failed run cannot be mistaken for a previous successful result.
    summary_path=output/"summary.json"
    if summary_path.exists():
        summary_path.unlink()
    env=os.environ.copy()
    env.update({"ROBOT_OUTPUT":str(output),"ROBOT_BATCH":"1","ROBOT_RECORD":"1" if record else "0",
                "PYTHONIOENCODING":"utf-8"})
    if vision:
        from robot_nav.vision import configure_camera_runtime
        configure_camera_runtime('stage1' if vision=='ego' else 'vision_camera')
        env.update({'PATH':str(Path(sys.executable).parent)+os.pathsep+env['PATH'],
                    'YOLO_CONFIG_DIR':str(ROOT/'.cache/ultralytics'),'MPLBACKEND':'Agg'})
        if 'vision_dropout_after_s' in scenario:
            env['ROBOT_EGO_DROP_AFTER_S' if vision=='ego' else 'ROBOT_VISION_DROP_AFTER_S']=str(scenario['vision_dropout_after_s']+(0 if vision=='ego' else 16*config.dt_s))
    args=[str(binary),"--batch","--mode=fast","--minimize","--stdout","--stderr"]
    if not record and not vision:
        args.append("--no-rendering")
    args.append(str(world))
    with (output/"webots.log").open("w",encoding="utf-8") as log:
        process=subprocess.Popen(args,env=env,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,
                                 creationflags=subprocess.CREATE_NO_WINDOW if os.name=="nt" else 0)
        try:
            code=process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            if os.name=="nt":
                subprocess.run(["taskkill","/PID",str(process.pid),"/T","/F"],capture_output=True)
            else:
                process.kill()
            raise RuntimeError(f"Webots timeout: {scenario['name']}; see {output/'webots.log'}")
    if not summary_path.exists():
        raise RuntimeError(f"Webots produced no summary (exit {code}); see {output/'webots.log'}")
    result=json.loads(summary_path.read_text(encoding="utf-8"))
    if code!=0:
        result['passed']=False
    if record:
        try:
            import imageio_ffmpeg
            ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
        except ImportError:
            ffmpeg=shutil.which("ffmpeg")
        if not ffmpeg or not Path(ffmpeg).exists():
            raise RuntimeError("Recording requires ffmpeg: python -m pip install imageio-ffmpeg")
        args=[str(ffmpeg),"-y","-hide_banner","-loglevel","error","-framerate",str(1/(4*config.dt_s)),
              "-i",str(output/"frames/frame-%05d.jpg"),"-vf",
              "scale=960:640:force_original_aspect_ratio=decrease,pad=960:640:(ow-iw)/2:(oh-ih)/2",
              "-c:v","libx264","-pix_fmt","yuv420p","-movflags","+faststart",str(output/"webots.mp4")]
        subprocess.run(args,check=True,timeout=120,capture_output=True)
        # Only remove known generated frame files within this run, after encoding.
        for frame in (output/"frames").glob("frame-*.jpg"):
            frame.unlink()
        (output/"frames").rmdir()
        if vision and (output/'camera-frames').exists():
            from robot_nav.vision import vision_config
            if vision=='ego':
                from robot_nav.onboard import ego_config
                fps=1/(ego_config()['sample_steps']*config.dt_s)
            else:
                fps=1/(vision_config()['sample_steps']*config.dt_s)
            subprocess.run([str(ffmpeg),'-y','-hide_banner','-loglevel','error','-framerate',str(fps),
                '-i',str(output/'camera-frames/frame-%05d.jpg'),'-c:v','libx264','-pix_fmt','yuv420p',
                '-movflags','+faststart',str(output/'yolo-camera.mp4')],check=True,timeout=120,capture_output=True)
            for frame in (output/'camera-frames').glob('frame-*.jpg'):
                frame.unlink()
            (output/'camera-frames').rmdir()
    print(json.dumps(result),flush=True)
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--scenario",default="replanning")
    parser.add_argument("--all",action="store_true")
    parser.add_argument("--record",action="store_true")
    parser.add_argument("--yolo",action="store_true",help="Use fixed RGB camera and trained YOLO box detector")
    parser.add_argument('--ego',action='store_true',help='Onboard front RGB + YOLO + wheel encoder odometry')
    parser.add_argument("--timeout",type=int,default=180)
    parser.add_argument("--output",type=Path,default=ROOT/"experiments/runs/webots")
    args=parser.parse_args()
    selected=scenarios() if args.all else [get_scenario(args.scenario)]
    results=[]
    for scenario in selected:
        results.append(run_one(locate_webots(),Config.load(),scenario,args.output/scenario['name'],args.record,args.timeout,'ego' if args.ego else args.yolo))
    write_batch(args.output,results)
    if not all(r['passed'] for r in results):
        raise SystemExit(1)


if __name__=="__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
