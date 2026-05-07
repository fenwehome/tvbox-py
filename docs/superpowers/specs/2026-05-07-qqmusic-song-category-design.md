# QQ音乐歌曲分类设计

## 目标

在现有 QQ 音乐 spider 基础上，新增“歌曲”固定分类，支持按 `type` 分页浏览新歌首发列表，并复用现有 `song:*` 单曲详情链路。

## 范围

- 修改 `py/QQ音乐.py`
- 修改 `py/tests/test_QQ音乐.py`
- `homeContent()` 从 `排行榜`、`歌手`、`专辑`、`歌单` 扩展为 `歌曲`、`排行榜`、`歌手`、`专辑`、`歌单`
- 支持 `GET /api/song?type=<type>&page=<pg>` 歌曲分页列表
- 支持通过 `filters["song"]` 暴露 `type` 筛选

## 非目标

- 不新增歌曲播放协议
- 不修改现有 `detailContent("song:*")` 和 `playerContent()` 行为
- 不修改现有搜索结果映射
- 不接入除 `type` 外的其他歌曲筛选参数
- 不额外实现歌曲 MV、歌词、评论或榜单联动

## 方案

### 分类

`homeContent(False)` 返回五个固定分类，顺序固定为：

- `song`: 歌曲
- `top`: 排行榜
- `singer`: 歌手
- `album`: 专辑
- `playlist`: 歌单

`homeVideoContent()` 保持返回空列表。

### 筛选

`homeContent(False)` 新增：

- `filters["song"]`

仅暴露一个筛选项：

- `key = type`
- `name = 地区`
- `init = 5`

可选值固定为：

- `最新` → `5`
- `内地` → `1`
- `港台` → `6`
- `欧美` → `2`
- `韩国` → `4`
- `日本` → `3`

现有 `filters["album"]` 保持不变，不与 `song` 共用筛选配置。

### 数据来源

歌曲分类浏览仅使用以下接口：

- `/api/song?type=<type>&page=<pg>`

不新增其他列表接口，也不改动已存在的 `/api/song/detail?mid=<mid>` 单曲详情能力。

### ID 约定

沿用现有 ID 规则：

- 歌曲：`song:<mid>`
- 排行榜：`top:<id>`
- 歌手：`singer:<singer_mid>`
- 专辑：`album:<album_mid>`
- 歌单：`playlist:<tid>`
- 播放：`qqmusic:<mid>`

歌曲分类列表中的卡片点击后直接进入现有 `song:*` 详情分支。

### 歌曲列表

`categoryContent("song", pg, filter, extend)` 逻辑：

- `pg` 为空时按 `1` 处理
- `extend` 非字典时按空字典处理
- 类型参数取 `extend["type"]`
- `type` 缺失、空值、非法值时回退到 `5`
- 仅接受 `5`、`1`、`6`、`2`、`4`、`3`
- 请求 `/api/song?type=<type>&page=<pg>`
- 校验返回 `code == 0`
- 遍历 `data.songlist`

每个歌曲卡片至少提取：

- `mid`
- `title`
- `name`
- `singer`
- `time_public`

映射为：

- `vod_id = song:<mid>`
- `vod_name = title`，缺失时回退 `name`
- `vod_pic = https://music.har01d.cn/api/song/cover/content?mid=<mid>&size=300`
- `vod_remarks`
  - 优先格式：`歌手名  发行日期`
  - 如果只有歌手名则只显示歌手名
  - 如果只有发行日期则只显示发行日期
  - 两者都没有则为空串

歌手名生成规则：

- 遍历 `singer`
- 使用 `name` 字段
- 多个歌手以 `/` 拼接

分页返回：

- `page = 当前页`
- `limit = 当前页条数`
- `total = 当前页条数`
- `list = 当前页歌曲卡片`

不返回 `pagecount`。

### 兼容性

当前 spider 已经存在：

- `song:*` 详情
- `qqmusic:<mid>` 播放协议
- 歌曲搜索结果封面组装规则

歌曲分类实现应直接复用现有封面 URL 规则和 `song:*` 详情入口，不新增第二套歌曲详情或播放链路，避免分类、搜索、详情之间的协议分叉。

### 容错

所有歌曲分类请求继续走统一 JSON 请求助手。

具体要求：

- `/api/song?type=<type>&page=<pg>` 请求失败时返回空列表
- `mid` 缺失的列表项直接跳过
- `title`、`name` 都缺失的列表项直接跳过
- `singer` 缺失、为空或单项字段缺失时按空歌手名处理，不抛异常
- `time_public` 缺失时允许只显示歌手名
- 非法 `type` 值统一回退到 `5`

## 测试

至少新增以下测试：

- `homeContent()` 返回 `song`、`top`、`singer`、`album`、`playlist` 五个固定分类，且顺序正确
- `filters["song"]` 包含 `key = type`、`init = 5` 和 6 个选项
- `categoryContent("song", "1", ..., {})` 默认请求 `type=5&page=1`
- `categoryContent("song", "2", ..., {"type": "3"})` 请求 `type=3&page=2`
- `categoryContent("song", ...)` 能映射 `song:<mid>`
- `categoryContent("song", ...)` 能正确拼接 `singer[].name`
- `categoryContent("song", ...)` 能正确生成歌曲封面 URL
- `categoryContent("song", ...)` 能正确生成 `歌手名  发行日期` 备注
- `categoryContent("song", ...)` 在非法 `type` 时回退到 `5`
- `categoryContent("song", ...)` 在 `mid` 或标题缺失时跳过坏数据
- `/api/song` 请求失败时返回空列表

## 风险

- 列表接口未提供总量字段时，实现只能继续沿用“当前页条数”作为 `total`
- 返回字段同时存在 `title` 和 `name`，必须明确优先级，避免不同列表项显示不一致
- 歌曲封面使用现有 cover 接口拼装时依赖 `mid`，因此 `mid` 缺失的坏数据必须直接跳过

实现应优先保持新增歌曲分类能力与现有 QQ 音乐 spider 的搜索、详情和播放器协议一致，不为了展示更多歌曲字段而扩大改动范围。
