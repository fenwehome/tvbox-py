# 酷狗音乐爬虫设计

## 目标

新增一个独立的酷狗音乐 spider，支持榜单浏览、单曲搜索、歌曲播放、MV 播放，以及付费歌曲的第三方网页兜底。

## 范围

- 新增 `py/酷狗音乐.py`
- 新增 `py/tests/test_酷狗音乐.py`
- 支持固定三类榜单：`热门榜`、`特色榜`、`全球榜`
- 支持榜单歌曲详情，输出 `MP3`、`MV` 两条播放线路
- 支持按关键词搜索歌曲
- 支持歌曲播放直链解析
- 支持 MV 播放直链解析
- 支持歌曲因“要付费”无法直出时，回退到 `sq0527` 搜索页抓取下载链接

## 非目标

- 不实现专辑、歌手、歌单等非歌曲搜索结果
- 不实现分页搜索和分页榜单浏览，除第一页外统一返回空结果
- 不为 MV 提供第三方兜底来源
- 不改动其他已有音乐 spider
- 不同步维护远程订阅指向文件，除非后续单独需要

## 方案

### 文件与接口

新增 [py/酷狗音乐.py](/home/harold/workspace/tvbox-resources/py/酷狗音乐.py)，类名保持为 `Spider`，继承 `BaseSpider`，实现以下接口：

- `init()`
- `getName()`
- `homeContent()`
- `homeVideoContent()`
- `categoryContent()`
- `detailContent()`
- `searchContent()`
- `playerContent()`

整体返回结构保持与仓库内现有音乐源一致。

### 分类

`homeContent(False)` 返回固定分类，不依赖首页推荐数据：

- `hot`: 热门榜
- `special`: 特色榜
- `global`: 全球榜

`homeVideoContent()` 直接复用首页列表语义，返回空 `list` 即可，不额外抓首页内容。

### 数据来源

榜单相关数据使用酷狗公开接口：

- 榜单列表接口：返回所有榜单元信息
- 榜单歌曲接口：返回指定榜单下歌曲列表
- 歌曲信息接口：返回单曲播放地址、备选地址、付费提示
- MV 信息接口：返回 MV 下载地址

付费歌曲兜底使用第三方网页：

- 搜索页：`https://www.sq0527.cn/search?ac=<keyword>`
- 详情页：从搜索结果进入后提取 `#btn-download-mp3`

搜索功能使用酷狗网页或 H5 搜索结果，只保留歌曲项。实现时优先选择最稳定、最容易通过测试模拟的数据入口；如果有多个候选入口，应优先结构化 JSON，而不是脆弱的纯 HTML 文本匹配。

### ID 约定

为了让榜单和搜索最终落到同一套播放流程，采用统一的 `vod_id` / `play_id` 规则。

榜单：

- 榜单卡片 `vod_id` 使用 `rank:<rank_id>`

搜索歌曲：

- 搜索结果 `vod_id` 使用可还原单曲信息的编码
- 推荐格式为 `song:<play_hash>:<mvhash>:<song_name>:<author_name>`
- `mvhash` 允许为空
- `song_name`、`author_name` 需要经过可逆编码，避免分隔符冲突

播放项：

- MP3 使用 `kugou-mp3-<hash>`
- MV 使用 `kugou-mv-<hash>`

`playerContent()` 只识别以上两类播放 id，其他输入统一返回空地址。

### 分类列表

`categoryContent(tid, pg, filter, extend)` 逻辑：

- 当 `pg != "1"` 时，直接返回空列表
- 当 `tid` 为 `hot`、`special`、`global` 时，请求榜单列表接口
- 依据酷狗榜单元数据中的 `classify` 字段筛选榜单

分类映射按参考逻辑保留：

- `hot`: `classify == "2"`
- `special`: `classify in {"3", "5"}`
- `global`: `classify in {"4", "2"}`

返回的榜单卡片至少包含：

- `vod_id`
- `vod_name`
- `vod_pic`
- `vod_remarks`

### 详情

`detailContent(ids)` 支持两类输入。

榜单详情 `rank:*`：

