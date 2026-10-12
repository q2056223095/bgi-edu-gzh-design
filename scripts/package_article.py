#!/usr/bin/env python3
"""Bundle current article, preview and verified original media only."""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path

def package(path):
    path=Path(path).resolve();base=path.parent
    media=json.loads(path.with_suffix('.media.json').read_text())
    files=[path,path.with_name(path.stem+'_本地图片.html'),path.with_suffix('.media.json'),path.with_suffix('.checks.json'),path.with_name(path.stem+'_待核对.txt')]
    preview=path.with_name(path.stem+'_预览.html')
    if preview.exists():files.append(preview)
    for x in media:
        p=(base/x['path']).resolve()
        if not p.is_relative_to(base):raise ValueError('素材路径超出目录')
        if hashlib.sha256(p.read_bytes()).hexdigest()!=x['sha256']:raise ValueError('素材内容改变：'+x['path'])
        files.append(p)
    out=path.with_name(path.stem+'_素材包.zip')
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        for f in dict.fromkeys(files):z.write(f,f.relative_to(base))
        z.writestr('使用说明.txt','浏览器打开预览HTML，点击复制到公众号，再粘贴。\n预览图片显示不等于公众号接收成功，缺图时按media.json顺序补传原图。\n实际发布前核对日期、权益、二维码标签及待核对清单。\n')
    print('已生成：'+str(out));return out
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('html');a=ap.parse_args();package(a.html)
