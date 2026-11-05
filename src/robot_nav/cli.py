import argparse
import json
from pathlib import Path
from .models import Config, ROOT
from .simulation import Simulation, get_scenario, scenarios
from .recording import write_run, write_batch


def main():
    parser = argparse.ArgumentParser(description="Stage 1 autonomous robot navigation")
    parser.add_argument("--config", type=Path, help="Robot JSON configuration")
    sub = parser.add_subparsers(dest="action", required=True)
    demo = sub.add_parser("demo", help="Run a 2D scenario")
    demo.add_argument("--scenario", default="replanning")
    demo.add_argument("--gui", action="store_true", help="Interactive 2D viewer")
    demo.add_argument("--export", action="store_true", help="Save PNG and animated GIF")
    demo.add_argument("--output", type=Path, default=ROOT / "experiments/runs/demo")
    batch = sub.add_parser("batch", help="Run all ten deterministic 2D scenarios")
    batch.add_argument("--output", type=Path, default=ROOT / "experiments/runs/batch")
    world = sub.add_parser("world", help="Generate a native Webots .wbt from shared config")
    world.add_argument("--scenario", default="replanning")
    world.add_argument("--output", type=Path, default=ROOT / "worlds/stage1.wbt")
    args = parser.parse_args()
    config = Config.load(args.config)
    if args.action == "world":
        from .webots_world import generate_world
        generate_world(config, get_scenario(args.scenario), args.output)
        print(args.output)
    elif args.action == "batch":
        results = []
        for scenario in scenarios():
            sim = Simulation(config, scenario)
            summary = sim.run()
            write_run(args.output / scenario["name"], config, scenario, sim.frames, sim.navigator, summary)
            results.append(summary)
            print(f"{scenario['name']:18} {summary['state']:14} passed={summary['passed']} plans={summary['plans']} t={summary['time_s']:.1f}s")
        write_batch(args.output, results)
        print(f"Expected outcomes: {sum(r['passed'] for r in results)}/{len(results)}; arrivals: {sum(r['state'] == 'GOAL_REACHED' for r in results)}")
        if not all(r["passed"] for r in results):
            raise SystemExit(1)
    else:
        sim = Simulation(config, get_scenario(args.scenario))
        if args.gui:
            from .viewer import interactive
            sim = interactive(sim)
        elif not sim.done:
            sim.run()
        summary = sim.summary()
        write_run(args.output, config, sim.scenario, sim.frames, sim.navigator, summary)
        if args.export and sim.frames:
            from .viewer import export
            export(sim, args.output)
        print(json.dumps(summary, indent=2))
