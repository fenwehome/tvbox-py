# AAZ音乐 Python 爬虫设计

## 目标

在当前 Python 仓库中新增一个符合 `base.spider.Spider` 接口的 AAZ 音乐爬虫，行为参考用户提供的 OmniBox 脚本，但交付物遵循仓库现有的单文件 Spider 结构、短 ID 约定和 `unittest` 测试方式。

首版仅覆盖仓库最常用的五个能力：

- 首页
- 分类
- 搜索
- 详情
- 播放

## 范围

本次实现包含：

- 新增独立脚本 `py/AAZ音乐.py`
- 新增独立测试 `py/tests/test_AAZ音乐.py`
- 首页固定分类与推荐歌曲解析
- 分类页对歌曲、歌手、歌单、专辑、MV 的列表解析
- 搜索页的混合结果解析
- 单曲详情解析
- 歌手、歌单、专辑、MV 详情页解析
- 单曲试听直链解析
- 针对短 ID、空结果、详情播放串和播放失败回退增加离线单测

本次实现不包含：

- 下载链接抓取和返回
- 歌词链接抓取和返回
- 修改 `py/base/` 公共层
- 引入新的第三方依赖
- 真实联网集成测试
- 复杂反爬绕过、代理、缓存和重试策略
- 对 MV 独立播放链路做额外兼容

## 方案选择

采用“按仓库 Python Spider 形态重写站点逻辑”的方案，而不是直接移植 OmniBox 脚本的数据模型。

原因如下：

- 当前仓库消费的是 Python Spider 接口，而不是 OmniBox 风格的异步 handler
- 仓库现有测试和调用都围绕 `homeContent/categoryContent/searchContent/detailContent/playerContent`
- 参考脚本中的下载、歌词和扩展字段不在本次范围内，直接照搬会增加无效复杂度
- 使用短 ID 和离线 fixture 更符合当前仓库的可维护性与可测试性

## 模块边界

新增模块 `py/AAZ音乐.py` 只负责 AAZ 站点逻辑，不修改 `py/base/`。

模块对外实现以下接口：

- `init`
- `getName`
- `homeContent`
- `homeVideoContent`
- `categoryContent`
- `detailContent`
- `searchContent`
- `playerContent`

模块内部使用 helper 收敛 URL、ID 编解码和页面解析逻辑：

- `_build_url`
  - 补全站点绝对地址
- `_fetch_html`
  - 统一 GET 页面并返回文本
- `_post_play_api`
  - 统一 POST `/js/play.php` 并解析 JSON
- `_load_html`
  - 将 HTML 转成可 XPath 的文档对象
- `_clean_text`
  - 规范化文本并移除多余空白
- `_extract_song_id`
  - 从 `/m/<id>.html` 链接提取单曲 ID
- `_encode_vod_id`
  - 将站点链接编码为仓库短 `vod_id`
- `_decode_vod_id`
  - 将短 `vod_id` 还原为站点详情路径
- `_parse_song_cards`
  - 解析歌曲列表
- `_parse_folder_cards`
  - 解析歌手、歌单、专辑、MV 封面卡片
- `_parse_folder_tracks`
  - 从目录型详情页提取歌曲播放列表
- `_parse_song_detail`
  - 提取单曲详情元信息
- `_build_empty_result`
  - 返回统一的空分页结构

## 站点配置

固定站点配置如下：

- 站点名：`AAZ音乐`
- 根地址：`https://www.aaz.cx`
- 默认请求头包含桌面浏览器 `User-Agent`
- 默认请求头带 `Referer: https://www.aaz.cx/`

固定首页分类如下：

- `new -> 新歌榜`
- `top -> TOP榜单`
- `singer -> 歌手`
- `playtype -> 歌单`
- `album -> 专辑`
- `mv -> 高清MV`

分类路径映射如下：

- `new -> /list/new.html`
- `top -> /list/top.html`
- `singer -> /singerlist/index/index/index/index.html`
- `playtype -> /playtype/index.html`
- `album -> /albumlist/index.html`
- `mv -> /mvlist/index.html`

## ID 设计

统一使用仓库短 ID，不在列表或搜索结果中暴露完整 URL。

`vod_id` 编码规则：

- `song:<song_id>`
- `singer:<slug>`
- `playlist:<slug>`
- `album:<slug>`
- `mv:<slug>`

目录型资源与链接前缀映射如下：

- `/s/xxx` -> `singer:xxx`
- `/p/xxx` -> `playlist:xxx`
- `/a/xxx` -> `album:xxx`
- `/v/xxx` -> `mv:xxx`

单曲资源与链接映射如下：

- `/m/<id>.html` -> `song:<id>`

`play_id` 首版只保留：

- `song:<song_id>`

内部路径还原规则：

- `song:<id>` -> `/m/<id>.html`
- `singer:<id>` -> `/s/<id>`
- `playlist:<id>` -> `/p/<id>`
- `album:<id>` -> `/a/<id>`
- `mv:<id>` -> `/v/<id>`

## 首页设计

`homeContent` 返回：

- `class`
- `list`

首页策略如下：

- 请求 `/list/new.html`
- 解析页面中的歌曲列表项
- 将歌曲链接统一编码为 `song:<id>`
- 以 `vod_id` 去重
- 返回固定分类和首页歌曲列表

首页列表项字段统一为：

- `vod_id`
- `vod_name`
- `vod_pic`
- `vod_remarks`

`homeVideoContent` 直接复用 `homeContent(False)` 的 `list`。

首版不返回 `filters`，因为当前站点分类依赖固定入口，不需要额外筛选面板。

