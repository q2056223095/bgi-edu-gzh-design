#!/usr/bin/env python3
"""Token-based WeChat fragment renderer. No network or third-party dependency."""
import argparse
import base64
import hashlib
import html
import json
import mimetypes
import re
from pathlib import Path
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]
AUTO_THEME={'course':'standard','exam':'standard','science':'friendly','joint':'professional','news':'professional','knowledge':'friendly'}
def safe_url(url,image=False):
    if not url or any(ord(c)<32 for c in url):return False
    parts=urlsplit(url)
    if parts.scheme:return parts.scheme.lower() in (('http','https') if image else ('http','https','mailto','tel'))
    return not url.startswith(('//','/','\\')) and '..' not in Path(url).parts

def parse_inline(text):
    """Small documented Markdown subset; raw HTML is escaped except <u>."""
    pattern=re.compile(r'!\[([^\]]*)\]\(([^)]+)\)|\[([^\]]+)\]\(([^)]+)\)|\*\*(.+?)\*\*|(?<!\*)\*([^*]+)\*|<u>(.*?)</u>|`([^`]+)`|https?://[^\s<>]+',re.S)
    out=[];last=0
    for m in pattern.finditer(text):
        if m.start()>last:out.append({'text':text[last:m.start()]})
        if m[2]:out.append({'image':m[2],'alt':m[1]})
        elif m[4]:
            for x in parse_inline(m[3]):x['href']=m[4];out.append(x)
        elif m[5]:
            for x in parse_inline(m[5]):x['bold']=True;out.append(x)
        elif m[6]:out.append({'text':m[6],'italic':True})
        elif m[7]:out.append({'text':m[7],'underline':True})
        elif m[8]:out.append({'text':m[8],'code':True})
        else:out.append({'text':m[0],'href':m[0]})
        last=m.end()
    if last<len(text):out.append({'text':text[last:]})
    return out
def parse_markdown(text):
    lines=text.splitlines();blocks=[];i=0
    def add(b):b['id']=f'b{len(blocks)+1:04d}';blocks.append(b)
    while i<len(lines):
        line=lines[i]
        if not line.strip():i+=1;continue
        if line.startswith('```'):
            language=line[3:];i+=1;body=[]
            while i<len(lines) and not lines[i].startswith('```'):body.append(lines[i]);i+=1
            add({'type':'code','language':language,'inlines':[{'text':'\n'.join(body),'code':True}]});i+=1;continue
        if line.lstrip().startswith('|') and i+1<len(lines) and re.match(r'\s*\|?\s*:?-{3,}',lines[i+1]):
            rows=[]
            while i<len(lines) and lines[i].lstrip().startswith('|'):
                if not re.fullmatch(r'[\s|:\-]+',lines[i]):
                    rows.append([{'blocks':[{'type':'paragraph','inlines':parse_inline(x.strip())}],'colspan':1,'rowspan':1} for x in re.split(r'(?<!\\)\|',lines[i].strip().strip('|'))])
                i+=1
            add({'type':'table','rows':rows});continue
        h=re.match(r'^(#{1,6})\s+(.*)',line)
        if h:add({'type':'heading','level':len(h[1]),'inlines':parse_inline(h[2])})
        elif re.match(r'^\s*(?:[-*+] |\d+[.)] )',line):
            add({'type':'list_item','inlines':parse_inline(line.strip())})
        elif line.startswith('> '):add({'type':'paragraph','role':'intro','inlines':parse_inline(line[2:])})
        else:
            add({'type':'paragraph','inlines':parse_inline(line)})
        i+=1
    return {'schema':'bgi-edu-article/1','blocks':blocks,'warnings':[]}
def plain(block):
    if block['type']=='table':return '\n'.join(plain(b) for row in block['rows'] for c in row for b in c['blocks'])
    return ''.join(x.get('text','') for x in block.get('inlines',[]))

