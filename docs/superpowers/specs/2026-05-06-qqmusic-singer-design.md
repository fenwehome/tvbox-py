# QQ音乐歌手分类设计

## 目标

在现有 QQ 音乐 spider 基础上，新增歌手分类列表和歌手详情能力，支持分页浏览歌手，并在歌手详情中输出热门歌曲播放列表。

## 范围

- 修改 `py/QQ音乐.py`
- 修改 `py/tests/test_QQ音乐.py`
- `homeContent()` 从单一 `排行榜` 分类扩展为 `排行榜`、`歌手` 两个固定分类
- 支持 `GET /api/singer?page=<pg>` 歌手分页列表
- 支持 `GET /api/singer?mid=<singer_mid>` 歌手详情和热门歌曲

## 非目标

- 不新增歌手播放协议
- 不修改现有 `playerContent()` 的 `qqmusic:<mid>` 协议
- 不在 `searchContent()` 中混入歌手搜索结果
- 不接入歌手筛选参数 `area/sex/genre/index`
- 不实现歌手简介、专辑、MV、相似歌手等扩展内容

## 方案

### 分类

`homeContent(False)` 返回两个固定分类：

- `top`: 排行榜
- `singer`: 歌手

`homeVideoContent()` 保持返回空列表。

### 数据来源

歌手能力仅使用以下接口：

- `/api/singer?page=<pg>`
- `/api/singer?mid=<singer_mid>`

不引入其他文档外接口。

### ID 约定

扩展现有 ID 规则，新增歌手详情 ID：

- 榜单：`top:<id>`
- 单曲：`song:<mid>`
- 歌手：`singer:<singer_mid>`
- 播放：`qqmusic:<mid>`

歌手热门歌曲的播放项仍然复用现有 `qqmusic:<mid>`，不新增播放器分支。

### 歌手列表

`categoryContent("singer", pg, filter, extend)` 逻辑：

- `pg` 为空时按 `1` 处理
- 请求 `/api/singer?page=<pg>`
- 校验返回 `code == 0`
- 遍历 `data.singerlist`

每个歌手卡片至少提取：

- `singer_mid`
- `singer_name`
- `singer_pic`
- `country`
- `other_name`

映射为：

- `vod_id = singer:<singer_mid>`
- `vod_name = singer_name`
- `vod_pic = singer_pic`
- `vod_remarks = other_name or country or ""`

分页返回：

- `page = 当前页`
- `limit = 当前页条数`
- `total = 当前页条数`
- `list = 当前页歌手卡片`

不返回 `pagecount`。

### 歌手详情

`detailContent(ids)` 新增对 `singer:*` 的支持：

- 请求 `/api/singer?mid=<singer_mid>`
- 校验返回 `code == 0`
- 从 `data` 提取：
  - `mid`
  - `name`
  - `fans`
  - `pic`
  - `songs`

详情页字段映射：

- `vod_id = singer:<mid>`
- `vod_name = name`
- `vod_pic = pic`
- `vod_remarks = 粉丝数: <fans>`，没有则空串
- `vod_content = ""`
- `vod_play_from = QQ音乐`
- `vod_play_url = 热门歌曲列表`

热门歌曲列表生成规则：

- 遍历 `songs`
- 只处理有 `mid` 的歌曲
- 歌曲名仍使用 `title`
- 歌手名复用现有歌曲归一化逻辑
- 播放项格式为：
  - `歌名 - 歌手$qqmusic:<mid>`

如果歌手详情没有歌曲：

- 仍返回歌手详情
- `vod_play_from = QQ音乐`
- `vod_play_url = ""`

### 兼容性

当前 spider 已经存在用于歌曲名称和歌手名称格式化的辅助逻辑。歌手详情中的热门歌曲实现应复用已有歌曲播放拼接逻辑，而不是单独再实现一套字符串协议，避免榜单、搜索、歌手详情三套输出格式分叉。

### 容错

所有歌手相关请求继续走统一 JSON 请求助手。

具体要求：

- `/api/singer?page=<pg>` 请求失败时返回空列表
- `/api/singer?mid=<singer_mid>` 请求失败时返回空 `list`
- `singer_mid` 缺失的列表项直接跳过
- 非法 `singer` ID 返回空 `list`
- 热门歌曲中 `mid` 缺失的条目直接跳过

## 测试

至少新增以下测试：

- `homeContent()` 返回 `top`、`singer` 两个固定分类
- `categoryContent("singer", "1", ...)` 能映射 `data.singerlist`
- `categoryContent("singer", "2", ...)` 会继续按页码请求，而不是直接返回空
- `categoryContent("singer", ...)` 会优先把 `other_name` 映射到 `vod_remarks`，没有时回退到 `country`
- `detailContent("singer:<mid>")` 能构造歌手详情
- `detailContent("singer:<mid>")` 能输出热门歌曲播放列表
- `detailContent("singer:<mid>")` 在无歌曲时仍返回歌手详情
- 非法 `singer` ID 返回空 `list`

## 风险

- `/api/singer?page=<pg>` 目前示例返回未提供总页数或总量，因此列表页只能返回“当前页条数”，不能推导真实总量
- 歌手详情中的 `songs` 字段结构若和榜单/搜索结果不完全一致，需要在实现时做最小归一化
- `pic`、`fans` 等字段在不同部署版本中可能缺失，实现时应保持空串降级，不抛异常

实现应优先复用现有 QQ 音乐 spider 内部辅助逻辑，避免因为新增歌手能力而破坏已工作的排行榜、单曲详情和播放流程。
