# QQ音乐歌单分类设计

## 目标

在现有 QQ 音乐 spider 基础上，新增歌单分类列表和歌单详情能力，支持分页浏览歌单，并在歌单详情中输出歌曲播放列表。

## 范围

- 修改 `py/QQ音乐.py`
- 修改 `py/tests/test_QQ音乐.py`
- `homeContent()` 从 `排行榜`、`歌手` 扩展为 `排行榜`、`歌手`、`歌单`
- 支持 `GET /api/playlist` 歌单分页列表
- 支持 `GET /api/playlist?id=<tid>` 歌单详情和歌曲列表

## 非目标

- 不新增歌单播放协议
- 不修改现有 `playerContent()` 的 `qqmusic:<mid>` 协议
- 不在 `searchContent()` 中混入歌单搜索结果
- 不处理歌单筛选参数或推荐标签筛选
- 不实现歌单歌曲的 MV、歌词、专辑扩展信息

## 方案

### 分类

`homeContent(False)` 返回三个固定分类：

- `top`: 排行榜
- `singer`: 歌手
- `playlist`: 歌单

`homeVideoContent()` 保持返回空列表。

### 数据来源

歌单能力仅使用以下接口：

- `/api/playlist`
- `/api/playlist?id=<tid>`

不引入其他文档外接口。

### ID 约定

扩展现有 ID 规则，新增歌单详情 ID：

- 榜单：`top:<id>`
- 单曲：`song:<mid>`
- 歌手：`singer:<singer_mid>`
- 歌单：`playlist:<tid>`
- 播放：`qqmusic:<mid>`

歌单详情中的歌曲播放项仍然复用现有 `qqmusic:<mid>`，不新增播放器分支。

### 歌单列表

`categoryContent("playlist", pg, filter, extend)` 逻辑：

- `pg` 为空时按 `1` 处理
- 请求 `/api/playlist?page=<pg>`
- 校验返回 `code == 0`
- 遍历 `data.List`
- 每项从 `item.Playlist.basic` 提取基础信息

每个歌单卡片至少提取：

- `tid`
- `title`
- `cover`
- `desc`
- `creator.nick`
- `song_cnt`

映射为：

- `vod_id = playlist:<tid>`
- `vod_name = title`
- `vod_pic` 优先 `cover.medium_url`，其次 `cover.big_url`、`cover.default_url`
- `vod_remarks = creator.nick or ""`

分页返回：

- `page = 当前页`
- `limit = 当前页条数`
- `total = 当前页条数`
- `list = 当前页歌单卡片`

不返回 `pagecount`。

### 歌单详情

`detailContent(ids)` 新增对 `playlist:*` 的支持：

- 请求 `/api/playlist?id=<tid>`
- 校验返回 `code == 0`
- 基础信息优先从以下任一层级提取：
  - `data.Playlist.basic`
  - `data.basic`
  - `data`
- 歌曲列表优先从以下任一层级提取：
  - `data.songlist`
  - `data.Playlist.songlist`

详情页字段映射：

- `vod_id = playlist:<tid>`
- `vod_name = title`
- `vod_pic = cover`
- `vod_remarks = 创建者: <nick>` 或空串
- `vod_content = desc`
- `vod_play_from = QQ音乐`
- `vod_play_url = 歌曲播放列表`

### 歌单歌曲列表

歌单详情中的 `songlist` 每项至少提取：

- `mid`
- `title`
- `name`
- `singer`
- `subtitle`
- `time_public`

歌曲播放项生成规则：

- 只处理有 `mid` 的歌曲
- 显示名优先 `title`，没有则回退到 `name`
- 如果同时缺 `title` 和 `name`，直接跳过
- 歌手名使用 `singer` 数组并复用现有歌曲归一化逻辑拼接
- 播放项格式为：
  - `歌名 - 歌手$qqmusic:<mid>`

### 兼容性

当前 spider 已存在用于歌曲标签和播放串拼接的辅助逻辑。歌单详情实现应直接复用这套“歌名 - 歌手”的标签格式，不应修改已有榜单、歌手详情、搜索结果的标签格式。

### 容错

所有歌单相关请求继续走统一 JSON 请求助手。

具体要求：

- `/api/playlist?page=<pg>` 请求失败时返回空列表
- `/api/playlist?id=<tid>` 请求失败时返回空 `list`
- `tid` 缺失的列表项直接跳过
- `songlist` 缺失时仍返回歌单详情，但 `vod_play_url = ""`
- `mid` 缺失的歌曲直接跳过
- `title`、`name` 都缺失的歌曲直接跳过
- `singer` 缺失或为空的歌曲直接跳过
- `cover`、`desc`、`creator.nick` 缺失时用空串降级

## 测试

至少新增以下测试：

- `homeContent()` 返回 `top`、`singer`、`playlist` 三个固定分类
- `categoryContent("playlist", "1", ...)` 能映射 `data.List[].Playlist.basic`
- `categoryContent("playlist", "2", ...)` 会继续按页码请求
- `categoryContent("playlist", ...)` 能正确选择封面 URL
- `categoryContent("playlist", ...)` 在 `tid` 缺失时跳过坏数据
- `detailContent("playlist:<tid>")` 能构造歌单基础详情
- `detailContent("playlist:<tid>")` 能从 `songlist` 生成播放列表
- `detailContent("playlist:<tid>")` 能生成 `歌名 - 歌手$qqmusic:<mid>`
- `detailContent("playlist:<tid>")` 在无歌曲时仍返回歌单详情
- 非法 `playlist` ID 返回空 `list`

## 风险

- `/api/playlist` 示例中未明确页码参数名和总量字段，实现时需要先兼容当前部署的真实入参行为
- 歌单详情的基础信息层级可能和列表接口不同，必须通过小型归一化助手统一
- 歌单详情中的 `songlist` 若后续出现缺失 `singer` 的异常返回，实现会直接跳过这些坏数据

实现应优先保持歌单能力与现有 QQ 音乐 spider 的分类、详情、播放器协议一致，不为了展示更多字段而破坏已工作的排行榜、歌手和单曲能力。
