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


def run_one(binary,config,scenario,output,record=False,timeout=180):
    output=output.resolve()
    world=ROOT/"worlds"/(scenario["name"]+".wbt")
    generate_world(config,scenario,world)
    output.mkdir(parents=True,exist_ok=True)
    # A failed run cannot be mistaken for a previous successful result.
    summary_path=output/"summary.json"
    if summary_path.exists():
        summary_path.unlink()
    env=os.environ.copy()
    env.update({"ROBOT_OUTPUT":str(output),"ROBOT_BATCH":"1","ROBOT_RECORD":"1" if record else "0",
                "PYTHONIOENCODING":"utf-8"})
    args=[str(binary),"--batch","--mode=fast","--minimize","--stdout","--stderr"]
    if not record:
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
    print(json.dumps(result),flush=True)
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--scenario",default="replanning")
    parser.add_argument("--all",action="store_true")
    parser.add_argument("--record",action="store_true")
    parser.add_argument("--timeout",type=int,default=180)
    parser.add_argument("--output",type=Path,default=ROOT/"experiments/runs/webots")
    args=parser.parse_args()
    selected=scenarios() if args.all else [get_scenario(args.scenario)]
    results=[]
    for scenario in selected:
        results.append(run_one(locate_webots(),Config.load(),scenario,args.output/scenario['name'],args.record,args.timeout))
    write_batch(args.output,results)
    if not all(r['passed'] for r in results):
        raise SystemExit(1)


if __name__=="__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
