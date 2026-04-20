# 欧歌 Python 爬虫设计

**日期：** 2026-04-20

## 目标

在当前 Python Spider 仓库中新增一个独立单站蜘蛛 `欧歌.py`，参考用户提供的 JS 版本行为，实现符合 `base.spider.Spider` 接口的网盘资源站适配。

本次实现需要覆盖：

- 固定 6 个分类
- 分类列表
- 搜索
- 详情页元数据解析
- 网盘链接整理
- 播放透传
- 对应 `unittest`

## 范围

本次实现包含：

- 新增独立蜘蛛文件 `py/欧歌.py`
- 新增测试文件 `py/tests/test_欧歌.py`
- 单域名站点适配：`https://woog.nxog.eu.org`
- 固定 6 个分类，分类 ID 与参考 JS 保持一致
- 分类页和搜索页卡片解析
- 详情页元数据与网盘链接提取
- 按网盘类型输出 `vod_play_from` 和 `vod_play_url`
- `playerContent` 对已识别网盘分享链接直接透传

本次实现不包含：

- 聚合多站
- 本地筛选配置文件
- 站内视频播放解析
- 验证码、浏览器执行或复杂反爬绕过
- 修改 `base/` 公共层

## 方案选择

采用“单站单文件 + 少量 helper + 单测”的仓库现有模式，而不是直接把参考 JS 逐段翻译成 Python。

原因：

- 用户明确要求独立单站文件
- 当前仓库已经普遍使用单文件 Spider 模式
- 私有 helper 可以把 URL 组装、文本清洗、列表解析、详情提取和网盘识别拆开，降低后续修站成本
- 测试可以直接针对 helper 和高层接口分层验证，适合 TDD

不采用“提前抽公共网盘站基类”的方案，原因是本次只落单站，过早抽象会增加复杂度且不符合当前仓库习惯。

## 接口设计

### `homeContent`

返回固定 6 个分类：

- `1 -> 欧歌电影`
- `2 -> 欧哥剧集`
- `3 -> 欧歌动漫`
- `4 -> 欧歌综艺`
- `5 -> 欧歌短剧`
- `21 -> 欧歌综合`

不返回筛选项。

### `homeVideoContent`

返回空列表：

- `{"list": []}`

### `categoryContent`

分类页 URL 规则：

- `/index.php/vod/show/id/{tid}/page/{page}.html`

解析页面中的卡片，输出：

- `vod_id`
- `vod_name`
- `vod_pic`
- `vod_remarks`

分页返回字段：

- `page`
- `limit`
- `total`
- `list`

不返回 `pagecount`，以保持当前仓库对新蜘蛛的约定。

### `searchContent`

搜索 URL 规则：

- `/index.php/vod/search/page/{page}/wd/{keyword}.html`

空关键词直接返回空列表。

搜索结果结构与分类列表保持一致。

### `detailContent`

通过详情页提取：

- `vod_id`
- `vod_name`
- `vod_pic`
- `vod_year`
- `vod_director`
- `vod_actor`
- `vod_content`
- `vod_play_from`
- `vod_play_url`

不解析站内播放页，只整理网盘分享链接。

### `playerContent`

若 `id` 是支持的网盘分享链接，则返回透传结果：

```python
{"parse": 0, "jx": 0, "playUrl": "", "url": id, "header": {}}
```

若不是已识别网盘链接，则返回空 URL：

```python
{"parse": 0, "jx": 0, "playUrl": "", "url": "", "header": {}}
```

## 模块边界

新蜘蛛内部拆分为以下职责：

- 站点配置与固定分类
- URL 组装
- 文本清洗
- 图片 URL 修正
- 列表卡片解析
- 搜索卡片解析
- 详情页字段提取
- 网盘类型识别
- 网盘线路拼接

不新增公共基类，不抽共享模块。

## URL 与 ID 设计

详情页 `vod_id` 使用站内短路径，而不是完整 URL。

编码方式：

- 详情链接 `/index.php/vod/detail/id/123.html` 对外直接保存为 `/index.php/vod/detail/id/123.html`

原因：

- 与参考 JS 行为一致
- 当前仓库已有多个蜘蛛直接使用站内短路径作为 `vod_id`
- 单站实现不需要再引入额外编码层

详情请求时再基于主域拼成完整地址。

## 请求策略

主域固定为：

- `https://woog.nxog.eu.org`

请求头包含固定 `User-Agent`，必要时补 `Referer` 为首页。

异常处理策略：

- 页面请求失败时返回空列表或空字段结果
- 不向上抛出未处理异常
- 不实现多域名切换
- 不实现重试

## 图片修正规则

保留参考 JS 的核心行为：

- 空图片返回空字符串
- 若已是绝对 URL，原样返回
- 若是站内相对路径，则补全为绝对地址
- 优先使用 `data-src`，其次回退 `src`

本次不额外引入聚合站里针对百度图片包裹 URL 的特殊修正，因为用户提供的欧歌参考实现没有这层要求；如果测试夹具后续证明站点确有该问题，再单独补充。

