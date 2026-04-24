# 世纪音乐 Python 爬虫设计

## 目标

在当前 Python 仓库中新增一个符合 `base.spider.Spider` 接口的世纪音乐爬虫，能力参考用户提供的 OmniBox JS 实现，但交付物遵循当前仓库的单文件 Spider 结构和 `unittest` 测试约定。

首版仅覆盖仓库里最常用的五个接口：

- 首页
- 分类
- 搜索
- 详情
- 播放

## 范围

本次实现包含：

- 新增独立脚本 `py/世纪音乐.py`
- 新增独立测试 `py/tests/test_世纪音乐.py`
- 首页固定分类与推荐内容解析
- 分类列表解析
- 关键词搜索解析
- 歌曲、MV、歌单、歌手、排行榜详情解析
- 歌曲与 MV 播放直链拼装
- 针对短 ID、字段回退、空结果和播放结果增加离线单测

本次实现不包含：

- 歌词抓取与返回
- 首页运行时缓存
- 修改 `py/base/` 公共层
- 引入新的第三方依赖
- 真实联网集成测试
- 复杂重试、反爬绕过和占位图补全

## 方案选择

采用“按仓库 Python Spider 形态重写站点逻辑”的方案，而不是直接把 OmniBox JS 原样翻译成 Python。

原因如下：

- 当前仓库交付物是 Python Spider，而不是 OmniBox 脚本
- 仓库现有测试体系围绕 `homeContent/categoryContent/detailContent/searchContent/playerContent`
- 参考 JS 中的核心能力可以映射到仓库接口，但其缓存和返回结构不适合直接搬运
- 直接使用短 ID 和离线 HTML 测试，能降低 host 变化、缓存缺失和运行时状态对结果的影响

## 模块边界

新增模块 `py/世纪音乐.py` 只负责该站点逻辑，不修改 `py/base/`。

模块对外实现以下接口：

- `init`
- `getName`
- `homeContent`
- `homeVideoContent`
- `categoryContent`
- `detailContent`
- `searchContent`
- `playerContent`

模块内部使用 helper 收敛 URL 和解析逻辑：

- `_build_url`
  - 补全站点绝对地址
- `_fetch_html`
  - 统一请求页面并返回文本
- `_load_html`
  - 将 HTML 转成可 XPath 的文档对象
- `_clean_text`
  - 规范化文本、去掉多余空白和站点装饰词
- `_extract_site_id`
  - 从站点链接中提取原始资源 ID
- `_encode_vod_id`
  - 将站点资源编码为仓库短 `vod_id`
- `_decode_vod_id`
  - 将短 `vod_id` 还原为站点路径和资源类型
- `_encode_play_id`
  - 将播放资源编码为短播放 ID
- `_decode_play_id`
  - 将短播放 ID 还原为直链参数
- `_parse_home_items`
  - 首页推荐解析
- `_parse_list_cards`
  - 分类和搜索卡片解析
- `_parse_rank_detail`
  - 排行榜详情解析
- `_parse_song_detail`
  - 歌曲详情解析
- `_parse_mv_detail`
  - MV 详情解析
- `_parse_playlist_detail`
  - 歌单详情解析
- `_parse_singer_detail`
  - 歌手详情解析

## 站点配置

固定站点配置如下：

- 站点名：`世纪音乐`
- 根地址：`https://www.4c44.com`
- 默认请求头包含桌面浏览器 `User-Agent`
- 默认请求头带 `Referer: https://www.4c44.com/`

固定首页分类如下：

- `home -> 首页推荐`
- `rank_list -> 排行榜`
- `playlist -> 歌单`
- `singer -> 歌手`
- `mv -> MV`

首版保留与参考实现一致的内容面，但不引入运行时缓存层。

## ID 设计

为避免在列表层暴露完整 URL，统一使用仓库短 ID。

`vod_id` 编码规则：

- `rank:<榜单标识>`
- `song:<song_id>`
- `mv:<mv_id>`
- `playlist:<slug或id>`
- `singer:<slug或id>`

`play_id` 编码规则：

- `music:<song_id>`
- `vplay:<mv_id>:1080`

内部路径还原规则：

- `song:<id>` -> `/mp3/<id>.html`
- `mv:<id>` -> `/mp4/<id>.html`
- `playlist:<id>` -> `/playlist/<id>.html`
- `singer:<id>` -> `/singer/<id>.html`
- `rank:<id>` -> `/list/<id>.html`

首页推荐卡片直接编码为真实短 ID，不依赖额外缓存命中。

## 首页设计

`homeContent` 返回：

- `class`
- `filters`
- `list`

首页推荐解析策略：

- 请求首页 HTML
- 从歌曲推荐区提取歌曲卡片
- 从 MV 推荐区提取 MV 卡片
- 根据链接前缀判断资源类型
- 统一映射为短 `vod_id`
- 按 `vod_id` 去重

首页推荐列表项统一字段：

- `vod_id`
- `vod_name`
- `vod_pic`
- `vod_remarks`

`homeVideoContent` 直接复用首页的 `list`，避免重复解析逻辑。

## 分类设计

`categoryContent` 支持以下分类：

- `home`
- `rank_list`
- `playlist`
- `singer`
- `mv`

返回结构遵循仓库当前约定：

- `page`
- `limit`
- `total`
- `list`

不返回 `pagecount`。

各分类策略如下：

### `home`

- 直接复用首页推荐列表
- `page=1`
- `limit` 与 `total` 使用当前列表长度