class Renderer:
    def __init__(self,base,theme='standard',color=None,embed=True):
        self.base=Path(base);self.embed=embed;self.notes=[];self.components=json.loads((ROOT/'assets/components.json').read_text())
        brand=json.loads((ROOT/'assets/brand.json').read_text());self.tokens=brand['themes'][theme].copy()
        if color:
            if not re.fullmatch(r'#[0-9a-fA-F]{6}',color):raise ValueError('主色必须为六位HEX')
            rgb=[int(color[k:k+2],16) for k in (1,3,5)]
            mix=lambda white,scale: '#'+''.join(f'{round(v*scale+255*white):02X}' for v in rgb)
            self.tokens.update(primary=color.upper(),ink=mix(0,.55),tint=mix(.95,.05),border=mix(.65,.35))
        self.tokens['chapter_style']=self.fill(self.tokens['chapter_style'])
    def fill(self,s,**values):
        tokens={**self.tokens,**values}
        return re.sub(r'\{\{([a-z_]+)\}\}',lambda m:str(tokens[m[1]]) if m[1] in tokens else m[0],s)
    def component(self,name,content):return self.fill(self.components[name],content=content)
    def leaf(self,t):return '<span leaf="">'+html.escape(t).replace('\n','<br>')+'</span>'
    def image(self,x):
        url=x['image'];src=url
        if not safe_url(url,True):raise ValueError('不支持的图片地址：'+url)
        if not urlsplit(url).scheme:
            path=(self.base/url).resolve()
            if not path.is_relative_to(self.base.resolve()):raise ValueError('图片超出源目录')
            if not path.is_file():raise FileNotFoundError('图片缺失：'+str(path))
            raw=path.read_bytes();digest=hashlib.sha256(raw).hexdigest()
            if x.get('sha256') and x['sha256']!=digest:raise ValueError('原图内容发生变化：'+url)
            mime=x.get('mime') or mimetypes.guess_type(url)[0] or 'application/octet-stream'
            if mime not in ('image/png','image/jpeg','image/gif','image/webp'):
                raise ValueError('图片需先转换为PNG/JPEG/GIF/WEBP并核对：'+url)
            if self.embed:src='data:'+mime+';base64,'+base64.b64encode(raw).decode()
        style='max-width:100%;height:auto;display:block;margin:0 auto;'
        if x.get('width'):
            w=float(x['width'])
            if not 0<w<=2000:raise ValueError('图片显示宽度超出范围')
            style+=f'width:{w:g}px;'
        tag=f'<img src="{html.escape(src,quote=True)}" alt="{html.escape(x.get("alt",""),quote=True)}" style="{style}">'
        if x.get('href'):tag=self.link(x['href'],tag)
        return self.component('image',tag)
    def link(self,url,content):
        if not safe_url(url):raise ValueError('不支持的链接协议：'+url)
        return '<a href="'+html.escape(url,quote=True)+'" style="color:'+self.tokens['ink']+';text-decoration:underline;overflow-wrap:anywhere;">'+content+'</a>'
    def text(self,x,keywords):
        t=x.get('text','');valid=[k for k in keywords if k and k in t]
        if valid:
            p='('+'|'.join(map(re.escape,valid))+')'
            s=''.join(self.component('mark',self.leaf(v)) if v in valid else self.leaf(v) for v in re.split(p,t) if v)
        else:s=self.leaf(t)
        if x.get('bold'):s='<strong>'+s+'</strong>'
        if x.get('italic'):s='<em>'+s+'</em>'
        if x.get('underline'):s=self.component('mark',s)
        if x.get('code'):s='<span style="font-family:Consolas,monospace;background:#F5F8FA;">'+s+'</span>'
        if x.get('href'):s=self.link(x['href'],s)
        return s
    def block(self,b):
        kind=b['type']
        if kind=='table':
            rows=[]
            for row in b['rows']:
                cells=[]
                for c in row:
                    attrs=''.join(f' {n}="{int(c.get(n,1))}"' for n in ('colspan','rowspan') if int(c.get(n,1))>1)
                    cells.append(f'<td{attrs} style="padding:10px;border:1px solid {self.tokens["border"]};vertical-align:top;">'+''.join(self.block(x) for x in c['blocks'])+'</td>')
                rows.append('<tr>'+''.join(cells)+'</tr>')
            return self.component('table',''.join(rows))
        if kind=='code':
            s=plain(b)
            return self.component('code',''.join('<p style="margin:0;line-height:1.7;">'+self.leaf(line.replace('\t','　　').replace('  ','　'))+'</p>' for line in s.split('\n')))
        role=b.get('role','body');style='paragraph'
        if kind=='heading':style='title' if b.get('level')==1 else 'chapter' if b.get('level')==2 else 'subhead'
        elif role in ('caption','reference'):style=role
        elif kind=='list_item':style='paragraph'
        keywords=b.get('keywords',[])[:3];parts=[];current=[]
        for x in b.get('inlines',[]):
            if 'image' in x:
                if current:parts.append(self.component(style,''.join(current)));current=[]
                parts.append(self.image(x))
            else:current.append(self.text(x,keywords))
        if current:parts.append(self.component(style,''.join(current)))
        content=''.join(parts)
        if role in ('intro','notice'):content=self.component('notice',content)
        elif role in ('exam','course','teacher','price','faq'):content=self.component('card',content)
        elif role=='cta':content=self.component('cta',content)
        return content
    def render(self,data):return self.component('root','\n'.join(self.block(b) for b in data['blocks']))

