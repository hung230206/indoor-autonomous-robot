"""Build the measured Vietnamese report. Run with Codex bundled Python/docx."""
import json
from pathlib import Path
from docx import Document
from docx.shared import Cm,Pt,RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'experiments/evidence/yolo_v1'


def main():
    data=json.loads((E/'report-data.json').read_text(encoding='utf-8'))
    metrics=data['model']['metrics']
    runs=data['navigation']; reference=data['range_reference']
    document=Document()
    section=document.sections[0]
    section.page_width=Cm(21); section.page_height=Cm(29.7)
    section.top_margin=Cm(1.9); section.bottom_margin=Cm(1.9)
    section.left_margin=Cm(2.1); section.right_margin=Cm(2.1)
    normal=document.styles['Normal']; normal.font.name='Times New Roman'; normal.font.size=Pt(12)
    normal.paragraph_format.space_after=Pt(6); normal.paragraph_format.line_spacing=1.12
    normal.paragraph_format.widow_control=True
    for name,size in [('Title',20),('Heading 1',15),('Heading 2',13)]:
        style=document.styles[name]; style.font.name='Times New Roman'; style.font.size=Pt(size)
        style.font.color.rgb=RGBColor.from_string('000000' if name=='Title' else '244767')
        style.font.bold=True
        fonts=style.element.get_or_add_rPr().get_or_add_rFonts()
        for attribute in list(fonts.attrib):
            if attribute.endswith('Theme') or attribute.endswith('theme'):
                del fonts.attrib[attribute]
        for script in ('ascii','hAnsi','eastAsia','cs'):
            fonts.set(qn('w:'+script),'Times New Roman')
    # The bundled default DOCX template contains a title paragraph border.
    for border in list(document.styles.element.iter(qn('w:pBdr'))):
        border.getparent().remove(border)
    document.styles['Title'].paragraph_format.space_after=Pt(8)
    for name in ('Heading 1','Heading 2'):
        document.styles[name].paragraph_format.space_before=Pt(8)
        document.styles[name].paragraph_format.space_after=Pt(5)
    foot=section.footer.paragraphs[0]; foot.alignment=WD_ALIGN_PARAGRAPH.RIGHT
    foot.add_run('Trang ').font.size=Pt(10)
    field=OxmlElement('w:fldSimple'); field.set(qn('w:instr'),'PAGE'); foot._p.append(field)
    document.core_properties.title='Báo cáo mô phỏng robot tự hành có nhận diện YOLO'
    document.core_properties.subject='Giai đoạn 1 mở rộng thị giác máy tính'
    document.core_properties.author='Dự án indoor-autonomous-robot'

    def p(text): return document.add_paragraph(text)
    def h(text): return document.add_heading(text,1)
    def page(): document.add_page_break()
    def table(headers,rows,widths=None):
        t=document.add_table(rows=1,cols=len(headers)); t.style='Table Grid'
        for cell,value in zip(t.rows[0].cells,headers):
            cell.text=str(value)
            shade=OxmlElement('w:shd'); shade.set(qn('w:fill'),'244767'); cell._tc.get_or_add_tcPr().append(shade)
            for run in cell.paragraphs[0].runs:
                run.font.bold=True; run.font.color.rgb=RGBColor(255,255,255)
        t.rows[0]._tr.get_or_add_trPr().append(OxmlElement('w:tblHeader'))
        for row in rows:
            cells=t.add_row().cells
            for cell,value in zip(cells,row): cell.text=str(value)
        for row in t.rows:
            row._tr.get_or_add_trPr().append(OxmlElement('w:cantSplit'))
            for cell in row.cells:
                for para in cell.paragraphs:
                    para.paragraph_format.space_after=Pt(3); para.paragraph_format.line_spacing=1.02
                    for run in para.runs: run.font.size=Pt(10.5)
        return t
    def picture(path,width,caption):
        para=document.add_paragraph(); para.alignment=WD_ALIGN_PARAGRAPH.CENTER
        para.paragraph_format.keep_with_next=True
        para.add_run().add_picture(str(path),width=Cm(width))
        cap=document.add_paragraph(caption); cap.alignment=WD_ALIGN_PARAGRAPH.CENTER
        for run in cap.runs: run.font.size=Pt(10); run.font.italic=True
    def code(text):
        para=document.add_paragraph(text)
        for run in para.runs: run.font.name='Consolas'; run.font.size=Pt(9)

    document.add_paragraph('Báo cáo mô phỏng robot tự hành có nhận diện YOLO','Title')
    p('Niên luận cơ sở ngành Khoa học máy tính\nDự án indoor-autonomous-robot · Ngày 06/11/2026')
    h('1 Mục tiêu và phạm vi')
    p('Dự án xây dựng robot di động hai bánh chủ động đi từ vị trí A đến đích B trong khu vực sàn đã biết. Khi xuất hiện vật cản mới, robot dừng, cập nhật bản đồ và lập lại đường nếu còn lối an toàn. Phiên bản mở rộng bổ sung nhận diện hộp bằng YOLO để tạo thông tin vật cản từ ảnh camera trên cao.')
    p('Kết quả hiện tại gồm mô phỏng động học 2D, mô phỏng vật lý Webots và thử nghiệm thị giác trên dữ liệu tổng hợp. Chưa có xe thật, định vị ArUco thực nghiệm hoặc firmware ESP32. Các kết luận chỉ áp dụng trong phạm vi các kịch bản đã chạy.')
    picture(E/'architecture.png',16.5,'Hình 1. Luồng xử lý của chế độ YOLO trong mô phỏng.')
    h('2 Phân tách thành phần')
    table(['Thành phần','Vai trò và dữ liệu'],[
        ('Camera và YOLO','Camera RGB cố định; YOLO11n trả khung bao, nhãn box và độ tin cậy.'),
        ('Bản đồ và A*','Occupancy grid tĩnh/động; lớp thị giác riêng; mở rộng vật cản và tìm đường.'),
        ('FSM và điều khiển','Quản lý trạng thái; bám waypoint; kiểm tra dữ liệu và gửi lệnh hai bánh.'),
        ('Adapter Webots','Lấy pose lý tưởng, số đo khoảng cách và đổi m/s sang rad/s cho motor.')])
    p('Trong chế độ thị giác, cảm biến khoảng cách vẫn được giữ để dừng nguy hiểm nhưng không dựng bản đồ. Tọa độ vật cản mới đi vào lớp thị giác phải bắt nguồn từ kết quả YOLO, không lấy trực tiếp tọa độ hộp trong kịch bản.')

    page(); h('3 Bản đồ và thuật toán điều hướng')
    p('Sàn mô phỏng rộng 3 × 2 m được chia thành 30 × 20 ô, mỗi ô 0,10 m. Hệ tọa độ dùng mét, x tăng sang phải, y tăng lên trên; góc hướng ngược chiều kim đồng hồ từ trục +x. Robot dài 0,18 m và rộng 0,15 m là giả định hình học ban đầu.')
    p('A* hoạt động trên lưới 8 hướng, dùng heuristic octile và không cho phép cắt góc qua chướng ngại vật. Trước khi tìm đường, ô vật cản được mở rộng theo đường tròn bao thân xe khoảng 0,117 m và biên an toàn 0,04 m; biên sàn cũng được xét. Không tìm được đường dẫn đến NO_PATH và lệnh bánh bằng 0.')
    p('Bộ bám waypoint tính sai số hướng và khoảng cách đến điểm kế tiếp. Robot quay tại chỗ nếu sai số hướng còn lớn, sau đó tiến và giảm tốc gần điểm. Vận tốc tiến giới hạn 0,16 m/s, tốc độ quay 1,8 rad/s và tốc độ tiếp tuyến từng bánh 0,24 m/s. Bản hiện tại chưa triển khai Pure Pursuit hoặc PID đầy đủ.')
    h('4 Máy trạng thái hữu hạn')
    table(['Trạng thái','Điều kiện hoặc hành vi chính'],[
        ('IDLE / LOCALIZING','Chờ START, kiểm tra dữ liệu pose; pose hiện lấy từ Supervisor.'),
        ('PLANNING','Lập đường ban đầu bằng A*; chưa ra lệnh di chuyển trong chu kỳ này.'),
        ('FOLLOWING','Bám waypoint khi lộ trình và dữ liệu còn hợp lệ.'),
        ('OBSTACLE_STOP','Đường bị chặn; trả lệnh dừng trước khi lập lại đường.'),
        ('REPLANNING','Tìm đường mới từ pose hiện tại đến đích.'),
        ('GOAL_REACHED','Sai số vị trí không quá 4,5 cm; hai lệnh bánh bằng 0.'),
        ('NO_PATH','Không có lối trên bản đồ hiện tại; giữ đứng yên.'),
        ('SAFE_STOP / TIMEOUT','Dừng do dữ liệu lỗi/cũ, khoảng cách nguy hiểm, STOP hoặc hết thời gian.')])
    p('Lịch sử chuyển trạng thái được lưu trong events.json. Mất ảnh mới quá 0,65 giây mô phỏng cũng dẫn đến SAFE_STOP. Dừng có chốt; hệ thống không tự bỏ qua lỗi rồi tiếp tục chạy bằng dữ liệu cũ.')

    page(); h('5 Dữ liệu và huấn luyện nhận diện')
    p('Sử dụng YOLO11n khởi tạo từ trọng số COCO rồi fine-tune một lớp box. Lớp hộp của project không có sẵn trong danh sách COCO; vì vậy cần dữ liệu và nhãn riêng [2, 3]. Camera Webots xuất ảnh RGB 640 × 480 từ độ cao 3,4 m, nhìn thẳng xuống. Tập tổng hợp thay đổi vị trí, kích thước, chiều cao và màu hộp, màu sàn, vị trí và hướng xe; có cả cảnh không có hộp.')
    split=data['dataset']['splits']
    table(['Tập','Số ảnh','Số hộp có nhãn'],[(k,split[k]['images'],split[k]['instances']) for k in ('train','val','test')])
    p('Mỗi cảnh được sinh độc lập theo seed; 240 ảnh có 240 SHA-256 khác nhau. Nhãn được tính từ phép chiếu tám đỉnh hình hộp chỉ ở bước tạo dữ liệu. Không chia các khung liền kề của một cảnh sang nhiều tập. Tuy nhiên, các tập vẫn cùng kiểu render và camera, nên chưa đánh giá được khả năng chuyển sang ảnh thật.')
    p('Huấn luyện 30 epoch trên CPU, kích thước đầu vào 320, batch 8, freeze 10 lớp đầu, seed 42. Có biến đổi màu, lật ảnh, xoay và mosaic. Tham số thực lưu trong training-args.yaml; seed không bảo đảm kết quả bit-identical giữa các môi trường.')
    picture(E/'training-curves.png',16,'Hình 2. Đường cong validation và loss huấn luyện, lấy từ training-results.csv.')
    h('6 Kết quả trên tập test độc lập')
    table(['Chỉ số do Ultralytics trả về','Giá trị'],[
        ('Precision',f"{metrics['metrics/precision(B)']*100:.2f}%"),
        ('Recall',f"{metrics['metrics/recall(B)']*100:.2f}%"),
        ('mAP50',f"{metrics['metrics/mAP50(B)']*100:.2f}%"),
        ('mAP50–95',f"{metrics['metrics/mAP50-95(B)']*100:.2f}%")])
    p('Đây là chỉ số phát hiện hộp trên 40 ảnh tổng hợp, không phải tỷ lệ robot đến đích. Các chỉ số được lấy từ val(split="test"); ngưỡng confidence khi vận hành được đặt riêng ở 0,5.')

    page(); h('7 Từ bounding box đến bản đồ')
    p('Bộ chiếu sử dụng hình học camera cố định đã biết để đổi pixel thành tọa độ mặt sàn. Bốn góc khung bao được chiếu xuống sàn, thêm padding 3 cm, rasterize thành ô occupancy rồi inflate theo kích thước xe. Khung bao không phải footprint sàn chính xác; sai số và che khuất có thể làm vùng ước lượng thiếu hoặc quá rộng.')
    p('Mỗi ô cần được thấy trong hai ảnh có timestamp khác nhau liên tiếp mới xác nhận. Detection trùng trong cùng ảnh không được tính hai lần. Lớp thị giác giữ ô 2 giây sau lần xác nhận cuối; kiểm tra nhãn, confidence, kích thước ảnh, tọa độ và độ mới của gói dữ liệu trước khi cập nhật.')
    h('8 Kết quả tích hợp trong Webots')
    table(['Kịch bản','Kết quả','Thời gian (s)','Lần A*'],[
        (label,r['state'],f"{r['time_s']:.3f}",r['plans']) for label,r in zip(
            ['Hộp ngoài tầm đo ban đầu','Hộp chặn tuyến ban đầu','Sàn không có hộp','Mất camera có chủ đích'],runs)])
    p('Cả bốn ca đúng kỳ vọng: ba ca đến đích, một ca mất camera chuyển SAFE_STOP. Không ghi nhận va chạm theo phép kiểm tra hình học hoặc tâm xe đi vào ô cấm đã inflate trong các lượt này. Số lần A* gồm lần đầu và các lần lập lại.')
    h('9 Đối chứng trên cùng ca hộp xa')
    table(['Đại lượng','Bản cảm biến','Bản YOLO'],[
        ('Dừng đầu để lập lại đường (s)',f"{reference['first_obstacle_stop_s']:.3f}",f"{runs[0]['first_obstacle_stop_s']:.3f}"),
        ('Thời gian đến đích (s)',f"{reference['time_s']:.3f}",f"{runs[0]['time_s']:.3f}"),
        ('Tổng số lần A*',reference['plans'],runs[0]['plans']),
        ('Va chạm ghi nhận',0,0)])
    p('Camera quan sát toàn sàn nên trong ca này có thể phát hiện hộp trước khi nó vào tầm ba tia khoảng cách. Một ca đối chứng chưa đủ kết luận YOLO luôn tốt hơn. Cần lặp nhiều bố trí và điều kiện để so sánh độ tin cậy, thời gian, quãng đường và độ trễ.')
    p('Sau thay đổi, 10/10 ca Webots nền vẫn đúng kỳ vọng: 8 đến đích và 2 NO_PATH. Bộ kiểm thử mã nguồn có 23 test qua, bao gồm A*, FSM/an toàn, quy đổi tọa độ, xác nhận ô thị giác, gói phát lại, ảnh sai kích thước và dữ liệu cũ.')

    page(); h('10 Minh họa nhận diện trong khi điều hướng')
    picture(E/'navigation/yolo_far_box/first-detection.jpg',15,'Hình 3. Kết quả YOLO trên ảnh RGB camera Webots trong ca hộp xa.')
    p('Khung bao và độ tin cậy trên hình do mô hình sinh từ ảnh camera. Video yolo-camera.mp4 lưu chuỗi ảnh đã nhận diện; webots.mp4 ghi mô phỏng vật lý. Detections.jsonl, camera-calibration.json, map_vision.csv và log FSM cho phép đối chiếu đường đi với đầu vào thị giác.')
    h('11 Giới hạn của kết quả')
    timing=data['inference_wall_time_ms']
    p(f"Trong lượt quay ca hộp xa, thời gian suy luận đo bằng đồng hồ thực ở lần gọi đầu là {timing['first_call']:.0f} ms; median sau lần đầu khoảng {timing['median_after_first']:.1f} ms. Lần gọi đầu có khởi tạo/warm-up. Đây là phép đo trên CPU trong phiên chạy này, không phải bảo đảm thời gian thực.")
    p('Webots đồng bộ các controller, nên suy luận chậm làm mô phỏng chạy chậm theo đồng hồ thực. Thử mất gói camera chứng minh luật chuyển trạng thái trong mô phỏng; chưa chứng minh xe thật dừng an toàn khi laptop treo. ESP32 phải có watchdog độc lập khi triển khai phần cứng.')
    p('Mô hình mới học hộp trong cảnh tổng hợp, chưa kiểm tra chân ghế, người, che khuất phức tạp, ánh sáng thật hoặc camera rung/trễ. Robot vẫn dùng pose Supervisor lý tưởng; chưa có định vị camera thật. Ba cảm biến là tia lý tưởng và không mô phỏng đầy đủ HC-SR04. Không suy rộng thành khả năng tránh mọi vật cản.')
    h('12 Công việc tiếp theo')
    p('Thu và gán nhãn ảnh từ điện thoại đúng góc đặt dự kiến; chia tập theo phiên quay/khu vực để tránh rò rỉ giữa các khung gần nhau. Hiệu chuẩn camera thực, đánh giá sai số vùng cản theo mét và kiểm thử mất dấu. Lặp các cấu hình cảm biến, thị giác và kết hợp trên nhiều seed; sau đó mới tích hợp với xe thật theo thiết kế nguồn/GPIO đã chuẩn bị.')

    page(); h('13 Tái lập và vị trí sản phẩm')
    p('Mã nguồn đã tách phần nhận diện, quy đổi bản đồ và điều phối. Lõi mô phỏng cũ không yêu cầu cài YOLO. Môi trường thử: Python '+data['environment']['python']+', Ultralytics '+data['environment']['ultralytics']+', Torch '+data['environment']['torch']+', OpenCV '+data['environment']['opencv']+'.')
    table(['Thành phần','Vị trí trong repo'],[
        ('Detector và phép chiếu','src/robot_nav/vision.py'),
        ('Camera và tạo dữ liệu','src/robot_nav/webots_vision.py'),
        ('FSM và tích hợp Webots','src/robot_nav/navigation.py; webots_adapter.py'),
        ('Cấu hình và ca thử','config/vision.json; config/vision_scenarios.json'),
        ('Checkpoint và chỉ số test','models/yolo_box/'),
        ('Ảnh, video, log và số liệu','experiments/evidence/yolo_v1/'),
        ('Hướng dẫn đầy đủ','docs/yolo.md')])
    p('Chạy từ thư mục gốc project sau khi cài requirements-yolo.txt vào môi trường riêng:')
    code('.venv-yolo\\Scripts\\python.exe tools/run_webots.py --scenario yolo_far_box --yolo')
    code('python -m unittest discover -s tests -v')
    p('Tập dữ liệu có thể tái tạo bằng tools/yolo_workflow.py collect; lệnh train huấn luyện và đánh giá trên test. Manifest lưu seed, nhãn hình học và hash ảnh; SHA256.txt xác định checkpoint đã dùng. Không dùng kết quả tập test để lựa chọn các phiên bản tiếp theo mà vẫn gọi đó là tập kiểm tra chưa thấy.')
    h('14 Tài liệu tham khảo')
    references=[
        '[1] Mã Trường Thành, Đỗ Thanh Nghị, Phạm Nguyên Khang, Nguyễn Hữu Hòa (2014). Tiếp cận mô hình máy học cho điều khiển Robot Pioneer P3-DX bám sát đối tượng. Hội thảo quốc gia lần thứ XVII. Tài liệu nền do người dùng cung cấp.',
        '[2] Ultralytics. YOLO11 và Object Detection. https://docs.ultralytics.com/models/yolo11/ ; https://docs.ultralytics.com/tasks/detect/',
        '[3] Ultralytics. COCO dataset configuration. https://github.com/ultralytics/ultralytics/blob/main/ultralytics/cfg/datasets/coco.yaml',
        '[4] Cyberbotics. Webots R2025a Reference Manual: Camera, Supervisor và Emitter/Receiver. https://cyberbotics.com/doc/reference/camera',
        '[5] Mã nguồn, cấu hình và bằng chứng thực nghiệm của project. https://github.com/hung230206/indoor-autonomous-robot'
    ]
    for ref in references:
        para=p(ref)
        for run in para.runs: run.font.size=Pt(10.5)
    p('Đề tài kế thừa hướng phản hồi thị giác của tài liệu nền [1] và chuyển sang điều hướng đến đích trên bản đồ biết trước. Phần mở rộng sử dụng YOLO có sẵn, tạo dữ liệu, fine-tune và tích hợp; chưa đề xuất kiến trúc YOLO mới hoặc cải tiến trực tiếp CamShift.')
    output=ROOT/'reports/Bao_cao_giai_doan_1_YOLO.docx'
    output.parent.mkdir(exist_ok=True)
    document.save(output)
    print(output)


if __name__=='__main__': main()
