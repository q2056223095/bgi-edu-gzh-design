import base64
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from extract_docx import extract
from render_article import Renderer,parse_markdown,render_file
from audit_article import audit,business,walk
from validate_gzh_html import validate
from package_article import package

PNG=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jGZ0AAAAASUVORK5CYII=')
class WorkflowTests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.p=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def image(self,name='images/qr.png'):
        p=self.p/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(PNG);return name
    def docx(self):
        xml='''<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><w:body>
        <w:p><w:pPr><w:pStyle w:val="MyHeading"/></w:pPr><w:r><w:t>示例标题</w:t></w:r></w:p>
        <w:p><w:r><w:rPr><w:b/></w:rPr><w:t>加粗正文</w:t></w:r><w:r><w:t>前文</w:t><w:drawing><a:blip r:embed="rImage"/></w:drawing><w:t>后文</w:t></w:r><w:hyperlink r:id="rLink"><w:r><w:t>课程入口</w:t></w:r></w:hyperlink></w:p>
        <w:tbl><w:tr><w:tc><w:tcPr><w:gridSpan w:val="2"/><w:vMerge w:val="restart"/></w:tcPr><w:p><w:r><w:t>合并单元格</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>权益甲</w:t></w:r></w:p></w:tc></w:tr>
        <w:tr><w:tc><w:tcPr><w:gridSpan w:val="2"/><w:vMerge/></w:tcPr><w:p/></w:tc><w:tc><w:p><w:hyperlink r:id="rLink"><w:r><w:t>表内链接</w:t></w:r></w:hyperlink><w:r><w:drawing><a:blip r:embed="rImage"/></w:drawing></w:r></w:p></w:tc></w:tr></w:tbl>
        </w:body></w:document>'''
        styles='''<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:style w:styleId="Heading2"><w:name w:val="Heading 2"/></w:style><w:style w:styleId="MyHeading"><w:name w:val="My Heading"/><w:basedOn w:val="Heading2"/></w:style></w:styles>'''
        rels='''<Relationships><Relationship Id="rImage" Target="media/qr.png"/><Relationship Id="rLink" Target="https://example.org/course?x=1&amp;y=2" TargetMode="External"/></Relationships>'''
        path=self.p/'fixture.docx'
        with zipfile.ZipFile(path,'w') as z:
            z.writestr('word/document.xml',xml);z.writestr('word/styles.xml',styles);z.writestr('word/_rels/document.xml.rels',rels);z.writestr('word/media/qr.png',PNG)
        return path
    def test_docx_order_links_and_merged_table(self):
        d=extract(self.docx(),self.p/'source.md')
        self.assertEqual(d['warnings'],[])
        self.assertEqual(d['blocks'][0]['level'],2)
        self.assertEqual(d['blocks'][1]['type'],'paragraph')
        xs=d['blocks'][1]['inlines'];self.assertEqual([x.get('text','IMAGE') for x in xs],['加粗正文','前文','IMAGE','后文','课程入口'])
        self.assertEqual(d['blocks'][2]['rows'][0][0]['rowspan'],2)
        self.assertEqual(d['blocks'][2]['rows'][0][0]['colspan'],2)
        frag=Renderer(self.p).render(d);self.assertFalse(audit(d,frag,self.p)['content_errors'])
        self.assertEqual(frag.count('<img '),2)
        self.assertIn('colspan="2" rowspan="2"',frag)
    def test_recolor_preserves_media_links_and_text(self):
        image=self.image();d={'blocks':[{'type':'paragraph','role':'notice','inlines':[{'text':'报名入口','href':'https://example.org/#00ACD2'},{'image':image,'sha256':hashlib.sha256(PNG).hexdigest()}]}]}
        a=Renderer(self.p).render(d);b=Renderer(self.p,color='#A04060').render(d)
        self.assertNotEqual(a,b);self.assertFalse(audit(d,b,self.p)['content_errors']);self.assertIn('#A04060',b)
        self.assertIn('https://example.org/#00ACD2',b)
    def test_swapped_images_and_missing_text_fail(self):
        one=self.image();two=self.image('images/second.png');(self.p/two).write_bytes(PNG+b'other')
        d={'blocks':[{'type':'paragraph','inlines':[{'text':'关键内容'},{'image':one},{'image':two}]}]};a=Renderer(self.p).render(d)
        self.assertTrue(audit(d,a.replace('关键内容','删改'),self.p)['content_errors'])
        wrong=copy.deepcopy(d);wrong['blocks'][0]['inlines'][1:]=wrong['blocks'][0]['inlines'][1:][::-1]
        self.assertTrue(audit(d,Renderer(self.p).render(wrong),self.p)['content_errors'])
    def test_markdown_no_personal_signature(self):
        d=parse_markdown('# 专业课程\n\n## 内容\n正文**重点**与[链接](https://example.org)。\n\n| 版本 | 权益 |\n|---|---|\n|基础版|视频课|\n\n```python\nprint("hello")\n```')
        a=Renderer(self.p).render(d);self.assertFalse(audit(d,a,self.p)['content_errors']);self.assertNotIn('我是',a);self.assertNotIn('三连',a);self.assertNotIn('THE END',a)
        self.assertEqual(validate(a)[0:2],([],[]))
    def test_date_weekday_and_deadline_notes(self):
        notes=business('考试时间：2026年10月17日 09：00。报名截止：2026年10月18日（周一）18：00。')
        self.assertTrue(any('星期' in x for x in notes));self.assertTrue(any('晚于' in x for x in notes))
        self.assertFalse(business('报名截止：2026年10月13日（周二）18：00。考试时间：2026年10月17日 09：00。'))
    def test_partial_dates_not_guessed(self):self.assertTrue(any('缺少年份' in x for x in business('考试时间：10月17日')))
    def test_unsafe_links_and_missing_images_fail(self):
        for x in [{'text':'点击','href':'javascript:alert(1)'},{'image':'../escape.png'},{'image':'missing.png'}]:
            with self.assertRaises((ValueError,FileNotFoundError)):Renderer(self.p).render({'blocks':[{'type':'paragraph','inlines':[x]}]})
    def test_theme_roles_and_six_types(self):
        d={'blocks':[{'type':'heading','level':2,'inlines':[{'text':'章节'}]},{'type':'paragraph','role':'notice','inlines':[{'text':'报名截止'}]}]}
        for theme in ['standard','professional','friendly']:
            a=Renderer(self.p,theme).render(d);self.assertNotIn('{{',a);self.assertEqual(validate(a)[:2],([],[]))
        source=self.p/'demo.md';source.write_text('# 演示\n正文。')
        for t in ['course','exam','science','joint','news','knowledge']:
            a,c=render_file(source,self.p/(t+'.html'),article_type=t);self.assertEqual(c['content_errors'],[])
    def test_packaging_keeps_media_and_no_unrelated_files(self):
        self.image();d={'blocks':[{'type':'paragraph','inlines':[{'text':'原图'},{'image':'images/qr.png'}]}]}
        source=self.p/'source.json';source.write_text(json.dumps(d));out=self.p/'article.html';render_file(source,out)
        (self.p/'private.docx').write_text('不要打包')
        package_path=package(out)
        with zipfile.ZipFile(package_path) as z:
            self.assertIn('images/qr.png',z.namelist());self.assertNotIn('private.docx',z.namelist());self.assertEqual(z.read('images/qr.png'),PNG)
    def test_preview_copies_only_body_and_escapes_title(self):
        out=self.p/'safe&title.html';out.write_text(Renderer(self.p).render({'blocks':[{'type':'paragraph','inlines':[{'text':'正文'}]}]}))
        subprocess.run([sys.executable,str(ROOT/'scripts/wrap_preview.py'),str(out)],check=True,capture_output=True)
        preview=out.with_name(out.stem+'_预览.html').read_text()
        self.assertIn('safe&amp;title',preview);self.assertIn("getElementById('gzh-content')",preview)
        self.assertNotIn('<button',out.read_text())
    def test_strict_validation_exits_nonzero_on_warning(self):
        p=self.p/'bad.html';p.write_text('<section><p>漏包裹文字</p><span leaf="">另一段</span></section>')
        r=subprocess.run([sys.executable,str(ROOT/'scripts/validate_gzh_html.py'),str(p),'--strict'],capture_output=True)
        self.assertNotEqual(r.returncode,0)

if __name__=='__main__':unittest.main()