def render_file(source,output,theme=None,article_type='course',color=None):
    source=Path(source).resolve();output=Path(output).resolve();output.parent.mkdir(parents=True,exist_ok=True)
    if source.suffix=='.json':data=json.loads(source.read_text(encoding='utf-8'))
    else:
        data=parse_markdown(source.read_text(encoding='utf-8'));data.update(source_name=source.name,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest())
        source=source.with_suffix('.source.json');source.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    theme=theme or AUTO_THEME[article_type]
    renderer=Renderer(source.parent,theme,color);fragment=renderer.render(data);output.write_text(fragment,encoding='utf-8')
    local=Renderer(source.parent,theme,color,False).render(data)
    # Rebase local images to output dir and copy bytes there; never depend on source folder after delivery.
    import shutil
    from html.parser import HTMLParser
    class Images(HTMLParser):
        def __init__(self):super().__init__();self.paths=[]
        def handle_starttag(self,tag,attrs):
            if tag=='img':self.paths.append(dict(attrs)['src'])
    parser=Images();parser.feed(local)
    media=[]
    for url in dict.fromkeys(parser.paths):
        if urlsplit(url).scheme:continue
        src=(source.parent/url).resolve();dst=(output.parent/url).resolve();dst.parent.mkdir(parents=True,exist_ok=True)
        if src!=dst:shutil.copyfile(src,dst)
        media.append({'path':url,'sha256':hashlib.sha256(src.read_bytes()).hexdigest()})
    output.with_name(output.stem+'_本地图片.html').write_text(local,encoding='utf-8')
    output.with_suffix('.media.json').write_text(json.dumps(media,ensure_ascii=False,indent=2),encoding='utf-8')
    from audit_article import audit
    checks=audit(data,fragment,source.parent)
    checks.update(theme=theme,article_type=article_type,primary=renderer.tokens['primary'],source_json=str(source),media_note='预览显示不等于公众号图片转存成功，必要时按素材索引补传。')
    output.with_suffix('.checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
    output.with_name(output.stem+'_待核对.txt').write_text('\n'.join(checks['business_notes']+data.get('warnings',[])) or '自动检查未发现已覆盖规则内的问题；机构身份、权益、二维码归属和实际粘贴仍须核对。',encoding='utf-8')
    print(f'已生成 {output}；theme={theme}；本地素材{len(media)}个。')
    if checks['content_errors']:raise ValueError('内容完整性失败：'+str(checks['content_errors']))
    return fragment,checks
def main():
    ap=argparse.ArgumentParser();ap.add_argument('source');ap.add_argument('-o','--output',required=True);ap.add_argument('--theme',choices=['standard','professional','friendly']);ap.add_argument('--type',dest='kind',choices=list(AUTO_THEME),default='course');ap.add_argument('--color');a=ap.parse_args()
    render_file(a.source,a.output,a.theme,a.kind,a.color)
if __name__=='__main__':main()
