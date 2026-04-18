# YouKnowTV Python 爬虫设计

## 目标

在当前 Python 仓库中新增一个符合 `base.spider.Spider` 接口的 YouKnowTV 站点爬虫，覆盖以下能力：

- 首页分类
- 今日更新列表
- 分类列表
- 详情页
- 搜索
- 播放解析

实现基于网页 DOM 抓取与播放页脚本解析，不依赖 Playwright，不修改 `base/` 公共层。

## 范围

本次实现包含：

- 新增独立脚本，暂定文件名为 `youknow.py`
- 使用单一站点主域：`https://www.youknow.tv`
- 支持 `home/homeVideo/category/detail/search/player` 全链路

本次实现不包含：

- 多域名自动回退
- Cloudflare 绕过
- 通用视频网站抽象框架
- 参考 JS 中所有非核心候选线路策略的 1:1 平移

## 方案选择

采用混合方案：

- 首页、分类、搜索、详情使用 `requests + lxml` 直接解析 HTML
- 播放解析吸收参考插件 `plugin_youknow` 中已经验证过的关键策略，包括：
  - `player_aaaa` 配置提取
  - 多层百分号/base64 解码
  - 播放页与 iframe 页中的候选直链提取
  - 多线路同集对齐

不逐行平移参考 JS，原因是：

- 当前仓库已有 Python 站点脚本风格，宜保持单文件实现
- 参考插件包含运行时兼容分支和 UI 输出逻辑，Python 版只保留站点真正需要的解析链路
- 先确保常见播放链路稳定，再看是否需要补特例

## 模块边界

新增脚本只在站点文件内部维护逻辑，不修改 `base/`。

脚本内部职责拆分如下：

- `init`
  - 初始化主域、请求头、分类映射
- `homeContent`
  - 返回固定分类
- `homeVideoContent`
  - 抓取今日更新页并解析媒体卡片
- `categoryContent`
  - 请求分类页并解析媒体卡片
- `searchContent`
  - 请求搜索页并解析搜索结果
- `detailContent`
  - 提取影片基础信息和多线路剧集列表
- `playerContent`
  - 解析剧集页、iframe 页与候选直链，返回最终播放地址
- 私有辅助函数
  - URL 与紧凑 id 归一化
  - 列表卡片解析
  - 详情字段解析
  - 剧集线路对齐
  - 播放页配置提取
  - 候选直链收集与去重

## Host 与分类策略

本次只实现单域：

- `https://www.youknow.tv`

请求失败时不做多域切换，只返回空结果或空播放地址。

分类沿用参考插件配置：

- `index`
- `drama`
- `movie`
- `variety`
- `anime`
- `short`
- `doc`

分类 URL 映射如下：

- `index -> /label/new/`
- `drama -> /show/1--------{pg}---/`
- `movie -> /show/2--------{pg}---/`
- `variety -> /show/3--------{pg}---/`
- `anime -> /show/4--------{pg}---/`
- `short -> /show/55--------{pg}---/`
- `doc -> /show/5--------{pg}---/`

其中：

- `homeContent` 返回上述固定分类
- `homeVideoContent` 请求 `/label/new/`

## 列表与搜索解析

### 今日更新页与分类页

主要解析海报卡片，优先覆盖参考插件里正则与 DOM 两种结构：

- `module-poster-item`
- `module-card-item-poster`

每张卡片提取规则：

- 链接：详情页链接
- 标题：优先 `title`，回退到 `alt` 或节点文本
- 封面：优先 `data-original`、`data-src`，其次 `src`
- 描述：优先 `module-item-note` 或 `module-item-text`

输出字段：

- `vod_id`
  - 返回紧凑详情 id，不返回完整详情 URL
- `vod_name`
- `vod_pic`
- `vod_remarks`

### 搜索页

搜索 URL：

- `/search/-------------.html?wd=<keyword>`

搜索结果与分类页复用同一套卡片解析逻辑。

### 分页策略

返回分页字段：

- `page = 当前页`
- `pagecount = pg + 1`，若当页无内容则为当前页
- `limit = 实际条目数`
- `total = 近似值`

不依赖站点总数统计。

## 详情页设计

`detailContent` 使用紧凑 `vod_id` 在内部组装详情页 URL 并请求页面。

提取字段：

- `vod_id`
- `path`
- `vod_name`
- `vod_pic`
- `vod_tag`
- `vod_time`
- `vod_remarks`
- `vod_play_from`
- `vod_play_url`
- `type_name`
- `vod_content`
- `vod_year`
- `vod_area`
- `vod_lang`
- `vod_director`
- `vod_actor`

不返回：

