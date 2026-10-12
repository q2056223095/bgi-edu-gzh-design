#!/usr/bin/env python3
"""Deterministic preservation checks + limited date consistency hints. No fact verification."""
import argparse
import base64
import datetime as dt
import hashlib
import html
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

class Content(HTMLParser):
    def __init__(self):super().__init__(convert_charrefs=True);self.text=[];self.images=[];self.links=[]
    def handle_data(self,s):self.text.append(s)
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='img':self.images.append(a.get('src',''))
        elif tag=='a':self.links.append(a.get('href',''))
        elif tag=='br':self.text.append('\n')

def walk(blocks):
    for b in blocks:
        if b['type']=='table':
            for row in b['rows']:
                for cell in row:yield from walk(cell['blocks'])
        else:
            for x in b.get('inlines',[]):yield x
def normalize(s):return re.sub(r'\s+','',s)
def business(text):
    notes=[];dates=[]
    pat=re.compile(r'(\d{4})[年/-](\d{1,2})[月/-](\d{1,2})日?(?:[（(](?:周|星期)([一二三四五六日天])[）)])?(?:\s*(\d{1,2})[：:](\d{2}))?')
    for m in pat.finditer(text):
        try:
            d=dt.datetime(int(m[1]),int(m[2]),int(m[3]),int(m[5] or 0),int(m[6] or 0))
        except ValueError:notes.append('日期／时间无效：'+m[0]);continue
        if m[4] and '一二三四五六日'[d.weekday()]!=m[4].replace('天','日'):
            notes.append(f'日期与星期不一致：{m[0]}，实际为周'+ '一二三四五六日'[d.weekday()])
        prefix=text[max(0,m.start()-45):m.start()]
        labels=list(re.finditer('报名截止|考试时间|开课时间|活动时间',prefix));label=labels[-1][0] if labels else None
        dates.append((d,label,m[0],bool(m[5])))
    deadlines=[x for x in dates if x[1]=='报名截止'];events=[x for x in dates if x[1] in ('考试时间','开课时间','活动时间')]
    for d in deadlines:
        for e in events:
            if (d[0] if d[3] and e[3] else d[0].date())>(e[0] if d[3] and e[3] else e[0].date()):notes.append('报名截止晚于所列考试／活动：'+d[2]+' ＞ '+e[2]+'；请按项目核对')
    if re.search(r'每年.*3月.*6月.*9月.*12月',text) and re.search(r'10月17日|10\.17',text):
        notes.append('年度常规考期与本次10月17日安排不同，请核对是否需要延期说明；原文未自动修改。')
    if re.search(r'\d{1,2}月\d{1,2}日',text) and not dates:
        notes.append('稿件日期缺少年份；星期和跨年顺序无法自动确定，请核对。')
    if re.search(r'17年',text) and re.search(r'20余年',text):notes.append('稿件同时出现17年与20余年，核对是否指同一讲师／同一经验范围。')
    return list(dict.fromkeys(notes))

def audit(data,fragment,base):
    p=Content();p.feed(fragment);items=list(walk(data['blocks']));errors=[]
    expected=normalize(''.join(x.get('text','') for x in items));actual=normalize(''.join(p.text))
    if expected!=actual:errors.append('正文文字或顺序与来源不一致（只忽略空白）。')
    originals=[x for x in items if 'image' in x]
    if len(originals)!=len(p.images):errors.append(f'图片数量不一致：来源{len(originals)}，输出{len(p.images)}')
    for idx,(x,url) in enumerate(zip(originals,p.images)):
        if urlsplit(x['image']).scheme:
            if url!=x['image']:errors.append(f'第{idx+1}张远程图片地址改变')
        else:
            src=Path(base)/x['image']
            if not src.is_file():errors.append('源图片缺失：'+x['image']);continue
            expected_hash=x.get('sha256') or hashlib.sha256(src.read_bytes()).hexdigest()
            if url.startswith('data:'):
                try:raw=base64.b64decode(url.split(',',1)[1],validate=True)
                except Exception:errors.append('内嵌图片数据无法解码');continue
                if hashlib.sha256(raw).hexdigest()!=expected_hash:errors.append(f'第{idx+1}张原图改变或错位')
            elif url!=x['image']:errors.append(f'第{idx+1}张本地图片路径改变')
    expected_links=[x['href'] for x in items if x.get('href')]
    # Repeated adjacent runs sharing one original link may render as repeated anchors.
    compress=lambda xs:[x for i,x in enumerate(xs) if i==0 or x!=xs[i-1]]
    if compress(expected_links)!=compress(p.links):errors.append('链接目标或相对顺序改变')
    return {'content_errors':errors,'business_notes':business(''.join(p.text)),
            'source_warnings':data.get('warnings',[]),'paragraph_blocks':len(data['blocks']),'image_occurrences':len(originals),
            'limitations':['未验证事实真伪、认证资质、权益和二维码归属。','HTML检查不等于公众号实际粘贴验证。','日期关联为文本邻近规则，可能需按项目人工排除。']}
def main():
    ap=argparse.ArgumentParser();ap.add_argument('source');ap.add_argument('html');ap.add_argument('-o','--output');a=ap.parse_args()
    src=Path(a.source);result=audit(json.loads(src.read_text()),Path(a.html).read_text(),src.parent)
    s=json.dumps(result,ensure_ascii=False,indent=2)
    if a.output:Path(a.output).write_text(s,encoding='utf-8')
    print(s);raise SystemExit(1 if result['content_errors'] else 0)
if __name__=='__main__':main()
