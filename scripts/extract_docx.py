#!/usr/bin/env python3
"""Ordered DOCX → source JSON, readable Markdown, original media (stdlib)."""
import argparse
import hashlib
import json
import posixpath
import re
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET

NS = {'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
      'r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
      'a':'http://schemas.openxmlformats.org/drawingml/2006/main',
      'wp':'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing',
      'v':'urn:schemas-microsoft-com:vml'}
def q(name):
    p,n=name.split(':');return '{'+NS[p]+'}'+n

class Extractor:
    def __init__(self, z, output):
        self.z=z;self.output=output;self.warnings=[];self.counter=0;self.media={};self.rels={};self.styles={}
        if 'word/_rels/document.xml.rels' in z.namelist():
            for r in ET.fromstring(z.read('word/_rels/document.xml.rels')):
                self.rels[r.get('Id')] = dict(r.attrib)
        if 'word/styles.xml' in z.namelist():
            for s in ET.fromstring(z.read('word/styles.xml')).findall('w:style',NS):
                self.styles[s.get(q('w:styleId'))]=s
    def warn(self,msg):
        if msg not in self.warnings:self.warnings.append(msg)
    def heading(self,p):
        pp=p.find('w:pPr',NS)
        if pp is None:return None
        outline=pp.find('w:outlineLvl',NS)
        if outline is not None:
            level=int(outline.get(q('w:val'),'9'));return level+1 if level<6 else None
        sid=pp.find('w:pStyle',NS);sid=sid.get(q('w:val')) if sid is not None else None
        seen=set()
        while sid and sid not in seen:
            seen.add(sid);st=self.styles.get(sid)
            if st is None:break
            n=st.find('w:name',NS);name=n.get(q('w:val'),'') if n is not None else ''
            m=re.fullmatch(r'(?:heading|标题)\s*([1-6])',name,re.I)
            if m:return int(m[1])
            o=st.find('w:pPr/w:outlineLvl',NS)
            if o is not None:
                level=int(o.get(q('w:val'),'9'))
                if level<6:return level+1
            b=st.find('w:basedOn',NS);sid=b.get(q('w:val')) if b is not None else None
        return None
    def image(self,rid,alt='',href=None,width=None):
        rel=self.rels.get(rid,{})
        if not rel:self.warn('无法解析图片关系：'+str(rid));return {'text':'［图片关系缺失］'}
        if rel.get('TargetMode')=='External':return {'image':rel['Target'],'alt':alt,'href':href}
        path=posixpath.normpath(posixpath.join('word',rel.get('Target','')))
        if path not in self.z.namelist():self.warn('图片缺失：'+path);return {'text':'［图片缺失］'}
        raw=self.z.read(path);digest=hashlib.sha256(raw).hexdigest();ext=Path(path).suffix.lower()
        if digest not in self.media:
            filename=f'images/{len(self.media)+1:02d}-{digest[:10]}{ext}'
            dest=self.output.parent/filename;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
            self.media[digest]=filename
        mime={'.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.gif':'image/gif','.svg':'image/svg+xml','.webp':'image/webp'}.get(ext,'application/octet-stream')
        if mime=='application/octet-stream':self.warn('图片格式需转换为公众号可用格式：'+ext)
        item={'image':self.media[digest],'sha256':digest,'mime':mime,'alt':alt}
        if href:item['href']=href
        if width:item['width']=width
        return item
    def inlines(self,node,href=None,fmt=None):
        fmt=dict(fmt or {});items=[]
        if node.tag==q('w:hyperlink'):
            rel=self.rels.get(node.get(q('r:id')),{});href=rel.get('Target')
            if not href:self.warn('内部书签链接需人工核对，保留文字')
        if node.tag==q('w:r'):
            rp=node.find('w:rPr',NS)
            if rp is not None:
                for prop,key in [('b','bold'),('i','italic'),('u','underline')]:
                    el=rp.find('w:'+prop,NS)
                    if el is not None:fmt[key]=el.get(q('w:val'),'1') not in ('0','false','none')
        if node.tag==q('w:t'):
            x={'text':node.text or '',**fmt}
            if href:x['href']=href
            return [x]
        if node.tag in (q('w:br'),q('w:cr'),q('w:tab')):return [{'text':'\t' if node.tag==q('w:tab') else '\n',**fmt}]
        if node.tag in (q('w:drawing'),q('w:pict')):
            dp=node.find('.//wp:docPr',NS);alt=dp.get('descr','') if dp is not None else ''
            ext=node.find('.//wp:extent',NS);width=None
            if ext is not None:width=round(int(ext.get('cx','0'))/9525,2) or None
            for bl in node.findall('.//a:blip',NS):
                items.append(self.image(bl.get(q('r:embed')) or bl.get(q('r:link')),alt,href,width))
            for bl in node.findall('.//v:imagedata',NS):items.append(self.image(bl.get(q('r:id')),alt,href,width))
            if node.find('.//w:txbxContent',NS) is not None:
                self.warn('文本框按XML文字顺序提取，需核对原图文布局')
                for tx in node.findall('.//w:txbxContent',NS):items.extend(self.inlines(tx,href,fmt))
            if not items:self.warn('绘图／图表未识别为图片，需人工提取')
            return items
        if node.tag==q('w:del'):self.warn('稿件包含修订删除，按当前可见正文处理，需核对修订版本');return []
        if node.tag==q('w:ins'):self.warn('稿件包含修订插入，需核对修订版本')
        if node.tag in (q('w:object'),q('w:altChunk')):self.warn('嵌入对象／外部内容无法完整提取，需人工补齐')
        if node.tag in (q('w:pPr'),q('w:rPr')):return []
        for child in node:items.extend(self.inlines(child,href,fmt))
        return items
    def blocks(self,parent):
        out=[]
        for el in parent:
            if el.tag==q('w:p'):
                content=self.inlines(el)
                if not any(x.get('text','').strip() or 'image' in x for x in content):continue
                self.counter+=1;b={'id':f'b{self.counter:04d}','type':'paragraph','inlines':content}
                h=self.heading(el)
                if h:b.update(type='heading',level=h)
                elif el.find('w:pPr/w:numPr',NS) is not None:
                    b.update(type='list_item');self.warn('列表编号仅保留项目顺序；原Word编号样式需人工核对')
                out.append(b)
            elif el.tag==q('w:tbl'):
                self.counter+=1;b={'id':f'b{self.counter:04d}','type':'table','rows':[]};active={}
                for tr in el.findall('w:tr',NS):
                    row=[];col=0;next_active={}
                    for tc in tr.findall('w:tc',NS):
                        gs=tc.find('w:tcPr/w:gridSpan',NS);span=int(gs.get(q('w:val'),'1')) if gs is not None else 1
                        vm=tc.find('w:tcPr/w:vMerge',NS);inner=self.blocks(tc)
                        if vm is not None and vm.get(q('w:val'))!='restart' and col in active:
                            origin=active[col];origin['rowspan']+=1;next_active[col]=origin
                            if inner:
                                origin['blocks'].extend(inner);self.warn('纵向合并延续格含内容，已合并保留，需检查阅读顺序')
                        else:
                            cell={'blocks':inner,'colspan':span,'rowspan':1};row.append(cell)
                            if vm is not None:next_active[col]=cell
                        col+=span
                    b['rows'].append(row);active=next_active
                out.append(b)
            elif el.tag in (q('w:sectPr'),q('w:tcPr'),q('w:bookmarkStart'),q('w:bookmarkEnd')):continue
            elif el.tag==q('w:sdt'):
                child=el.find('w:sdtContent',NS)
                if child is not None:out.extend(self.blocks(child))
            else:
                self.warn('非标准正文结构：'+el.tag.split('}')[-1]+'；需人工核对')
                content=self.inlines(el)
                if content:self.counter+=1;out.append({'id':f'b{self.counter:04d}','type':'paragraph','inlines':content})
        return out