- `dbid`
- `type`

详情字段优先从详情主块中按标签解析，并兼容纯文本或链接混排形式。

### 多线路剧集设计

YouKnowTV 的详情页可能存在多线路、多集数，且同一集在不同线路有不同播放页 URL。参考实现的关键点不是简单把所有链接平铺，而是：

- 先解析每条线路的剧集链接
- 从剧集 URL 中提取：
  - `vodId`
  - `sourceId`
  - `episodeIndex`
- 按 `episodeIndex` 对齐多条线路
- 对同一集生成一个紧凑播放 payload，里面保存多个候选线路

Python 版会保留这一思路，但对外仍然维持仓库统一约定：

- `vod_play_from`
  - 若只做单一虚拟源，可固定为 `YouKnowTV`
- `vod_play_url`
  - 单集项格式为 `标题$紧凑播放id`

紧凑播放 id 将采用站点内部可逆的序列化形式，用于在 `playerContent` 中恢复该集的候选线路列表，而不是直接暴露完整播放页 URL。

## 播放解析设计

YouKnowTV 的播放解析不是单层页面直链，而是候选直链收集问题。核心来源包括：

1. 播放页脚本中的 `player_aaaa`
2. 播放页 HTML 中直接出现的 `m3u8/mp4/flv`
3. 播放页中 iframe 的 `src`
4. iframe 页中再次出现的 `player_aaaa` 或直链

### 解码策略

参考实现中关键解码规则如下，Python 版保留：

- `encrypt = 0`
  - 原样处理
- `encrypt = 1`
  - 百分号解码
- `encrypt = 2`
  - 多层候选解码：
    - 原值
    - 百分号解码 1-2 层
    - base64 解码
    - base64 后再做 1-3 层百分号解码
  - 从这些候选里优先选直接可播 URL

### 候选直链判定

可播直链至少满足以下之一：

- `http://` 或 `https://`
- 协议相对 `//`
- 包含 `.m3u8`
- 包含 `.mp4`
- 包含 `.flv`

### 播放流程

`playerContent` 实现步骤：

1. 将紧凑播放 id 还原为候选播放页 URL 列表
2. 按顺序请求每个候选播放页
3. 收集播放页中的候选直链
4. 若页面包含 iframe，再请求 iframe 页补充候选直链
5. 将候选直链去重
6. 选择第一个最终可播 URL 返回

返回格式：

- `parse = 0`
- `playUrl = ""`
- `url = 最终播放地址`
- `header = {"User-Agent": "...", "Referer": "..."}`

若所有候选线路都失败，则返回空播放结构。

## 请求与兼容性

统一请求头至少包含：

- 浏览器 `User-Agent`
- `Referer`
- `Accept-Language`

YouKnowTV 可能出现 challenge 页面。Python 版不负责绕过 challenge，但会识别明显 challenge 标志并优雅返回空结果，避免把错误页当成正文继续解析。

## 错误处理

实现遵循“失败返回空，不抛异常中断”的原则：

- 页面请求失败时返回空列表或空播放 URL
- DOM 节点缺失时字段回退为空字符串
- 候选播放页解析失败时继续尝试下一个候选
- 最终失败则返回 `{"parse": 0, "playUrl": "", "url": ""}`

日志只保留必要调试信息，重点是播放候选恢复和直链提取链路。

## 测试设计

采用测试优先方式实现，先给纯解析函数写测试，再补生产代码。

测试重点：

1. 首页/分类卡片解析
   - 断言能解析紧凑 `vod_id`、标题、封面和备注
2. 首页与分类高层流程
   - 断言 `homeContent` 返回固定分类
   - 断言 `homeVideoContent` 与 `categoryContent` 组装结果正确
3. 搜索解析
   - 断言搜索结果复用卡片解析
4. 详情解析
   - 断言基础字段提取正确
   - 断言多线路剧集会被对齐成紧凑播放 id
5. 播放解析
   - 断言能提取 `player_aaaa`
   - 断言 `encrypt=1/2` 解码行为正确
   - 断言能从播放页与 iframe 页提取候选直链
   - 断言候选失败时继续尝试下一条

优先使用 `unittest` 和 mock，避免测试依赖真实站点网络。

## 实施顺序

1. 新增 `tests/test_youknow.py`，先覆盖首页/分类/搜索/详情/播放器核心解析
2. 新增 `youknow.py` 基本骨架与分类映射
3. 实现首页、分类和搜索列表抓取
4. 实现详情字段、多线路对齐与紧凑播放 payload
5. 实现播放页与 iframe 页的候选直链解析
6. 运行测试并补必要的解码与容错逻辑
