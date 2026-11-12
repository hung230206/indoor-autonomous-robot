"""Standalone validator, also bundled into the Colab dataset archive."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path


def validate_dataset(directory, minimum_class_images=1):
    from PIL import Image
    directory=Path(directory)
    manifest=json.loads((directory/'manifest.json').read_text(encoding='utf-8'))
    assert manifest['classes']==['box','furniture_leg','slipper'],'Wrong class order'
    seen_seeds=set(); hashes={}; image_files=set(); label_files=set()
    stats={s:{'images':0,'negative_images':0,'instances':Counter(),'class_images':Counter(),
              'bottom_clipped_instances':0} for s in ('train','val','test')}
    for item in manifest['scenes']:
        split=item['split']; stats[split]['images']+=1
        assert item['seed'] not in seen_seeds,'Duplicate scene seed'
        seen_seeds.add(item['seed'])
        for key,expected,collection in (('image','image_sha256',image_files),('label','label_sha256',label_files)):
            path=directory/item[key]
            assert path.resolve().is_relative_to(directory.resolve()),'Unsafe manifest path'
            assert str(item[key]).startswith(key+'s/'+split+'/'),'Split/path mismatch'
            assert item[key] not in collection,'Duplicate file entry'
            collection.add(item[key])
            assert hashlib.sha256(path.read_bytes()).hexdigest()==item[expected],f'Hash mismatch: {path}'
        digest=item['image_sha256']
        with Image.open(directory/item['image']) as pixels:
            assert pixels.size==(manifest['camera']['camera_width'],manifest['camera']['camera_height']),'Wrong image size'
            pixels.verify()
        assert digest not in hashes or hashes[digest]==split,'Identical image across splits'
        hashes[digest]=split
        lines=(directory/item['label']).read_text(encoding='utf-8').splitlines()
        assert len(lines)==len(item['annotations']),'Annotation count mismatch'
        if not lines:stats[split]['negative_images']+=1
        classes=set()
        for line,annotation in zip(lines,item['annotations']):
            values=list(map(float,line.split()))
            assert len(values)==5 and all(math.isfinite(v) for v in values),'Bad label'
            cid,cx,cy,w,h=values
            assert cid==int(cid) and 0<=cid<len(manifest['classes']),'Bad class'
            assert 0<w<=1 and 0<h<=1,'Bad dimensions'
            assert -1e-7<=cx-w/2<cx+w/2<=1+1e-7,'Out-of-image x'
            assert -1e-7<=cy-h/2<cy+h/2<=1+1e-7,'Out-of-image y'
            assert int(cid)==annotation['class_id'],'Class/manifest mismatch'
            x0,y0,x1,y1=annotation['xyxy']
            width=manifest['camera']['camera_width'];height=manifest['camera']['camera_height']
            expected=((x0+x1)/(2*width),(y0+y1)/(2*height),(x1-x0)/width,(y1-y0)/height)
            assert all(abs(a-b)<1e-7 for a,b in zip(values[1:],expected)),'Box/manifest mismatch'
            label=manifest['classes'][int(cid)]
            stats[split]['instances'][label]+=1; classes.add(label)
            stats[split]['bottom_clipped_instances']+=int(annotation['bottom_clipped'])
        for label in classes:stats[split]['class_images'][label]+=1
    assert image_files=={p.relative_to(directory).as_posix() for p in (directory/'images').rglob('*.png')},'Unlisted images'
    assert label_files=={p.relative_to(directory).as_posix() for p in (directory/'labels').rglob('*.txt')},'Unlisted labels'
    for split,values in stats.items():
        assert values['images']>0,'Empty split'
        for label in manifest['classes']:
            assert values['class_images'][label]>=minimum_class_images,f'Too few {label} images in {split}'
    return {'passed':True,'total_images':len(manifest['scenes']),'classes':manifest['classes'],
            'splits':stats,'scope':'Integrity and annotation checks, not detector performance or real-world accuracy'}


def contact_sheet(directory, output):
    from PIL import Image,ImageDraw
    directory=Path(directory)
    manifest=json.loads((directory/'manifest.json').read_text(encoding='utf-8'))
    selected=[]
    for split in ('train','val','test'):
        for cid in (0,1,2,None):
            item=next((s for s in manifest['scenes'] if s['split']==split and
                       ((not s['annotations']) if cid is None else any(a['class_id']==cid for a in s['annotations']))),None)
            if item:selected.append(item)
    colors=('#ffbb33','#00ee88','#33ccff')
    sheet=Image.new('RGB',(4*400,3*330),'#111827'); draw=ImageDraw.Draw(sheet)
    for index,item in enumerate(selected):
        tile=Image.open(directory/item['image']).convert('RGB')
        painter=ImageDraw.Draw(tile)
        for a in item['annotations']:
            color=colors[a['class_id']];bbox=a['xyxy']
            painter.rectangle(bbox,outline=color,width=2)
            painter.text((bbox[0],max(0,bbox[1]-12)),manifest['classes'][a['class_id']],fill=color,stroke_width=1,stroke_fill='black')
        x=(index%4)*400;y=(index//4)*330
        sheet.paste(tile.resize((400,300)),(x,y))
        draw.text((x+5,y+306),f"{item['split']} / {item['id']:05d} / {len(item['annotations'])} labels",fill='white')
    sheet.save(output)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('dataset',type=Path)
    parser.add_argument('--minimum-class-images',type=int,default=1)
    parser.add_argument('--sheet',type=Path)
    args=parser.parse_args()
    report=validate_dataset(args.dataset,args.minimum_class_images)
    (args.dataset/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    if args.sheet:contact_sheet(args.dataset,args.sheet)
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
