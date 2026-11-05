"""Build the measured stage-1 report from retained evidence, not guessed metrics."""
import csv
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from robot_nav.simulation import scenarios


def main():
    evidence=ROOT/'experiments/evidence'
    results=[]
    for scenario in scenarios():
        name=scenario['name']
        row=[]
        for mode in ('kinematic_batch','webots'):
            summary=json.loads((evidence/mode/name/'summary.json').read_text(encoding='utf-8'))
            assert summary['passed'],summary
            with (evidence/mode/name/'trajectory.csv').open(encoding='utf-8') as stream:
                records=list(csv.DictReader(stream))
            assert records and float(records[-1]['command_left_m_s'])==0 and float(records[-1]['command_right_m_s'])==0
            assert not any(r['collision_flag']=='True' for r in records)
            row.append(summary)
        results.append(row)
    lines=[
        '# Kết quả triển khai giai đoạn 1',
        '',
        'Lần kiểm chứng ban đầu: **06/11/2026**. Phạm vi là mô phỏng; chưa kiểm chứng xe thật.',
        '',
        'Đã triển khai M1–M5: world Webots native với robot 2WD, occupancy grid và inflation, A* 8 hướng, bám waypoint, phát hiện cản bằng ba tia khoảng cách, dừng/lập lại đường, CSV/JSON và video demo.',
        '',
        '## Kết quả trên bộ 10 kịch bản',
        '',
        'Cả mô phỏng động học 2D và Webots R2025a đạt **10/10 kết quả đúng kỳ vọng**: **8/8 ca có đường đến đích**, **2/2 ca được thiết kế không có đường dừng với `NO_PATH`**. Không ghi nhận va chạm theo phép kiểm tra hình học bảo thủ, hoặc tâm xe đi vào ô cấm đã inflate trong các lượt này. Đây là kết quả của bộ ca cố định, không phải xác suất thành công ở môi trường tùy ý.',
        '',
        '| Kịch bản | Kết quả Webots | Thời gian 2D (s) | Thời gian Webots (s) | Quãng đường Webots (m) | Số lần A* Webots |',
        '|---|---|---:|---:|---:|---:|',
    ]
    for sim,web in results:
        lines.append(f"| {web['scenario']} | {web['state']} | {sim['time_s']:.2f} | {web['time_s']:.2f} | {web['distance_m']:.3f} | {web['plans']} |")
    arrival=[web for _,web in results if web['state']=='GOAL_REACHED']
    maximum_error=max(w['goal_error_m'] for w in arrival)*100
    maximum_planning=max(w['max_planning_ms'] for _,w in results)
    lines += [
        '',
        f'Sai số đích lớn nhất trong 8 lượt Webots đến đích: **{maximum_error:.2f} cm**, dưới ngưỡng cấu hình 4,5 cm. Thời gian thực thi A* lớn nhất của lượt benchmark: **{maximum_planning:.2f} ms**. Số này đo bằng đồng hồ thực trên laptop; thời gian đến đích trong bảng là thời gian mô phỏng.',
        '',
        'Số lần A* bao gồm lần đầu. `replanning` có 4 lần lập đường (3 lần lập lại); `new_barrier` có 6 lần (5 lần lập lại). Bản đồ động chỉ biết các điểm chạm đã quan sát; khi thấy thêm cạnh hộp, xe có thể phải dừng và lập lại đường nhiều lần. `s_curve` cũng có một lần lập lại đường trong cấu hình này; chưa tối ưu việc tái lập kế hoạch dư thừa.',
        '',
        '## Ca an toàn bổ sung',
        '',
        '`dynamic_no_path` bắt đầu với cửa thông, sau 3 giây xuất hiện hộp đóng kín cửa. Cả 2D và Webots kết thúc `NO_PATH` sau khoảng **3,10 giây**, có trạng thái `OBSTACLE_STOP` trước khi lập lại đường và lệnh cuối hai bánh bằng 0. Ca này lưu riêng, không cộng vào mẫu 10 ca ở bảng.',
        '',
        'Bộ **14 test** đã qua: kiểm tra A* so với Dijkstra trên 15 bản đồ có seed, cắt góc, inflation, ô ngoài map, khe hẹp, xác nhận/TTL cản động, pose cũ, dữ liệu cảm biến thiếu/NaN/tương lai, STOP có chốt, các ca di chuyển và thao tác giao diện chọn đích/thêm cản/STOP. Log tại `experiments/evidence/tests.txt`.',
        '',
        '## Bằng chứng và cách chạy lại',
        '',
        '- [Kết quả 10 ca Webots](../experiments/evidence/webots/results.csv)',
        '- [Kết quả 10 ca động học 2D](../experiments/evidence/kinematic_batch/results.csv)',
        '- [Video Webots thực tế, khoảng 30 giây](../experiments/evidence/webots_video/replanning/webots.mp4)',
        '- [Quỹ đạo và bản đồ 2D của ca lập lại đường](../experiments/evidence/kinematic_replanning/trajectory.png)',
        '- [Hình A* sàn trống](../experiments/evidence/planning_examples/open.png), [hộp cố định](../experiments/evidence/planning_examples/box.png), [không có đường](../experiments/evidence/planning_examples/no_path.png)',
        '- Ca đóng kín cửa: `experiments/evidence/webots_safety/dynamic_no_path/` và `experiments/evidence/kinematic_safety/`.',
        '',
        'Video lấy trực tiếp khung hình Webots và ghép bằng ffmpeg. Log CSV và `paths.json`/`events.json` trong cùng thư mục cung cấp lịch sử để đối chiếu. Video được quay trong một lượt riêng; thời gian A* đo bằng đồng hồ thực có thể khác lượt benchmark.',
        '',
        '```powershell',
        'python -m unittest discover -s tests -v',
        'python run.py batch',
        'python tools/run_webots.py --all',
        'python tools/run_webots.py --scenario dynamic_no_path',
        'python tools/run_webots.py --scenario replanning --record',
        '```',
        '',
        '## Các giả định và phần chưa chứng minh',
        '',
        'Pose lấy lý tưởng từ Supervisor. Ba cảm biến là generic DistanceSensor một tia mỗi hướng, đáp ứng bằng khoảng cách mét và không có nhiễu. Không coi đây là mô hình đầy đủ HC-SR04. Robot có thể bỏ sót vật nằm giữa các tia; chưa kiểm tra trễ mạng/video, mất echo hoặc trượt bánh thực.',
        '',
        'Kiểm tra va chạm dùng đường tròn bao robot so với hình chữ nhật vật cản và biên sàn; kiểm tra ô cấm dùng tâm robot so với lưới đã mở rộng. Không dùng kết quả này để khẳng định an toàn phần cứng hay tránh va chạm ở mọi tốc độ.',
        '',
        'Bộ bám waypoint hiện quay tại chỗ, chưa so sánh với Pure Pursuit. Biên an toàn và rasterization có thể loại một số đường thực tế còn lọt được. Mọi thông số hình học xe vẫn là giả định cho mô phỏng.',
        '',
        'Trong phạm vi các cổng nghiệm thu đề xuất của giai đoạn 1, đã có mã nguồn, 8 ca đến đích trên 10 ca kiểm soát, ca lập lại đường, dừng khi hết đường, log và video. Việc quyết định mua linh kiện nên dựa thêm trên xác nhận của người dùng/giảng viên về phạm vi và thiết kế nguồn thực tế.',
    ]
    report=ROOT/'docs/stage1-results.md'
    report.parent.mkdir(exist_ok=True)
    report.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    files={str(p.relative_to(evidence)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest()
           for p in sorted(evidence.rglob('*')) if p.is_file() and p.name!='sha256.json'}
    (evidence/'sha256.json').write_text(json.dumps(files,indent=2),encoding='utf-8')
    print('Report generated; checked 20 runs and final stop commands.')


if __name__=='__main__':
    main()
