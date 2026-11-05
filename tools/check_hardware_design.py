"""Pin and documentation consistency checks, NOT an electrical/hardware test."""
import csv
import itertools
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]


def check():
    c=json.loads((ROOT/'config/hardware_v1.json').read_text(encoding='utf-8'))
    docs=ROOT/'docs/hardware'
    motor=c['motor_control']
    sensors=c['sensors_phase3']
    controls=[*motor['left'].values(),*motor['right'].values(),motor['stby']]
    outputs=controls+[sensors[s]['trig'] for s in ('front','left','right')]
    inputs=[sensors[s]['echo'] for s in ('front','left','right')]
    reserved=list(c['reserved_gpio'].values())
    pins=outputs+inputs+reserved
    assert len(pins)==len(set(pins)), 'GPIO collision'
    valid=set(range(0,20))|{21,22,23,25,26,27,32,33,34,35,36,39}
    assert set(pins)<=valid, 'Invalid/unexposed pin for selected classic ESP32 board'
    forbidden={0,2,5,12,15,1,3,6,7,8,9,10,11}
    assert not (set(pins)&forbidden), 'Boot, UART programming or flash pin selected'
    assert not (set(outputs)&{34,35,36,39}), 'Input-only pin assigned output'
    assert len(controls)==7
    assert c['power']['tb6612_vcc_v']==3.3 and c['power']['motor_target_v']==5.0
    assert c['power']['logic_target_v']==5.0

    divider=sensors['echo_divider']
    top,bottom=divider['top_ohm'],divider['bottom_ohm']
    tol=divider['resistor_tolerance_fraction']
    assert top>0 and bottom>0 and 0<tol<1
    nominal=divider['echo_design_high_v']*bottom/(top+bottom)
    corners=[vin*rb/(rt+rb) for vin,rt,rb in itertools.product(
        [c['power']['logic_accept_min_v'],divider['echo_design_high_max_v']],
        [top*(1-tol),top*(1+tol)],[bottom*(1-tol),bottom*(1+tol)])]
    assert max(corners)<3.3, 'Divider exceeds selected nominal GPIO supply'
    assert min(corners)>0.75*3.3, 'Divider below classic ESP32 nominal VIH requirement'

    buf=sensors['trigger_buffer']
    expected={'front':(1,2,3),'left':(4,5,6),'right':(10,9,8)}
    for side,pinout in expected.items():
        assert tuple(buf[side][key] for key in ('oe','a','y'))==pinout
    assert (buf['vcc_pin'],buf['gnd_pin'])==(14,7)
    assert tuple(buf['unused'].values())==(13,12,11)

    with (docs/'gpio.csv').open(encoding='utf-8-sig',newline='') as stream:
        rows=list(csv.DictReader(stream))
    assert {int(r['gpio']) for r in rows}==set(pins)
    assert len(rows)==len(pins)
    assert {int(r['gpio']) for r in rows if r['direction']=='OUTPUT'}==set(outputs)
    assert {int(r['gpio']) for r in rows if r['direction']=='INPUT'}==set(inputs)
    for name in ('power.svg','signals.svg'):
        ET.parse(docs/name)
    for name in ('assembly-checklist.csv','measurement-log.csv'):
        with (docs/name).open(encoding='utf-8-sig',newline='') as stream:
            assert len(list(csv.DictReader(stream)))>0

    assert c['battery']['bms_model'] is None
    assert c['power']['fuse_current_a'] is None
    assert c['power']['motor_stall_current_a'] is None
    assert c['firmware_requirements_proposed']['implemented'] is False
    report={
        'scope':'Static consistency and divider calculation only; no electrical test or motor simulation',
        'pin_count_including_reservations':len(pins),
        'unique_pins':True,
        'output_capabilities_and_boot_pin_exclusion':True,
        'gpio_csv_matches_config':True,
        'ahct125_dip_pinout_matches_reference':True,
        'svg_xml_valid':True,
        'echo_gpio_nominal_v':round(nominal,6),
        'echo_gpio_corner_min_v':round(min(corners),6),
        'echo_gpio_corner_max_v':round(max(corners),6),
        'measurement_or_hardware_claim':False,
        'open_items':['Exact BMS/holder/cell and charger model','Motor stall/start/load and thermal budget',
                      'Fuse/switch/wire ratings','Loaded buck performance and voltage transients','Firmware M7 not implemented']
    }
    (docs/'design-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f"Pin/doc checks passed: {len(pins)} unique GPIO assignments, echo calculation {min(corners):.3f}..{max(corners):.3f} V.")
    print('No electrical testing or firmware execution performed.')


if __name__=='__main__':
    check()