- 请求榜单歌曲接口
- 逐条提取 `filename`、`sqhash`、`hash`、`mvhash`
- 歌曲播放 hash 优先使用 `sqhash`，为空时回退到 `hash`
- 输出两个播放线路：
  - `MP3`
  - `MV`
- 没有 `mvhash` 的歌曲不进入 `MV` 线路

单曲详情 `song:*`：

- 不额外请求歌曲详情页
- 直接用 `vod_id` 中保存的信息构造单曲详情
- 至少输出 `vod_name`、`vod_play_from`、`vod_play_url`
- 若 `mvhash` 非空，则同时输出 `MV` 线路；否则仅输出 `MP3`

### 搜索

`searchContent(key, quick, pg="1")` 逻辑：

- 关键词为空时返回空列表
- 当 `pg != "1"` 时返回空列表
- 调用酷狗搜索入口
- 仅保留歌曲类型结果
- 搜索结果阶段尽量提取：
  - `song_name`
  - `author_name`
  - `play_hash`
  - `mvhash`
- 直接编码为搜索结果 `vod_id`

搜索结果点击后，应进入单曲详情流程，而不是再走一层“虚拟榜单”。

### 播放

`playerContent(flag, id, vipFlags)` 逻辑：

MP3：

- 命中 `kugou-mp3-<hash>` 时，请求歌曲信息接口
- 正常场景优先取 `url`
- `url` 为空时，再取 `backup_url[0]`
- 若接口返回 `error` 包含“要付费”，则触发第三方兜底：
  - 用 `song_name` 搜索 `sq0527`
  - 在搜索结果中同时匹配 `song_name` 和 `author_name`
  - 命中后进入详情页提取下载按钮链接

MV：

- 命中 `kugou-mv-<hash>` 时，请求 MV 信息接口
- 优先取 `mvdata.sq.downurl`
- 次选 `mvdata.le.downurl`

返回：

- 成功解析时 `parse = 0`
- 地址为空时仍保持 `parse = 0`，但 `url = ""`
- MP3 可返回空 header
- MV 返回固定 `User-Agent` header

### 容错

所有远程请求统一通过辅助方法处理：

- 固定 `User-Agent`
- 10 秒超时
- JSON 解析失败时返回空对象
- HTML 获取失败时返回空字符串

异常和源站结构变化时，统一降级为空结果，不向上层抛异常。

具体要求：

- 榜单接口异常时返回空分类列表
- 搜索接口异常时返回空搜索结果
- 付费兜底搜索失败时返回空播放地址
- MV 解析失败时返回空播放地址

## 测试

新增 `py/tests/test_酷狗音乐.py`，沿用现有 `unittest + patch` 模式，不打真实网络。

至少覆盖以下场景：

- `homeContent()` 返回固定三类分类
- `homeVideoContent()` 返回空列表
- `categoryContent()` 能按 `hot`、`special`、`global` 过滤榜单
- `categoryContent()` 在 `pg != 1` 或非法分类时返回空列表
- `detailContent(rank:*)` 能输出 `MP3`、`MV` 双线路
- `detailContent(rank:*)` 会忽略没有 `mvhash` 的 MV 条目
- `detailContent(song:*)` 能从编码后的 `vod_id` 构造单曲详情
- `searchContent()` 只返回歌曲结果，并正确编码 `vod_id`
- `searchContent()` 在空关键词或非第一页时返回空列表
- `playerContent()` 能解析普通 MP3
- `playerContent()` 在 MP3 付费时走第三方兜底
- `playerContent()` 能解析 MV
- `playerContent()` 对非法播放 id 返回空地址

## 风险

- 酷狗搜索入口可能存在多套返回格式，需优先选择更稳定的结构化入口
- `sq0527` 属于第三方页面，HTML 结构变化会直接影响付费歌曲兜底
- 搜索结果如果无法稳定返回 `author_name`，会降低兜底命中率
- 使用 `sqhash` 与 `hash` 的回退策略依赖当前接口字段约定，后续可能变更

实现应优先保持接口稳定和空结果降级，不为了“尽量返回内容”而引入脆弱的隐式猜测逻辑。
