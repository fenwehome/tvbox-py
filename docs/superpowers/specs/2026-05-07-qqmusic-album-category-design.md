# QQ音乐专辑分类设计

## 目标

在现有 QQ 音乐 spider 基础上，新增专辑分类列表能力，支持按地区分页浏览专辑，并复用已存在的 `album:*` 详情能力进入专辑详情页。

## 范围

- 修改 `py/QQ音乐.py`
- 修改 `py/tests/test_QQ音乐.py`
- `homeContent()` 从 `排行榜`、`歌手`、`歌单` 扩展为 `排行榜`、`歌手`、`专辑`、`歌单`
- 支持 `GET /api/album?area=<area>&page=<pg>` 专辑分页列表
- 支持通过 `extend["area"]` 传递地区筛选参数

## 非目标

- 不新增专辑播放协议
- 不修改现有 `detailContent("album:*")` 的详情协议
- 不修改现有 `searchContent()` 的歌曲、歌手、专辑、歌单搜索逻辑
- 不在 `homeContent()` 中暴露筛选定义结构
- 不接入除 `area` 以外的其他专辑筛选参数

## 方案

### 分类

`homeContent(False)` 返回四个固定分类，顺序固定为：

- `top`: 排行榜
- `singer`: 歌手
- `album`: 专辑
- `playlist`: 歌单

`homeVideoContent()` 保持返回空列表。

### 数据来源

专辑分类浏览仅使用以下接口：

- `/api/album?area=<area>&page=<pg>`

不新增其他列表接口，也不改动已存在的 `/api/album?mid=<mid>` 详情能力。

### ID 约定

沿用现有 ID 规则：

- 榜单：`top:<id>`
- 单曲：`song:<mid>`
- 歌手：`singer:<singer_mid>`
- 专辑：`album:<album_mid>`
- 歌单：`playlist:<tid>`
- 播放：`qqmusic:<mid>`

专辑分类列表中的卡片点击后直接进入现有 `album:*` 详情分支，不新增中间协议。

### 专辑列表

`categoryContent("album", pg, filter, extend)` 逻辑：

- `pg` 为空时按 `1` 处理
- `extend` 非字典时按空字典处理
- 地区参数取 `extend["area"]`
- `area` 缺失、空值、非法值时回退到 `1`
- 仅接受 `1-5` 五个地区值
- 请求 `/api/album?area=<area>&page=<pg>`
- 校验返回 `code == 0`
- 遍历 `data.albums`

地区值固定映射为：

- `1`: 内地
- `2`: 港台
- `3`: 欧美
- `4`: 韩国
- `5`: 日本

每个专辑卡片至少提取：

- `mid`
- `name`
- `singers`
- `release_time`
- `photo.pic_mid`
- 兼容直出的 `pic` 或 `cover`

映射为：

- `vod_id = album:<mid>`
- `vod_name = name`
- `vod_pic`
  - 优先使用接口直接给出的 `pic`
  - 其次使用接口直接给出的 `cover`
  - 否则根据 `photo.pic_mid` 组装 QQ 音乐专辑封面 URL
  - 如果都缺失则为空串
- `vod_remarks`
  - 优先格式：`歌手名  发行日期`
  - 如果只有歌手名则只显示歌手名
  - 如果只有发行日期则只显示发行日期
  - 两者都没有则为空串

歌手名生成规则：

- 遍历 `singers`
- 使用 `name` 字段
- 多个歌手以 `/` 拼接

分页返回：

- `page = 当前页`
- `limit = 当前页条数`
- `total = 当前页条数`
- `list = 当前页专辑卡片`

不返回 `pagecount`。

### 兼容性

当前 spider 已经存在：

- `album:*` 搜索结果映射
- `detailContent("album:*")` 专辑详情
- 歌曲播放串拼接逻辑

专辑分类实现应只负责列表入口和列表字段归一化，不重新实现专辑详情或播放逻辑。分类列表返回的 `vod_id` 必须与现有 `album:*` 详情分支保持一致，避免出现“搜索可以进详情、分类不能进详情”的分叉行为。

### 容错

所有专辑分类请求继续走统一 JSON 请求助手。

具体要求：

- `/api/album?area=<area>&page=<pg>` 请求失败时返回空列表
- `mid` 缺失的列表项直接跳过
- `name` 缺失的列表项直接跳过
- `singers` 缺失、为空或单项字段缺失时按空歌手名处理，不抛异常
- `release_time` 缺失时允许只显示歌手名
- `pic`、`cover`、`photo.pic_mid` 都缺失时 `vod_pic = ""`
- 非法 `area` 值统一回退到 `1`

## 测试

至少新增以下测试：

- `homeContent()` 返回 `top`、`singer`、`album`、`playlist` 四个固定分类，且顺序正确
- `categoryContent("album", "1", ..., {})` 默认请求 `area=1&page=1`
- `categoryContent("album", "2", ..., {"area": "3"})` 请求 `area=3&page=2`
- `categoryContent("album", ...)` 能映射 `album:<mid>`
- `categoryContent("album", ...)` 能正确拼接 `singers[].name`
- `categoryContent("album", ...)` 能正确生成 `歌手名  发行日期` 备注
- `categoryContent("album", ...)` 能在 `pic` 缺失时回退到 `photo.pic_mid` 封面 URL
- `categoryContent("album", ...)` 在非法 `area` 时回退到 `1`
- `categoryContent("album", ...)` 在 `mid` 或 `name` 缺失时跳过坏数据
- `/api/album` 请求失败时返回空列表

## 风险

- 专辑列表接口示例未明确总量字段，实现时只能继续沿用“当前页条数”作为 `total`
- `photo.pic_mid` 的封面 URL 规则若后端后续变更，需要调整归一化逻辑
- 不同部署版本的专辑列表字段可能在 `pic`、`cover`、`photo.pic_mid` 之间切换，实现时必须按优先级兼容

实现应优先保持新增专辑分类能力与现有 QQ 音乐 spider 的搜索、详情和播放器协议一致，不为了展示更多专辑字段而扩大改动范围。
