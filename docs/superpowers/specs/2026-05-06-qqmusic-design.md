# QQ音乐爬虫设计

## 目标

新增一个独立的 QQ 音乐 spider，基于 `https://music.har01d.cn` 提供的 QQ Music API，实现排行榜浏览、单曲搜索、歌曲详情和播放直链解析。

## 范围

- 新增 `py/QQ音乐.py`
- 新增 `py/tests/test_QQ音乐.py`
- `base url` 固定使用 `https://music.har01d.cn`
- 支持排行榜列表浏览
- 支持排行榜歌曲详情
- 支持按关键词搜索歌曲
- 支持单曲详情
- 支持歌曲播放直链解析

## 非目标

- 不实现歌手详情、专辑详情、歌单详情
- 不实现歌词功能
- 不实现多音质切换，固定请求 `flac`
- 不实现分页翻页，除第一页外统一返回空结果
- 不改动其他已有音乐 spider
- 不修改远程订阅对应的 `txt` 文件

## 方案

### 文件与接口

新增 [py/QQ音乐.py](/home/harold/workspace/tvbox-resources/py/QQ音乐.py)，类名保持为 `Spider`，继承 `BaseSpider`，实现以下接口：

- `init()`
- `getName()`
- `homeContent()`
- `homeVideoContent()`
- `categoryContent()`
- `detailContent()`
- `searchContent()`
- `playerContent()`

整体返回结构保持与仓库内现有音乐源一致。

### 基础配置

- 站点名称：`QQ音乐`
- 基础地址：`https://music.har01d.cn`
- 固定请求头至少包含常规桌面浏览器 `User-Agent`
- 网络请求统一走辅助方法，设置 10 秒超时

### 首页与分类

`homeContent(False)` 返回固定单个分类：

- `top`: 排行榜

`homeVideoContent()` 返回空列表，不额外请求首页内容。

`categoryContent("top", "1", filter, extend)` 调用：

- `GET /api/top`

将接口返回的榜单列表原样展示为卡片列表，不做人为分组和重排。

### 数据来源

仅使用以下 4 个接口：

- `/api/top`
- `/api/search`
- `/api/song/detail`
- `/api/song/url`

不依赖文档外的隐藏接口，也不混用 QQ 音乐官方未封装接口。

### ID 约定

为让排行榜和搜索最终落到同一套播放流程，采用统一 ID 规则：

榜单：

- `top:<id>`

单曲：

- `song:<mid>`

播放：

- `qqmusic:<mid>`

`playerContent()` 只识别 `qqmusic:<mid>`，其他输入统一返回空地址。

### 分类列表

`categoryContent(tid, pg, filter, extend)` 逻辑：

- 当 `pg != "1"` 时，直接返回空列表
- 当 `tid != "top"` 时，直接返回空列表
- 请求 `/api/top`
- 校验返回 `code == 0`
- 遍历 `data.list`

每个榜单卡片至少包含：

- `vod_id = top:<id>`
- `vod_name = name`
- `vod_pic = cover`，缺失时为空串
- `vod_remarks = intro`，缺失时为空串

不返回 `pagecount`。

### 详情

`detailContent(ids)` 支持两类输入。

榜单详情 `top:*`：

- 请求 `/api/top?id=<id>&num=100`
- 校验返回 `code == 0`
- 从榜单详情中的歌曲列表提取：
  - `mid`
  - `title`
  - `singer`
- 歌手数组使用 `/` 连接名称
- 输出单条播放线路：
  - `QQ音乐`
- `vod_play_url` 格式为：
  - `歌名 - 歌手$qqmusic:<mid>`

榜单详情返回字段至少包含：

- `vod_id`
- `vod_name`
- `vod_pic`
- `vod_content`
- `vod_play_from`
- `vod_play_url`

单曲详情 `song:*`：

