---
name: bgi-edu-gzh-design
description: "将深圳市华大教育中心的 Word、Markdown、纯文本稿件排版为微信公众号 HTML。默认使用 #00ACD2 品牌色，支持课程招生、认证考试、科普研学、联合培养、合作新闻、科学知识与公益科普；保留原文、图片、表格和链接，输出一键复制预览及素材包。用于华大教育公众号排版、推文美化和品牌配色调整；封面仅在用户要求时调用图像生成能力。不负责默认改写文章或生成官网、GEO、多平台传播稿。"
---

# 华大教育公众号排版

版本：0.1.0。基于 isjiamu/gzh-design-skill 的预览与校验流程适配，署名与许可见 NOTICE、LICENSE。

## 工作流程

1. 读取输入与用户要求。直接排版时自动选主题，不反复确认结构、配色；只有输入不明确或缺少必要文件时询问。
2. 读取 references/brand.md、references/recipes.md、references/theme-index.md。用户配色／活动主视觉优先；默认主色 #00ACD2。
3. 读取 references/input-media.md，Word 用 `python3 <SKILL_ROOT>/scripts/extract_docx.py 输入.docx -o 输出/原稿.md`，生成 Markdown、source.json、原图。JSON 是保真来源；读取全部 blocks 和 warnings，不以统计或摘要代替全文。
4. 综合样式和语义判断标题；加粗正文、时间说明不是章节。按业务模板给现有模块赋 role，只调整 JSON 的 type、level、role、keywords 等展示属性，保留 id、inlines、rows 和内容顺序。不能删除源块来凑模板或规避检查。
5. 按 references/components.md 和 assets/components.json 的真实组件装配，不能手写另一套视觉。通常每段0—2个关键词，原文无重点时不强制划线。默认不添加博主署名、固定三连、英文标签、∞／/// 或新目录。
6. 渲染：`python3 <SKILL_ROOT>/scripts/render_article.py 输出/原稿.source.json -o 输出/推文.html --theme standard --type exam`。theme：standard/professional/friendly；type：course/exam/science/joint/news/knowledge。`--color '#00ACD2'` 可覆盖配色；重渲染而非全文件颜色替换，避免修改图片和URL。Markdown、纯文本可直接输入，未支持结构由 Agent 转JSON保留。
7. 检查：`python3 <SKILL_ROOT>/scripts/validate_gzh_html.py 输出/推文.html --strict`；`python3 <SKILL_ROOT>/scripts/audit_article.py 输出/原稿.source.json 输出/推文.html -o 输出/核对.json`。内容完整性与平台ERROR必须通过；样式WARNING要修复；业务矛盾保留原文，在正文之外列出，不擅自修改。读取生成的 checks.json 和待核对清单。
8. 预览：`python3 <SKILL_ROOT>/scripts/wrap_preview.py 输出/推文.html`；素材包：`python3 <SKILL_ROOT>/scripts/package_article.py 输出/推文.html`。375、390、677px检查溢出、图片比例、表格边框、长链接、二维码，实际点击复制按钮。不能浏览器验证时说明“脚本已检查，实际粘贴待核验”。浏览器可见与公众号成功粘贴是不同检查，不承诺本地图片必定被接收。
9. 交付预览 HTML、干净正文 HTML；有本地图片附媒体包，有矛盾附核对清单。说明打开预览→复制→公众号粘贴；图片未被接收按素材顺序补传。未要求时不额外生成封面、不发布公众号、不安装。

## 内容与机构身份

- 保留所有段落、图片、表格字段、链接和顺序。移除重复页眉前确认其为版面噪声；不随意删除文末品牌图。
- 日期、金额、讲师姓名资历、认证名称、权益、合作方和主办承办关系必须有本稿来源，不固化动态考期或课程事实。
- 新闻保留华大主体、行动、贡献与合作方角色，不通过排版提高证据强度或扩写权威、保证通过、就业承诺。
- 只有用户明确要求改写时另做可审阅版本。默认排版中的疑似错误、矛盾与夸大进核对清单，原文保留。
- 原稿有报名、咨询、预约则整理为唯一行动区；无则不新增。已有个人署名、引用作者保留，无则不创造。
- 人物照片、官方Logo、IP仅使用提供素材，不生成替代标识、不改变角色。

## 可选封面与维护

用户请求封面时读取 references/cover.md，调用图像生成工具一次一张，沿用正文主色，默认1200×448。不要新增费用、考期、合作标识或真实儿童；图像生成色值与文字需要核验。
修改组件跑 `python3 scripts/component_lint.py .`；修改脚本跑 `python3 -m unittest discover -s tests -v`。验收规则见 references/evaluation.md。任何“已测试”说明写明对象和限制；示例稿不是原稿回归，浏览器检查不是公众号实际粘贴。
