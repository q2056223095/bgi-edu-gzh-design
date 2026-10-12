# 华大教育公众号排版 · BGI Edu GZH Design

v0.1.0，面向深圳市华大教育中心的课程、认证、科普研学、联合培养和合作新闻。

把 Word／Markdown／纯文本排成可复制到微信公众号编辑器的 HTML，默认主色 **#00ACD2**。保留原文、图片、表格与链接，提供一键复制预览、原图素材包和待核对清单。

## 给 AI 的用法

将本仓库作为 skill 加载，入口是 [SKILL.md](SKILL.md)。例如：

> 使用 bgi-edu-gzh-design，把这个 Word 排成华大教育公众号推文，保留全文和配图。

> 用华大青·专业版排版这篇联合培养报道。

> 将这篇推文主色改为 #00ACD2，保留原图、文字及链接。

支持三套主题：华大青·标准版、华大青·专业版、科学教育·亲和版；六类业务配方在 [references/recipes.md](references/recipes.md)。已有活动主视觉或用户指定配色优先。

## 本地脚本

Python **3.9+**，生产脚本仅使用标准库。先提取 Word：

```bash
python3 scripts/extract_docx.py article.docx -o output/source.md
```

AI 读取原稿后可在 `source.source.json` 调整展示层级、角色和关键词，保留实际内容、ID和顺序；根据原始JSON核对完整性。再生成：

```bash
python3 scripts/render_article.py output/source.source.json -o output/article.html --type exam
python3 scripts/validate_gzh_html.py output/article.html --strict
python3 scripts/audit_article.py output/source.source.json output/article.html -o output/audit.json
python3 scripts/wrap_preview.py output/article.html
python3 scripts/package_article.py output/article.html
```

Markdown可直接作为渲染输入。`--type` 可选 course、exam、science、joint、news、knowledge；`--theme` 可选 standard、professional、friendly；`--color '#00ACD2'` 覆盖主题色。

脚本负责可重复的提取、渲染与检查；文章结构与业务角色仍由AI阅读源稿后判断。复杂稿件不是单条命令就能替代审稿。

## 使用产物

浏览器打开 `article_预览.html` → 点击“复制到公众号” → 在公众号编辑器粘贴。
本地图片已内嵌用于离线预览；公众号可能需要再次上传图片。素材包包含本地图片版正文、原图、媒体索引和核对结果。网页预览正确不代表公众号图片转存必定成功。

原稿缺少二维码或字段时保留占位并提示，不编造。业务矛盾保留原文，在核对清单提示。默认不改写、不给机构添加博主署名或固定三连。
仅用户请求时配套生成封面，默认1200×448，一次一张；生成依赖外部可用的图像生成能力。

## 验证

```bash
python3 -m unittest discover -s tests -v
python3 scripts/component_lint.py .
```

首版11项自动测试通过。真实考试通知回归保留16张原图和原链接，职业规划稿回归保留全文和价格权益表；真实稿件与二维码不在公开仓库。
首版尚未完成公众号编辑器实际粘贴验收；独立Agent试用与浏览器视口检查在当前运行环境中未完成。见 [references/evaluation.md](references/evaluation.md) 和 [docs/validation-v0.1.0.md](docs/validation-v0.1.0.md)。

## 上游与许可

基于 [isjiamu/gzh-design-skill](https://github.com/isjiamu/gzh-design-skill) 的预览、平台校验与组件检查流程适配。感谢 **甲木 × 摸鱼小李**。
保留 GNU AGPL-3.0 许可与上游署名，变更范围见 [NOTICE](NOTICE)。本主题采用用户确认的工作品牌色，不代替官方完整 VI，未附官方Logo或IP素材。
