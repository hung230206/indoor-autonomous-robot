"""Matplotlib UI and reproducible 2D evidence. Imported only when requested."""
import math
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.patches import Circle, Rectangle
from matplotlib.widgets import Button
from .models import Command
from .simulation import Simulation, rect_distance


def draw(ax, sim, frame_index=None, show_inflation=True):
    ax.clear()
    c, nav = sim.config, sim.navigator
    frame = sim.frames[frame_index] if sim.frames and frame_index is not None else (sim.frames[-1] if sim.frames else None)
    now = frame.time if frame else sim.now
    pose = frame.pose if frame else sim.world.pose(now)
    if show_inflation:
        for cell in sim.grid.blocked:
            x, y = cell
            ax.add_patch(Rectangle((x * c.resolution_m, y * c.resolution_m), c.resolution_m, c.resolution_m,
                                   facecolor="#e8edf3", edgecolor="none"))
    for rect in sim.scenario["obstacles"]:
        ax.add_patch(Rectangle((rect[0], rect[1]), rect[2]-rect[0], rect[3]-rect[1], color="#33465a"))
    for event in sim.scenario.get("spawn", []):
        if event["at_s"] <= now:
            rect = event["rect"]
            ax.add_patch(Rectangle((rect[0], rect[1]), rect[2]-rect[0], rect[3]-rect[1], color="#ed8752"))
    for cell, expiry in sim.grid.dynamic.items():
        if now < expiry and show_inflation:
            x, y = cell
            ax.add_patch(Rectangle((x*c.resolution_m, y*c.resolution_m), c.resolution_m, c.resolution_m,
                                   fill=False, edgecolor="#d84545", linewidth=1))
    plans = [p for p in nav.plans if p["time_s"] <= now]
    if plans:
        initial = plans[0]["waypoints"]
        if initial:
            ax.plot(*zip(*initial), "--", color="#a5aeb9", label="Initial A*", linewidth=1.4)
        current = plans[-1]["waypoints"]
        if current:
            ax.plot(*zip(*current), color="#2767c4", label="Current A*", linewidth=2)
    history = sim.frames[:frame_index+1] if frame_index is not None else sim.frames
    if history:
        ax.plot([f.pose.x for f in history], [f.pose.y for f in history], color="#15977d", label="Trajectory", linewidth=2)
    ax.add_patch(Circle((pose.x, pose.y), c.radius_m, color="#15977d", alpha=.8))
    ax.arrow(pose.x, pose.y, .15*math.cos(pose.theta), .15*math.sin(pose.theta), width=.012, color="#142f3d")
    ax.plot(*sim.scenario["start"][:2], "o", color="#15977d", markersize=7, label="Start")
    ax.plot(*nav.goal, "*", color="#c83a59", markersize=17, label="Goal")
    state = frame.state if frame else nav.state
    ax.set_title(f"{sim.scenario['name']} | {state} | {now:.1f} s", loc="left", fontweight="bold", pad=15)
    ax.set(xlim=(0,c.width_m), ylim=(0,c.height_m), xlabel="x (m)", ylabel="y (m)")
    ax.set_aspect("equal")
    ax.set_xticks([i*.2 for i in range(round(c.width_m/.2)+1)])
    ax.set_yticks([i*.2 for i in range(round(c.height_m/.2)+1)])
    ax.grid(alpha=.2)
    ax.legend(loc="upper center", bbox_to_anchor=(.5,-.17), ncol=5, fontsize=8, frameon=False)


def export(sim, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    plt.switch_backend("Agg")
    fig, ax = plt.subplots(figsize=(9,6), dpi=100)
    fig.subplots_adjust(bottom=.2)
    draw(ax, sim)
    fig.savefig(directory / "trajectory.png", dpi=160)
    # Replay the map visible at each timestamp, not the final discovered map.
    # Geometry/paths/trajectory remain faithful; hide final inflation during playback.
    stride = max(1, round(.16 / sim.config.dt_s))
    indices = list(range(0, len(sim.frames), stride))
    if indices[-1] != len(sim.frames)-1:
        indices.append(len(sim.frames)-1)
    animation = FuncAnimation(fig, lambda i: draw(ax, sim, i, show_inflation=False), frames=indices, interval=80)
    animation.save(directory / "demo.gif", writer=PillowWriter(fps=12))
    plt.close(fig)


def interactive(sim):
    fig, ax = plt.subplots(figsize=(10,7))
    fig.subplots_adjust(bottom=.25)
    holder = {"sim": sim, "running": True}
    buttons = []

    def pause(_):
        holder["running"] = not holder["running"]

    def stop(_):
        current = holder["sim"]
        current.navigator.stop(current.now)
        current.world.command(Command())

    def reset(_):
        holder["sim"] = Simulation(sim.config, sim.scenario)
        holder["running"] = True

    for x, title, callback in ((.18,"Pause / Resume",pause),(.42,"STOP",stop),(.66,"Reset",reset)):
        button = Button(fig.add_axes([x,.05,.18,.055]), title)
        button.on_clicked(callback)
        buttons.append(button)

    def click(event):
        current = holder["sim"]
        if event.inaxes != ax or event.xdata is None:
            return
        if event.button == 1:
            goal = (event.xdata, event.ydata)
            if current.grid.free(current.grid.cell(*goal)):
                current.navigator.goal = goal
                current.scenario["goal"] = list(goal)
                current.navigator.start(current.now)
                holder["running"] = True
        elif event.button == 3:
            rect = [event.xdata-.1,event.ydata-.1,event.xdata+.1,event.ydata+.1]
            if rect_distance(current.world.x,current.world.y,rect) <= current.config.clearance_m:
                return
            # Add to world only: discovery must come through sensors.
            current.world.obstacles.append(tuple(rect))
            current.scenario.setdefault("spawn",[]).append({"at_s":current.now,"rect":rect})
            current.world.spawned.add(len(current.scenario["spawn"])-1)

    fig.canvas.mpl_connect("button_press_event", click)
    fig.text(.5,.16,"Left click: new goal | Right click: add an unknown obstacle", ha="center", fontsize=10)

    def update(_):
        current = holder["sim"]
        if holder["running"] and not current.done:
            for _ in range(4):
                if not current.done:
                    current.tick()
        draw(ax,current)

    animation = FuncAnimation(fig,update,interval=64,cache_frame_data=False)
    plt.show()
    holder["sim"].world.command(Command())
    return holder["sim"]
