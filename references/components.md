# 组件与装配

实际 HTML 单一来源 assets/components.json。render_article.py 加载真实组件，{{token}}替换为常量，不输出CSS变量。

| 内容 | 组件 |
|---|---|
| 全局 | root：白底677px、16px正文 |
| 主标题／章节／子标题 | title／chapter／subhead |
| 段落／关键词 | paragraph／mark |
| intro、notice | notice：浅底左条 |
| exam、course、teacher、price、faq | card：深字浅边框 |
| 原稿行动／图注／来源 | cta／caption／reference |
| 图片／表格／代码 | image／table／code |

骨架：原稿标题与首图→原稿导语→章节正文→原稿行动与品牌图。缺模块直接省略。
业务配方见recipes.md，主题见brand.json，一篇一套主题且保留输入顺序。长表格保留可滚动；转卡片须保留全部字段和源映射，由Agent处理核对。
375、390、677px检查溢出、图片比例、长链接、表格边框与二维码。
