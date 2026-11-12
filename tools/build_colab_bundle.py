"""Build a verified portable dataset ZIP and a GPU Colab notebook."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import textwrap
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from validate_object_dataset import validate_dataset


def notebook(zip_name,zip_sha):
    cells=[]
    def md(source):cells.append({'cell_type':'markdown','id':f'cell-{len(cells):02d}','metadata':{},'source':textwrap.dedent(source).strip().splitlines(keepends=True)})
    def code(source):cells.append({'cell_type':'code','id':f'cell-{len(cells):02d}','execution_count':None,'metadata':{},'outputs':[],
                                  'source':textwrap.dedent(source).strip().splitlines(keepends=True)})
    md('''
    # Train YOLO11n: hộp, chân bàn/ghế và dép

    **Dữ liệu tổng hợp từ camera trước gắn trên xe trong Webots**, 1.200 cảnh độc lập:
    840 train / 180 validation / 180 test. Lớp: `box`, `furniture_leg`, `slipper`.
    Mỗi chân bàn/ghế có nhãn riêng; mặt bàn/ghế là vật che khuất, không phải nhãn chân.

    1. Chọn **Runtime → Change runtime type → GPU** (T4 nếu có).
    2. Chạy các ô theo thứ tự. Bộ dữ liệu sẽ được tải tự động từ repo.
    3. Sau train, chạy ô test một lần, rồi tải ZIP kết quả gồm `best.pt`, `last.pt`, metrics và biểu đồ.

    Chưa có model mới được train trước trong notebook này. GPU Colab phụ thuộc tài nguyên/quota tài khoản.
    [Colab FAQ](https://research.google.com/colaboratory/faq.html) ·
    [Ultralytics train](https://docs.ultralytics.com/modes/train/)
    ''')
    code('''
    import sys, subprocess
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', 'ultralytics==8.4.202'])
    import torch, ultralytics
    assert torch.cuda.is_available(), 'Chưa có GPU: chọn Runtime > Change runtime type > GPU rồi chạy lại.'
    print('GPU:', torch.cuda.get_device_name(0))
    print('Torch:', torch.__version__, '| CUDA:', torch.version.cuda, '| Ultralytics:', ultralytics.__version__)
    ''')
    md(f'''
    ## Lấy bộ dữ liệu đã chuẩn bị

    Mặc định tải file **`{zip_name}`** từ repo project rồi kiểm tra SHA-256 trước khi giải nén.
    Không cần upload thủ công. Nếu mạng GitHub gặp lỗi, đổi `USE_LOCAL_UPLOAD=True` và chọn ZIP trên máy.
    Chưa cần gán nhãn lại.
    ''')
    code(f'''
    from google.colab import files
    from pathlib import Path, PurePosixPath
    import hashlib, zipfile, json, urllib.request
    USE_LOCAL_UPLOAD = False
    if USE_LOCAL_UPLOAD:
        uploaded = files.upload()
        zip_names = [name for name in uploaded if name.endswith('.zip')]
        assert len(zip_names) == 1, 'Chọn đúng một ZIP dữ liệu.'
        archive_path = Path(zip_names[0])
    else:
        archive_path = Path('/content/{zip_name}')
        urllib.request.urlretrieve('https://raw.githubusercontent.com/hung230206/indoor-autonomous-robot/main/artifacts/training/{zip_name}', archive_path)
    DATASET_ZIP_SHA256 = '{zip_sha}'
    assert hashlib.sha256(archive_path.read_bytes()).hexdigest() == DATASET_ZIP_SHA256, 'Sai ZIP hoặc file bị hỏng.'
    extract_root = Path('/content/robot_objects_v1')
    assert not extract_root.exists(), 'Thư mục dữ liệu đã tồn tại. Dùng runtime mới để tránh trộn dữ liệu.'
    with zipfile.ZipFile(archive_path) as archive:
        for name in archive.namelist():
            part = PurePosixPath(name)
            assert not part.is_absolute() and '..' not in part.parts, 'Đường dẫn ZIP không hợp lệ.'
        archive.extractall(extract_root)
    data_root = extract_root / 'dataset'
    print('Dataset:', data_root)
    ''')
    code('''
    sys.path.insert(0, str(data_root))
    from validate_object_dataset import validate_dataset
    from train_objects import train_model, evaluate_model, export_results
    integrity = validate_dataset(data_root, minimum_class_images=30)
    print(json.dumps(integrity, indent=2))
    # Rewrite only the portable YAML root for this Colab VM.
    from ultralytics.utils import YAML
    dataset_config = YAML.load(data_root / 'dataset.yaml')
    dataset_config['path'] = str(data_root)
    YAML.save(data_root / 'dataset.yaml', dataset_config)
    ''')
    md('''
    ## Huấn luyện trên GPU

    Mặc định 60 epoch, ảnh 640, batch 16, YOLO11n COCO, seed 42. Ảnh 640 giữ chi tiết chân mảnh tốt hơn
    ảnh 320 của bản cũ nhưng cần đo lại tốc độ khi tích hợp. Chọn checkpoint theo validation, không theo test.

    `SAVE_TO_DRIVE=False` lưu trong máy ảo; nhớ tải kết quả trước khi mất phiên. Có thể bật `True` để giữ
    checkpoint trên Drive: Colab sẽ yêu cầu **bạn** cấp quyền. Thay batch thành 8 nếu GPU báo hết bộ nhớ.
    ''')
    code('''
    from datetime import datetime, timezone
    SAVE_TO_DRIVE = False
    EPOCHS, IMAGE_SIZE, BATCH = 60, 640, 16
    if SAVE_TO_DRIVE:
        from google.colab import drive
        drive.mount('/content/drive')
        project = Path('/content/drive/MyDrive/robot_yolo_training')
    else:
        project = Path('/content/robot_yolo_training')
    run_name = 'objects_v1_' + datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    run = train_model(data_root, project, run_name, epochs=EPOCHS,
                      imgsz=IMAGE_SIZE, batch=BATCH, device='0')
    provenance_path = run / 'training-provenance.json'
    provenance = json.loads(provenance_path.read_text())
    provenance['dataset_zip_sha256'] = DATASET_ZIP_SHA256
    provenance_path.write_text(json.dumps(provenance, indent=2))
    print('Checkpoint được chọn từ validation:', run / 'weights/best.pt')
    ''')
    code('''
    from IPython.display import Image, display
    if (run / 'results.png').exists():
        display(Image(filename=str(run / 'results.png')))
    ''')
    md('''
    ## Đánh giá test sau khi đã chọn checkpoint

    Ô này đánh giá 180 cảnh test và ghi precision, recall, mAP50, mAP50–95 cho từng lớp.
    Chỉ dùng test để báo kết quả cuối; nếu điều chỉnh theo lỗi test, lần sau cần một tập giữ lại mới.
    Chỉ số này **không so ngang** mAP của bộ box cũ, không chứng minh xe tránh được mọi vật và không phải ảnh thật.
    ''')
    code('''
    report = evaluate_model(data_root, run, device='0', imgsz=IMAGE_SIZE, batch=BATCH, split='test')
    print(json.dumps(report, indent=2))
    if (run / 'test_evaluation/confusion_matrix.png').exists():
        display(Image(filename=str(run / 'test_evaluation/confusion_matrix.png')))
    ''')
    md('''
    ## Lưu kết quả về máy

    Giữ cả ZIP kết quả, không chỉ `best.pt`. Sau đó đưa ZIP về project để kiểm tra đúng thứ tự lớp,
    tích hợp detector đa lớp và chạy lại các ca bàn/ghế/dép. Notebook không tự thay model demo.
    Phép chiếu mép dưới bbox vẫn có thể sai khi chân bị che/cắt; train detector chưa tự sửa được giới hạn đó.
    ''')
    code('''
    result_zip = export_results(run, Path('/content') / (run.name + '_results.zip'))
    print('Kết quả:', result_zip)
    files.download(str(result_zip))
    ''')
    return {'cells':cells,'metadata':{'colab':{'name':'train_robot_objects.ipynb','provenance':[]},
            'accelerator':'GPU','kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},
            'language_info':{'name':'python'}},'nbformat':4,'nbformat_minor':5}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('dataset',type=Path)
    parser.add_argument('--output',type=Path,default=ROOT/'artifacts/training')
    parser.add_argument('--reuse-archive',action='store_true',help='Verify an existing identical ZIP, regenerate only notebook/metadata')
    args=parser.parse_args()
    validation=validate_dataset(args.dataset,minimum_class_images=30)
    args.output.mkdir(parents=True,exist_ok=True)
    archive_path=args.output/'robot_objects_v1_dataset.zip'
    entries=[]
    for sub in ('images','labels'):
        entries.extend((path,'dataset/'+path.relative_to(args.dataset).as_posix())
                       for path in sorted((args.dataset/sub).rglob('*')) if path.is_file())
    entries.extend((args.dataset/name,'dataset/'+name) for name in ('manifest.json','dataset.yaml','validation.json','labels-preview.jpg'))
    entries.extend(((ROOT/'training/train_objects.py','dataset/train_objects.py'),
                    (ROOT/'tools/validate_object_dataset.py','dataset/validate_object_dataset.py')))
    if args.reuse_archive:
        with zipfile.ZipFile(archive_path) as archive:
            assert set(archive.namelist())=={name for _,name in entries},'Archive contents changed'
            for path,name in entries:
                assert archive.read(name)==path.read_bytes(),'Archive/source mismatch: '+name
    else:
        # Exclusive creation preserves the dataset the user has already downloaded.
        with zipfile.ZipFile(archive_path,'x',zipfile.ZIP_DEFLATED) as archive:
            for path,name in entries:archive.write(path,name)
    sha=hashlib.sha256(archive_path.read_bytes()).hexdigest()
    destination=ROOT/'notebooks/train_robot_objects.ipynb';destination.parent.mkdir(exist_ok=True)
    document=notebook(archive_path.name,sha)
    # All cells are ordinary Python so syntax can be checked without a Colab login.
    for i,cell in enumerate(document['cells']):
        if cell['cell_type']=='code':compile(''.join(cell['source']),f'colab_cell_{i}','exec')
    destination.write_text(json.dumps(document,ensure_ascii=False,indent=2),encoding='utf-8',newline='\n')
    report={'archive':archive_path.name,'sha256':sha,'bytes':archive_path.stat().st_size,
            'notebook':'notebooks/train_robot_objects.ipynb','validation':validation,
            'status':'prepared and syntax-checked; full GPU training not executed',
            'colab_url':'https://colab.research.google.com/github/hung230206/indoor-autonomous-robot/blob/main/notebooks/train_robot_objects.ipynb'}
    (args.output/'package.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    (args.output/(archive_path.name+'.sha256')).write_text(sha+'  '+archive_path.name+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