def md_inline(items):
    out=[]
    for x in items:
        if 'image' in x:t='!['+x.get('alt','')+']('+x['image']+')'
        else:
            t=x.get('text','')
            if x.get('bold'):t='**'+t+'**'
            if x.get('italic'):t='*'+t+'*'
            if x.get('underline'):t='<u>'+t+'</u>'
        if x.get('href'):t='['+t+']('+x['href']+')'
        out.append(t)
    return ''.join(out)
def markdown(blocks):
    out=[]
    for b in blocks:
        if b['type']=='table':
            for c in b['rows']:
                out.append('| '+' | '.join(markdown(x['blocks']).strip().replace('\n','<br>').replace('|','\\|') for x in c)+' |')
            out.append('')
        else:
            prefix='#'*b.get('level',0)+' ' if b['type']=='heading' else '- ' if b['type']=='list_item' else ''
            out.extend([prefix+md_inline(b['inlines']),''])
    return '\n'.join(out)
def extract(path,out):
    out=Path(out);out.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(path) as z:
        e=Extractor(z,out);body=ET.fromstring(z.read('word/document.xml')).find('w:body',NS)
        blocks=e.blocks(body)
        for name in z.namelist():
            if re.match(r'word/(header|footer|footnotes|endnotes)\d*\.xml$',name):
                extra=ET.fromstring(z.read(name))
                meaningful=[el for el in extra if int(el.get(q('w:id'),'1'))>0 and any((t.text or '').strip() for t in el.iter(q('w:t')))]
                if meaningful:e.warn('有页眉页脚／脚注内容，需判断是否需纳入正文：'+name)
    data={'schema':'bgi-edu-article/1','source_name':Path(path).name,'source_sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest(),'blocks':blocks,'warnings':e.warnings}
    out.write_text(markdown(blocks),encoding='utf-8');src=out.with_suffix('.source.json');src.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'已提取 {len(blocks)} 个正文块，{len(e.media)} 张原图；{len(e.warnings)} 项需核对。JSON：{src}')
    return data
def main():
    ap=argparse.ArgumentParser();ap.add_argument('input');ap.add_argument('-o','--output');a=ap.parse_args()
    extract(a.input,a.output or str(Path(a.input).with_suffix('.md')))
if __name__=='__main__':main()
