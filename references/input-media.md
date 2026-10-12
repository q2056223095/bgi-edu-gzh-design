# 输入与媒体保真

## Word
extract_docx.py 使用 Python 标准库，输出.md、.source.json、images/。JSON为保真来源，遍历段落、表格、行内文字、图片、链接并保持相对顺序。
仅明确标题样式／大纲级别识别标题，加粗不是标题；解析继承样式。Agent根据语义确认层级。
表格保留多段文字、图片、链接与合并信息；复杂结构、文本框、修订记录等列 warnings。浮图保留XML锚点位置，不宣称复原Word绝对坐标。

## Markdown／纯文本
支持标题、段落、列表、引用、表格、粗体、斜体、下划线、图片、链接、行内代码和围栏。未支持结构由Agent转JSON，不能删除。纯文本URL保留可点击。PDF先通过PDF能力完整读取，再转JSON，不宣称脚本支持直接解析PDF。

## 图片与链接
保留原图 bytes、原比例、图文顺序、二维码名称关联、外链目标。样式max-width:100%;height:auto;display:block;margin:0 auto，不放大小图。
小二维码可设置单图显示width；禁止重绘二维码。预览内嵌本地图，交付原图包；公众号可能需补传，不承诺自动成功。远程图URL原样保留，不编图床。
允许http/https/mailto/tel和安全本地路径；拒绝javascript等执行协议并提示。切换色系只改变主题token。

## 结构
block含id、type、role、keywords、inlines。文字inline含text及可选bold/italic/underline/code/href；图片含image相对路径、mime、sha256、alt、可选href和width。
table的rows为cell数组，cell含blocks、colspan、rowspan。用户追加事实进入新来源；不为了通过核验修改原source.json。