- 请求 `/api/song/detail?mid=<mid>`
- 校验返回 `code == 0`
- 提取：
  - `mid`
  - `title`
  - `singer`
  - `cover`
  - `album`
  - `publish_date`
- 歌手数组使用 `/` 连接名称
- `vod_play_from = QQ音乐`
- `vod_play_url = 歌名 - 歌手$qqmusic:<mid>`

单曲详情返回字段至少包含：

- `vod_id`
- `vod_name`
- `vod_pic`
- `vod_actor`
- `vod_remarks`
- `vod_play_from`
- `vod_play_url`

`vod_remarks` 优先使用专辑名；如果专辑名不可用，则回退到发行日期；都没有则为空串。

### 搜索

`searchContent(key, quick, pg="1")` 逻辑：

- 关键词为空时返回空列表
- 当 `pg != "1"` 时返回空列表
- 请求 `/api/search?keyword=<key>&type=song&num=20&page=1`
- 校验返回 `code == 0`
- 遍历 `data.list`

每个搜索结果至少提取：

- `mid`
- `title`
- `singer`
- `cover`

搜索结果映射为：

- `vod_id = song:<mid>`
- `vod_name = title`
- `vod_pic = cover`，缺失时为空串
- `vod_remarks = 歌手名拼接`

搜索结果点击后进入单曲详情流程，不额外构造虚拟榜单。

### 播放

`playerContent(flag, id, vipFlags)` 逻辑：

- 命中 `qqmusic:<mid>` 时，请求 `/api/song/url?mid=<mid>&quality=flac`
- 校验返回 `code == 0`
- 优先取接口返回的播放直链字段
- 如果接口已自动降级到较低音质，直接使用其返回地址

返回：

- 成功解析时 `parse = 0`
- `header = {}`
- 地址为空时仍保持 `parse = 0`，但 `url = ""`

不额外处理音质选择，也不增加其他播放线路。

### 容错

所有远程请求统一通过辅助方法处理：

- 固定 `User-Agent`
- 10 秒超时
- HTTP 非 200 时返回空对象
- JSON 解析失败时返回空对象
- `code != 0` 时按失败处理

异常和源站结构变化时，统一降级为空结果，不向上层抛异常。

具体要求：

- 榜单接口异常时返回空分类列表
- 榜单详情异常时返回空 `list`
- 单曲详情异常时返回空 `list`
- 搜索接口异常时返回空搜索结果
- 播放解析失败时返回空播放地址
- 非法 `vod_id` 或播放 ID 返回空结果

## 测试

新增 `py/tests/test_QQ音乐.py`，沿用现有 `unittest + patch` 模式，不打真实网络。

至少覆盖以下场景：

- `homeContent()` 返回固定一个 `排行榜` 分类
- `homeVideoContent()` 返回空列表
- `categoryContent()` 能将 `/api/top` 榜单列表映射成卡片
- `categoryContent()` 在 `pg != 1` 或非法分类时返回空列表
- `detailContent(top:*)` 能输出榜单歌曲的单线路播放列表
- `detailContent(song:*)` 能从 `/api/song/detail` 构造单曲详情
- `detailContent()` 对非法 `vod_id` 返回空列表
- `searchContent()` 能将 `/api/search` 歌曲结果映射为 `song:<mid>`
- `searchContent()` 在空关键词或非第一页时返回空列表
- `playerContent()` 能从 `/api/song/url` 解析直链
- `playerContent()` 在无地址或非法播放 ID 时返回空结果

## 风险

- `/api/song/url` 的实际返回字段名可能随部署版本变化，需要实现时优先兼容文档示例和常见字段
- `/api/top` 榜单列表和榜单详情的字段命名可能并不完全一致，实现时要先以测试约束出统一映射
- 部署站 `https://music.har01d.cn` 与文档默认示例地址不同，若该实例后续升级落后于文档，可能出现字段差异

实现应优先保持接口稳定和空结果降级，不为了“尽量返回内容”而引入额外猜测逻辑。
