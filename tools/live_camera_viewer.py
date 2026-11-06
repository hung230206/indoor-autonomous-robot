"""Read-only live RGB/YOLO monitor, separate from Webots and navigation."""
import argparse
import io
import json
import os
from pathlib import Path
import time
import tkinter as tk
from PIL import Image, ImageTk


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    root=tk.Tk()
    root.title('Robot vision - Camera RGB + YOLO live | '+args.output.name)
    root.geometry('1060x600')
    root.configure(bg='#111827')
    onboard=os.environ.get('ROBOT_CAMERA_MODE')=='ego'
    tk.Label(root,text='ROBOT VISION | '+('Camera trước trên xe' if onboard else 'Camera trên cao (bản cũ)'),fg='white',bg='#111827',font=('Segoe UI',17,'bold')).pack(pady=(12,2))
    tk.Label(root,text='RGB trên xe → YOLO → chân vật thể + cự ly → A* / FSM. Pose: encoder + IMU mô phỏng.' if onboard else 'Camera cố định bên ngoài xe. Khung và confidence do YOLO dự đoán.',fg='#cbd5e1',bg='#111827',font=('Segoe UI',10)).pack()
    panels=tk.Frame(root,bg='#111827'); panels.pack(pady=8)
    images=[]
    for col,title in enumerate(('CAMERA RGB | Anh goc','YOLO | Nhan dien box')):
        frame=tk.Frame(panels,bg='#1e293b'); frame.grid(row=0,column=col,padx=6)
        tk.Label(frame,text=title,fg='white',bg='#1e293b',font=('Segoe UI',12,'bold')).pack(pady=5)
        label=tk.Label(frame,text='Dang cho camera / khoi dong YOLO...',bg='#0b1220',fg='white',width=68,height=23)
        label.pack(); images.append(label)
    camera_text=tk.StringVar(value='Dang cho khung hinh dau tien...')
    navigation_text=tk.StringVar(value='FSM: waiting')
    tk.Label(root,textvariable=camera_text,fg='#67e8f9',bg='#111827',font=('Segoe UI',11)).pack(pady=3)
    tk.Label(root,textvariable=navigation_text,fg='white',bg='#111827',font=('Segoe UI',11)).pack()
    tk.Label(root,text='Reload World trong Webots de chay lai. Dong cua so nay khong dung robot.',fg='#94a3b8',bg='#111827',font=('Segoe UI',10)).pack(pady=6)
    versions={}

    def refresh():
        for label,name in zip(images,('live-raw.jpg','live-yolo.jpg')):
            path=args.output/name
            try:
                stamp=path.stat().st_mtime_ns
                if versions.get(name)!=stamp:
                    pixels=Image.open(io.BytesIO(path.read_bytes())).convert('RGB').resize((500,375))
                    photo=ImageTk.PhotoImage(pixels)
                    label.configure(image=photo,text='',width=500,height=375)
                    label.image=photo
                    versions[name]=stamp
            except (OSError,ValueError):
                pass
        try:
            data=json.loads((args.output/'live-camera.json').read_text(encoding='utf-8'))
            age=time.time()-(args.output/'live-camera.json').stat().st_mtime
            suffix=' | Khung cu / mo phong tam dung' if age>3 else ' | LIVE'
            confidences=', '.join(f"{d['confidence']:.2f}" for d in data['detections']) or '-'
            camera_text.set(f"Camera t={data['timestamp']:.2f}s | {len(data['detections'])} box | confidence: {confidences} | inference {data['latency_ms']:.0f} ms{suffix}")
        except (OSError,ValueError,KeyError):
            pass
        try:
            nav=json.loads((args.output/'live-navigation.json').read_text(encoding='utf-8'))
            navigation_text.set(f"FSM: {nav['state']} | A*: {nav['plans']} | Vision cells: {nav['vision_cells']} | Pose: ({nav['x']:.2f}, {nav['y']:.2f}) m | {nav['reason']}")
        except (OSError,ValueError,KeyError):
            pass
        root.after(150,refresh)
    refresh()
    root.mainloop()


if __name__=='__main__':
    main()