### `rank_list`

- 使用模块内固定榜单映射
- 每页返回固定数量的榜单卡片
- 榜单项 `vod_id` 为 `rank:<榜单标识>`
- 榜单项不依赖站点页面结构

### `playlist`

- 根据筛选参数构造歌单页 URL
- 从歌单列表容器解析 `/playlist/` 链接
- 列表项编码为 `playlist:<id>`

### `singer`

- 根据筛选参数构造歌手页 URL
- 从歌手列表容器解析 `/singer/` 链接
- 列表项编码为 `singer:<id>`

### `mv`

- 根据筛选参数构造 MV 页 URL
- 从 MV 列表容器解析 `/mp4/` 链接
- 列表项编码为 `mv:<id>`

筛选器首版沿用参考实现中的三组能力：

- `singer`
  - 性别、地区、字母
- `mv`
  - 地区、类型、排序
- `playlist`
  - 语种、风格

## 搜索设计

`searchContent` 行为如下：

- 空关键词直接返回空结构
- 非空关键词请求站点搜索页
- 统一扫描搜索结果中的歌曲、MV、歌单、歌手链接
- 根据链接前缀判断资源类型并编码为短 `vod_id`
- 按 `vod_id` 去重

返回结构：

- `page`
- `limit`
- `total`
- `list`

空关键词返回固定结果：

- `{"page": 1, "limit": 0, "total": 0, "list": []}`

## 详情设计

`detailContent` 按 `vod_id` 前缀分流，不依赖首页缓存。

### 排行榜详情

- 请求 `/list/<rank>.html`
- 解析榜单页歌曲链接
- 每首歌生成 `music:<song_id>` 播放 ID
- 输出单线路 `vod_play_from`

### 歌曲详情

- 请求 `/mp3/<song_id>.html`
- 解析标题、歌手、封面
- 输出单条播放项
- `vod_play_url` 格式为 `歌曲名$music:<song_id>`

### MV 详情

- 请求 `/mp4/<mv_id>.html`
- 解析标题、歌手、封面
- 输出单条播放项
- `vod_play_url` 格式为 `标题$vplay:<mv_id>:1080`

### 歌单详情

- 请求 `/playlist/<id>.html`
- 解析歌单标题、封面和歌曲列表
- 播放列表中的每个条目编码为 `music:<song_id>`

### 歌手详情

- 请求 `/singer/<id>.html`
- 解析歌手名称、封面、简介和歌曲列表
- 播放列表中的每个条目编码为 `music:<song_id>`

详情对象至少包含以下字段：

- `vod_id`
- `vod_name`
- `vod_pic`
- `vod_remarks`
- `vod_content`
- `vod_play_from`
- `vod_play_url`

站点能稳定提供时再补充：

- `vod_actor`
- `type_name`

## 播放设计

`playerContent` 只负责短播放 ID 到可播放 URL 的还原，不抓歌词。

规则如下：

- `music:<song_id>`
  - 还原为 `https://www.4c44.com/data/down.php?ac=music&id=<song_id>`
- `vplay:<mv_id>:1080`
  - 还原为 `https://www.4c44.com/data/down.php?ac=vplay&id=<mv_id>&q=1080`

返回结构遵循仓库常见模式：

- `parse=0`
- `url=<直链>`
- `header`

默认请求头返回：

- `User-Agent`
- `Referer`

若播放 ID 无法解析，则返回空 URL 和 `parse=0`，不抛异常。

## 错误处理设计

错误处理原则为“优先返回空结果，不中断主链路”。

- 页面请求失败
  - 首页、分类、搜索返回空列表
- 分类页结构变化
  - 当前分类返回空列表，不影响其他分类
- 搜索页无匹配结果
  - 返回空列表
- 详情页解析失败
  - 返回 `{"list": []}`
- 播放 ID 无法解析
  - 返回空 URL

不在首版加入复杂重试和缓存回退。

## 测试设计

新增测试文件 `py/tests/test_世纪音乐.py`，使用 `unittest` 和 `unittest.mock`，不访问真实网络。

测试范围如下：

- `homeContent`
  - 返回固定分类与筛选器
  - 能从首页 HTML 解析歌曲和 MV 推荐
- `homeVideoContent`
  - 复用首页列表
- `categoryContent`
  - `rank_list` 返回固定榜单分页
  - `playlist` 能解析歌单卡片
  - `singer` 能解析歌手卡片
  - `mv` 能解析 MV 卡片
  - 未知分类返回空结果
- `searchContent`
  - 空关键词返回空结果
  - 非空关键词能将歌曲、MV、歌单、歌手映射成短 `vod_id`
- `detailContent`
  - `rank:<id>` 能组装歌曲播放列表
  - `song:<id>` 能组装歌曲详情
  - `mv:<id>` 能组装 MV 详情
  - `playlist:<id>` 能组装歌单详情
  - `singer:<id>` 能组装歌手详情
- `playerContent`
  - `music:<id>` 返回歌曲直链
  - `vplay:<id>:1080` 返回 MV 直链
  - 非法播放 ID 返回空 URL

## 风险与约束

首版实现依赖站点当前 HTML 结构，因此有以下约束：

- 列表解析对 CSS 类名和链接前缀有一定依赖
- 歌单和歌手详情依赖页面内歌曲列表容器
- 搜索结果若结构分散，需要在实现中优先选择稳定容器，并在测试中覆盖字段回退

这些风险都限制在站点模块内部，不扩散到公共层。