## 列表与搜索解析

分类列表解析容器：

- `#main .module-item`

提取策略：

- 链接：`.module-item-pic a[href]`
- 标题：`.module-item-pic img[alt]`
- 封面：`.module-item-pic img[data-src|src]`
- 备注：`.module-item-text`

搜索结果解析容器：

- `.module-search-item`

提取策略：

- 链接和标题优先来自 `.video-serial`
- 封面来自 `.module-item-pic img[data-src|src]`
- 备注优先取 `.video-serial` 文本，缺失时回退 `.module-item-text`

列表和搜索都应避免空标题、空链接项。

## 详情解析

详情页从 HTML 中提取以下信息：

- 标题：`.page-title`
- 封面：`.mobile-play .lazyload[data-src|src]`
- 年份：优先取页面中 `.module-item-caption span` 或其它可用年份文本，缺失时留空
- 导演、主演、剧情：遍历 `.video-info-itemtitle` 与相邻内容节点
- 网盘链接：`.module-row-info p`

字段处理规则：

- 多个导演或主演用英文逗号连接
- 去除多余空白字符
- 缺失字段保留空字符串

剧情字段优先从标题为“剧情”的信息块中提取 `p` 文本。

## 网盘线路设计

详情页中每个分享链接会被识别为网盘类型，再输出为播放线路。

首批支持识别：

- 百度网盘
- 夸克网盘
- UC 网盘
- 阿里云盘
- 迅雷云盘
- 115 网盘
- 天翼云盘
- 139 网盘
- 123 云盘

输出规则：

- `vod_play_from` 中每条线路格式为 `<pan_type>`
- `vod_play_url` 中每条线路格式为 `<资源标题>$<分享链接>`
- 线路之间使用 `$$$` 分隔
- 同一详情页内对重复分享链接去重
- 同一详情页内按预设网盘优先级排序

资源标题使用人类可读名称，例如：

- `百度资源`
- `夸克资源`
- `UC资源`
- `阿里资源`

这里刻意不把站点名写入 `vod_play_from`，因为本次是独立单站，保留纯盘类型更贴近用户提供的 JS 行为。

## 失败与回退行为

### 分类与搜索

- HTML 为空或请求失败时，返回当前页和空列表
- 空关键字搜索时，不发请求，直接返回空列表

### 详情

- 请求失败或 HTML 无法解析时，返回单条结果
- 至少保留传入的 `vod_id`
- 其它字段使用空字符串
- `vod_play_from` 与 `vod_play_url` 为空字符串

### 播放

- 识别到支持的网盘分享链接时，直接透传
- 未识别链接时返回空 URL
- 不尝试解析站内播放页

## 测试设计

测试采用 `unittest` 和 `unittest.mock`，风格与当前仓库一致，通过 `SourceFileLoader` 加载 `欧歌.py`。

### 第一组：结构与纯函数

覆盖：

- 固定 6 个分类输出正确
- `homeVideoContent` 返回空列表
- URL 组装符合站点规则
- 网盘类型识别正确

### 第二组：列表与搜索

覆盖：

- 分类页卡片解析出短路径 `vod_id`
- 分类接口正确拼 URL 并返回分页结构
- 搜索接口正确拼 URL 并解析结果
- 空关键字搜索直接返回空列表且不请求网络

### 第三组：详情与播放

覆盖：

- 详情页标题、海报、导演、主演、剧情解析
- 网盘分享链接识别与去重
- `vod_play_from` / `vod_play_url` 顺序对齐
- `playerContent` 对网盘分享链接透传
- `playerContent` 对未知链接返回空 URL

## 实现顺序

遵循 TDD：

1. 先写结构与 helper 测试，验证失败
2. 写最小实现让结构测试通过
3. 增加分类与搜索测试，验证失败
4. 写最小实现让列表测试通过
5. 增加详情与播放测试，验证失败
6. 写最小实现让详情和播放测试通过
7. 运行目标模块测试，必要时再跑更大范围回归

## 风险与约束

- 该站页面结构如果对 `.page-title`、`.module-row-info` 等选择器有明显偏移，需要在实现时增加一层轻量兜底选择器
- 参考 JS 中年份直接来自列表页卡片，而详情页未明确给出稳定选择器，因此 `vod_year` 允许为空，不强行猜测
- 页面里的网盘文本可能不是纯 URL，实现时应允许从文本中提取 URL，而不是假设整个节点文本就是链接
- 不做实时联网核验，本次以用户给出的参考 JS 结构和仓库测试风格为准

## 验收标准

满足以下条件即可视为完成：

- 新增 `欧歌.py` 与 `tests/test_欧歌.py`
- `homeContent/homeVideoContent/categoryContent/detailContent/searchContent/playerContent` 均返回符合当前仓库习惯的数据结构
- 列表和搜索结果使用站内短路径 `vod_id`
- 详情页输出符合预期的网盘线路
- `playerContent` 只透传网盘分享链接，不做站内解析
- 新增测试通过
