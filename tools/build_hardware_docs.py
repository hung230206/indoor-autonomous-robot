"""Generate wiring diagrams and empty bench forms from the shared pin config."""
import csv
import json
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/hardware"


class Diagram:
    def __init__(self, width, height, title, subtitle):
        self.items = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
                      f'<title>{escape(title)}</title><desc>{escape(subtitle)}</desc>',
                      '<defs><marker id="arrow" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto"><path d="M0 0L9 4.5L0 9" fill="#3466ad"/></marker></defs>',
                      '<style>text{font-family:"Segoe UI",Arial,sans-serif;fill:#203047}.title{font-size:32px;font-weight:700}.sub{font-size:18px;fill:#54667b}.head{font-size:22px;font-weight:700}.body{font-size:18px}.small{font-size:16px}</style>',
                      f'<rect width="{width}" height="{height}" fill="#f8fafc"/>']
        self.text(40,55,title,"title")
        self.text(40,88,subtitle,"sub")

    def text(self,x,y,text,kind="body",anchor="start"):
        self.items.append(f'<text x="{x}" y="{y}" class="{kind}" text-anchor="{anchor}">{escape(str(text))}</text>')

    def box(self,x,y,w,h,title,lines=(),fill="#ffffff"):
        self.items.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{fill}" stroke="#9fb2c9" stroke-width="1.5"/>')
        self.text(x+18,y+32,title,"head")
        for i,line in enumerate(lines):
            self.text(x+18,y+63+i*27,line)

    def line(self,points,color="#c43f48",width=3,arrow=False):
        coords=' '.join(f'{x},{y}' for x,y in points)
        extra=' marker-end="url(#arrow)"' if arrow else ''
        self.items.append(f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linejoin="round"{extra}/>')

    def dot(self,x,y,color="#c43f48"):
        self.items.append(f'<circle cx="{x}" cy="{y}" r="5" fill="{color}"/>')

    def save(self,name):
        (OUT/name).write_text('\n'.join(self.items)+"\n</svg>\n",encoding="utf-8")


def write_csv(name,header,rows):
    # Never overwrite a bench form that the user may already have filled in.
    if name in {'assembly-checklist.csv','measurement-log.csv'} and (OUT/name).exists():
        return
    with (OUT/name).open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.writer(stream)
        writer.writerow(header)
        writer.writerows(rows)


def build():
    c=json.loads((ROOT/'config/hardware_v1.json').read_text(encoding='utf-8'))
    OUT.mkdir(parents=True,exist_ok=True)
    motor=c['motor_control']
    controls=[('left',signal.upper(),pin) for signal,pin in motor['left'].items()]
    controls += [('right',signal.upper(),pin) for signal,pin in motor['right'].items()]
    controls.append(('enable','STBY',motor['stby']))
    rows=[[2,group,signal,pin,'OUTPUT',f'ESP32 GPIO{pin}',f'TB6612 {signal}','3.3 V','10k to GND','LOW at boot']
          for group,signal,pin in controls]
    for name in ('front','left','right'):
        sensor=c['sensors_phase3'][name]
        rows += [[3,name,'TRIG',sensor['trig'],'OUTPUT',f"ESP32 GPIO{sensor['trig']}",f'AHCT125 input -> {name} TRIG','3.3 V -> 5 V','10k to GND','Buffer as shown in wiring.md'],
                 [3,name,'ECHO',sensor['echo'],'INPUT',f'{name} ECHO -> 10k/15k divider',f"ESP32 GPIO{sensor['echo']}",'5 V -> 3.0 V nominal','15k divider bottom to GND','Never connect ECHO directly']]
    rows += [['future',name,'RESERVED',pin,'NOT_CONNECTED','','','','','No circuit implemented'] for name,pin in c['reserved_gpio'].items()]
    write_csv('gpio.csv',['phase','group','signal','gpio','direction','from','to','level','pull','notes'],rows)
    checklist=[
        ('P01','Before purchase','BMS/holder/cells','Exact BMS model and instructions; midpoint accessible; correct cell and charger chemistry'),
        ('P02','Before motor power','Motor/driver current','Stall/start/load data evaluated against driver, thermals and wiring; fuse rated'),
        ('M01','M6','Mechanical assembly','Wheels free, cables clear, chassis/axle/wheel dimensions measured'),
        ('E01','M6','Battery/BMS inspection','Polarity and B+/BM/B-/P+/P- checked against actual module; no B- load bypass'),
        ('E02','M6','Buck outputs without electronics','Both set to 5.00 V; separate OUT+; record no-load and load voltages'),
        ('E03','M6','USB power modes','One source into ESP32; no connection between laptop USB 5V and buck 5V'),
        ('F01','M7 pending firmware','Default boot/reset','Seven control signals LOW; STBY LOW before Wi-Fi and arming'),
        ('F02','M7 pending firmware','Left motor, wheels lifted','Low-duty short pulse, correct direction, current recorded, STOP checked'),
        ('F03','M7 pending firmware','Right motor, wheels lifted','Low-duty short pulse, correct direction, current recorded, STOP checked'),
        ('F04','M7 pending firmware','Two motors, wheels lifted','Forward/reverse/turn; rail sag and temperature recorded; stop before reversal'),
        ('F05','M7 pending firmware','Wi-Fi/client failure','Timeout drives PWM and STBY LOW; logical stop delay and mechanical coast measured'),
        ('F06','M7 pending firmware','Short floor test','All prior gates passed; low speed; manual power cut within reach; coast distance recorded'),
        ('S01','M11 later','Sensors','Echo dividers checked, TRIG buffer wired, sensor tests sequential with finite timeout')]
    write_csv('assembly-checklist.csv',['id','phase','check','acceptance','status','measurement_reference','notes'],
              [[*row,'NOT_RUN','',''] for row in checklist])
    checks=[('identity','BMS/holder/cell/charger model','Record exact models','text'),
            ('power','Cell C1 voltage','Within purchased-cell operating limits','V'),
            ('power','Cell C2 voltage','Within purchased-cell operating limits','V'),
            ('power','Pack and BMS P+/P- voltage','Correct polarity; record no-load and under-load','V'),
            ('power','5V_LOGIC, no load','5.00 target; 4.75..5.25 accepted DC','V'),
            ('power','5V_LOGIC, motor startup','4.75..5.25 accepted DC; inspect transients if possible','V'),
            ('power','5V_MOTOR, no load','5.00 target; initial 4.90..5.10','V'),
            ('power','5V_MOTOR, two motors','Record sag and assess driver operating range','V'),
            ('power','ESP32 3V3','Near 3.3; compare board/device specifications','V'),
            ('logic','STBY, reset/not armed','LOW','V'),
            ('motor','Left working/start/stall data','Working design target <=0.6 A; stall evaluated separately','A'),
            ('motor','Right working/start/stall data','Working design target <=0.6 A; stall evaluated separately','A'),
            ('thermal','Driver/buck temperature and ambient','Record load, duration and temperature; evaluate ratings','deg C'),
            ('safety','Last valid command to PWM/STBY off','Proposed watchdog 250 ms; measure actual scheduling delay','ms'),
            ('safety','STOP to mechanical rest / coast distance','Measure; no assumption of instant braking','s / m'),
            ('mechanical','Axle center spacing / wheel diameter / body','Measure real robot; update real-robot config later','m'),
            ('sensors later','Front/left/right divider HIGH','Nominal 3.00 with 5 V Echo; verify actual levels and pulses','V')]
    write_csv('measurement-log.csv',['date','phase','test_point','expected_or_method','measured','unit','result','notes'],
              [['',phase,point,expected,'',unit,'NOT_RUN',''] for phase,point,expected,unit in checks])

    d=Diagram(1520,1040,'Nguồn xe 2WD — bản thiết kế v1','Hai LM2596 cùng đầu vào, tách đầu ra 5 V. Đối chiếu model BMS trước khi đấu điện.')
    d.box(40,140,250,250,'Hộp pin 2S',fill='#fff5e8')
    for y,label in ((211,'C2 (+) → B+'),(256,'BM: C1 (+) / C2 (-)'),(301,'C1 (-) → B-'),(358,'Cần dây điểm giữa')):
        d.text(58,y,label)
    d.box(360,140,240,250,'BMS 2S',fill='#edf8f3')
    for y,label in ((211,'B+'),(256,'BM'),(301,'B-')):
        d.text(378,y,label)
    d.text(558,211,'P+')
    d.text(558,341,'P-')
    d.text(378,372,'Theo đúng module','small')
    for y in (205,250,295):
        d.line([(290,y),(360,y)],'#b07925',2)
    d.line([(600,205),(640,205)])
    d.box(640,180,80,55,'F1')
    d.line([(720,205),(760,205)])
    d.box(760,180,80,55,'S1')
    d.line([(840,205),(980,205)])
    d.dot(900,205)
    d.box(980,150,180,130,'LM2596 #1',('OUT+ = 5,00 V','5V_LOGIC','IN-/OUT-: GND'),fill='#fff1f2')
    d.line([(1160,205),(1230,205)])
    d.text(1180,185,'5 V','small')
    d.box(1230,150,250,205,'ESP32',('Micro-USB: VBUS/GND','Cáp nguồn 2 dây','Ngắt trước khi cắm PC','3V3 → VCC driver'),fill='#edf3ff')
    d.line([(900,205),(900,485),(980,485)])
    d.box(980,430,180,130,'LM2596 #2',('OUT+ = 5,00 V','5V_MOTOR','IN-/OUT-: GND'),fill='#fff1f2')
    d.line([(1160,485),(1205,485)])
    d.box(1205,460,75,55,'S2')
    d.line([(1280,485),(1320,485)])
    d.box(1320,430,160,225,'TB6612FNG',fill='#edf8f3')
    for y,label in ((491,'VM: 5 V'),(530,'GND: P- tải'),(576,'AO1/AO2'),(616,'BO1/BO2')):
        d.text(1338,y,label)
    d.line([(1440,355),(1440,405),(1400,405),(1400,430)],'#8154b6')
    d.text(1260,395,'3V3 từ ESP32','small')
    d.text(1412,423,'VCC','small')
    d.line([(600,335),(640,335),(640,740),(1480,740)],'#34465a',4)
    d.text(660,720,'GND_LOAD = P- bảo vệ; không nối thêm B- vào tải','head')
    for x,label in ((760,'Buck #1'),(1010,'Buck #2'),(1230,'ESP / driver'),(1430,'HC / buffer')):
        d.dot(x,740,'#34465a')
        d.line([(x,740),(x,762)],'#34465a',2)
        d.text(x,788,label,'small','middle')
    d.box(980,820,500,125,'Hai motor TT',('AO1/AO2 → motor trái; BO1/BO2 → motor phải','Hai đầu mỗi motor chỉ nối vào cặp ngõ ra driver'),fill='#edf3ff')
    d.line([(1480,570),(1500,570),(1500,855),(1480,855)],'#3466ad',2)
    d.line([(1480,610),(1510,610),(1510,890),(1480,890)],'#3466ad',2)
    d.box(40,820,880,160,'Ghi chú đấu nguồn',('F1: chọn sau khi biết dòng; S1: ngắt cả xe; S2: cắt nhánh VM.',
          '5V_LOGIC còn cấp HC-SR04 và buffer ở GĐ3, không lấy từ VM.',
          'Tụ gần driver: VCC 10 µF + 100 nF; VM 470 µF + 100 nF.',
          'Chỉnh buck khi chưa nối tải; không nối hai OUT+ với nhau.'),fill='#fff5e8')
    d.text(40,1012,'Sơ đồ chức năng theo tên chân, không phải PCB/pad map. Chưa mua, chưa lắp, chưa đo tải. Chi tiết: wiring.md.','small')
    d.save('power.svg')

    d=Diagram(1560,1170,'Tín hiệu ESP32 — motor và phần dành cho cảm biến','Mọi GND dùng chung phía P-. Chân GPIO là số IO, không phải số thứ tự header.')
    d.box(40,150,310,540,'TB6612FNG',('VCC = 3V3 ESP32','VM = 5V_MOTOR','AO → motor trái; BO → phải'),fill='#edf8f3')
    d.box(520,150,390,660,'NodeMCU-32S',(),fill='#edf3ff')
    for i,(group,signal,pin) in enumerate(controls):
        y=300+i*50
        d.text(310,y-10,signal,'body','end')
        d.line([(520,y),(350,y)],'#3466ad',2,True)
        d.text(540,y+6,f'GPIO{pin} → {signal}')
    d.text(58,650,'7 × 10 kΩ xuống GND','body')
    d.text(540,740,'GPIO33/36/22: dự phòng','body')
    d.text(540,775,'STBY luôn LOW trước khi RUN','small')
    d.box(1120,150,400,260,'AHCT125, chỉ GĐ3',('VCC14 = 5V_LOGIC, GND7','GPIO18 → 2(A) / 3(Y) → TRIG trước',
          'GPIO19 → 5(A) / 6(Y) → TRIG trái','GPIO21 → 9(A) / 8(Y) → TRIG phải','/OE 1,4,10 → GND; 10k ở mỗi A','Kênh 4: /OE13 → 5V; A12 → GND'),fill='#fff5e8')
    for i,name in enumerate(('front','left','right')):
        y=230+i*65
        pin=c['sensors_phase3'][name]['trig']
        d.text(925,y-10,f'GPIO{pin}','small')
        d.line([(910,y),(1120,y)],'#3466ad',2,True)
    d.box(1120,475,400,285,'HC-SR04 × 3, chỉ GĐ3',('VCC = 5V_LOGIC; GND chung','Mỗi Echo qua một bộ chia riêng','TRIG nhận từ buffer phía trên',
          'Trước: Echo → GPIO34','Trái: Echo → GPIO35','Phải: Echo → GPIO32'),fill='#edf8f3')
    for i,name in enumerate(('front','left','right')):
        y=570+i*70
        pin=c['sensors_phase3'][name]['echo']
        d.text(925,y-12,f'GPIO{pin}','small')
        d.line([(1120,y),(910,y)],'#3466ad',2,True)
        d.text(1000,y+23,'10k / 15k','small','middle')
    d.box(40,855,1480,250,'Mỗi đường Echo: bộ chia 10 kΩ / 15 kΩ, dung sai 1%',(),fill='#ffffff')
    d.text(90,957,'Echo 5 V')
    d.line([(205,950),(330,950)],'#b07925')
    d.box(330,925,170,60,'Rtop 10k')
    d.line([(500,950),(690,950),(870,950)],'#b07925')
    d.dot(690,950,'#b07925')
    d.text(900,957,'→ GPIO Echo: 3,00 V danh định')
    d.line([(690,950),(690,975)],'#34465a')
    d.items.append('<rect x="675" y="975" width="30" height="55" fill="#fff" stroke="#34465a" stroke-width="2"/>')
    d.line([(690,1030),(690,1045)],'#34465a')
    for offset,halfwidth in ((0,20),(7,13),(14,6)):
        d.line([(690-halfwidth,1045+offset),(690+halfwidth,1045+offset)],'#34465a',2)
    d.text(720,1014,'Rbottom 15k → GND_LOAD')
    d.text(90,1070,'Tối đa tính toán ≈3,18 V khi Echo 5,25 V và điện trở 1%. Cần kiểm chứng mức/xung thực tế.','small')
    d.text(40,1140,'Không nối Echo thẳng ESP32. Phần sensor/buffer chưa cần lắp ở GĐ2. Hướng dẫn đủ chân DIP và tụ nằm trong wiring.md.','small')
    d.save('signals.svg')
    print('Generated two SVG diagrams, GPIO CSV and two empty bench forms.')


if __name__=='__main__':
    build()