## 分类设计

`categoryContent` 支持以下分类：

- `new`
- `top`
- `singer`
- `playtype`
- `album`
- `mv`

返回结构遵循仓库当前约定：

- `page`
- `limit`
- `total`
- `list`

不返回 `pagecount`。

各分类策略如下：

### `new` 与 `top`

- 请求对应榜单页面
- 解析歌曲列表
- 结果项编码为 `song:<id>`
- `vod_name` 使用站点卡片标题
- 若卡片存在 MV 标记，可写入 `vod_remarks`

### `singer`

- 请求歌手列表页
- 解析 `/s/` 链接的封面卡片
- 编码为 `singer:<slug>`

### `playtype`

- 请求歌单列表页
- 解析 `/p/` 链接的封面卡片
- 编码为 `playlist:<slug>`

### `album`

- 请求专辑列表页
- 解析 `/a/` 链接的封面卡片
- 编码为 `album:<slug>`

### `mv`

- 请求 MV 列表页
- 解析 `/v/` 链接的封面卡片
- 编码为 `mv:<slug>`

首版不实现翻页抓取；所有分类都按单页结果返回，`page` 仍回显请求值，`limit` 和 `total` 取当前页解析条数。

## 搜索设计

`searchContent(keyword, quick, pg)` 请求 `/so/{keyword}.html`。

搜索策略如下：

- 空关键字直接返回空分页结构
- 请求搜索结果页
- 统一扫描结果区域中的站点链接
- 根据链接前缀映射为 `song/singer/playlist/album/mv` 五类短 ID
- 对结果按 `vod_id` 去重

搜索结果字段统一为：

- `vod_id`
- `vod_name`
- `vod_pic`
- `vod_remarks`

搜索结果允许混合类型存在，不对类型做二次拆分。

## 详情设计

`detailContent` 根据 `vod_id` 分为“单曲详情”和“目录型详情”两条链路。

### 单曲详情

当 `vod_id` 为 `song:<id>` 时：

- 请求 `/m/<id>.html`
- 提取歌名、歌手、专辑、封面、时长和简介
- `vod_name` 使用解析到的歌名
- `vod_pic` 优先使用详情页封面
- `vod_remarks` 组合歌手、专辑和时长
- `vod_play_from` 固定为 `AAZ音乐`
- `vod_play_url` 生成为 `播放$song:<id>`

单曲详情不暴露下载地址、慢速下载地址和歌词地址。

### 目录型详情

当 `vod_id` 为 `singer/playlist/album/mv` 之一时：

- 根据短 ID 还原对应详情页 URL
- 提取页面标题、封面和简介
- 从页面歌曲列表中解析 `/m/<id>.html`
- 生成 `歌曲名$song:<id>` 的播放串
- `vod_play_from` 固定为 `AAZ音乐`

目录型详情只保证歌曲列表和歌曲试听，不承诺 MV 独立播放能力。即使详情类型为 `mv:<slug>`，只要页面能列出歌曲，就按目录型播放列表处理。

若详情页没有有效歌曲列表，则返回只有基础元信息、播放串为空的单对象详情。

## 播放设计

`playerContent(flag, id, vipFlags)` 只处理 `song:<id>`。

播放流程如下：

1. 解析 `id` 中的 `song_id`
2. POST `https://www.aaz.cx/js/play.php`
3. 请求体使用 `id=<song_id>&type=music`
4. 请求头补充表单提交和 `X-Requested-With`
5. 从 JSON 中提取 `url`
6. 若成功，返回 `parse=0` 的直链播放结果
7. 若失败，返回 `parse=0` 且 `url=""`

返回结构至少包含：

- `parse`
- `url`
- `header`

`header` 固定返回：

- `User-Agent`
- `Referer: https://www.aaz.cx/`

首版不接入下载接口，也不把播放失败回退到下载地址。

## 错误处理

统一遵循仓库现有的宽松容错策略：

- 页面请求失败时返回空字符串或空结果，不抛出到调用层
- 解析缺失字段时回退为空字符串
- 搜索空关键字返回空分页结构
- 未知 `vod_id` 或非法 `play_id` 返回空详情或空播放地址

空分页结构统一为：

- `{"page": 1, "limit": 0, "total": 0, "list": []}`

## 测试设计

新增 `py/tests/test_AAZ音乐.py`，使用 `unittest` 与 `unittest.mock`。

测试覆盖以下行为：

- `homeContent`
  - 返回 6 个固定分类
  - 首页歌曲卡片正确映射为 `song:<id>`
- `homeVideoContent`
  - 直接复用首页 `list`
- `categoryContent`
  - `new/top` 正确解析歌曲
  - `singer/playtype/album/mv` 正确解析目录型短 ID
  - 未知分类返回空分页结构
- `searchContent`
  - 混合结果正确映射为五类短 ID
  - 空关键字返回空分页结构
- `detailContent`
  - `song:<id>` 生成单条播放串
  - `singer/playlist/album/mv` 详情页能生成歌曲播放列表
  - 无效 `vod_id` 返回空 `list`
- `playerContent`
  - `/js/play.php` 返回 JSON 时正确映射直链
  - 非法 `play_id` 或空 `url` 时返回空播放地址

fixture 采用内嵌 HTML/JSON 文本，不依赖真实网络。

## 验证计划

实现阶段先执行最小受影响测试，再执行模块完整测试。

预期验证命令为：

```bash
cd py && python -m unittest tests.test_AAZ音乐 -v
```

本次工作完成后不新增更大范围的套件验证要求，因为实现不会修改公共层。
