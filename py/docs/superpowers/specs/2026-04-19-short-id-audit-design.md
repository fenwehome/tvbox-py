# Spider 短路径 ID 审计与修正规范

## 目标

对当前 Python 仓库内已有 Spider 做一轮 `vod_id` 与播放 id 的规范审计，修正仍然暴露完整 URL 的实现，统一满足以下规则：

- `vod_id` 使用站内短路径 id
- 播放列表中的剧集 id 使用站内短路径 id
- `detailContent` 与 `playerContent` 在内部把短路径还原为完整请求地址
- 对外返回数据不暴露完整 URL

本次工作是规范性修正，不新增站点功能，不调整已有解析能力范围。

## 范围

本次审计对象包括当前仓库内的这些 Spider：

- `libvio.py`
- `低端影视.py`
- `滴答影视.py`
- `剧迷.py`
- `橘子TV.py`
- `youknow.py`
- `乌云影视.py`
- `剧圈圈.py`

本次实现包含：

- 审计上述 Spider 的 `vod_id` 与播放 id 返回形式
- 只修改实际违规的 Spider
- 为每个被修改的 Spider 补充或更新测试

本次实现不包含：

- 改动本就已符合规范的 Spider
- 统一不同站点的 id 格式
- 修改站点已有的播放解析策略
- 修改与 id 压缩无关的列表、详情、搜索、播放逻辑

## 核心规则

### 规则 1：按各站原始路径压缩

用户要求“按各站原始路径压缩”，因此不采用统一的跨站格式，例如不强制所有站都用 `vod/<id>`。

每个站点应保留自身 URL 路径语义，例如：

- `/detail/123.html` 压缩为 `detail/123`
- `/vod/123.html` 压缩为 `vod/123`
- `/play/100-1-1.html` 压缩为 `play/100-1-1`
- `/movie/demo/` 压缩为 `movie/demo`
- `/d/456/` 压缩为 `d/456`

允许保留当前 Spider 已稳定使用的非 URL 型短 id，例如：

- 纯数字 id
- 站点 API 原生 `vodId`
- 已有可逆紧凑 payload

前提是这些值本身不暴露完整 URL。

### 规则 2：详情 id 可逆

`vod_id` 必须是 Spider 内部可逆的：

- 列表/搜索返回短 id
- `detailContent` 内部负责把短 id 还原成完整详情请求地址

### 规则 3：播放 id 可逆

详情播放列表中的每个剧集项也必须是 Spider 内部可逆的：

- 详情返回短路径或紧凑播放 id
- `playerContent` 内部负责把 id 还原成完整播放请求地址或播放参数

### 规则 4：对外不返回完整 URL

以下位置禁止返回完整站内详情/播放 URL：

- 列表页结果中的 `vod_id`
- 搜索结果中的 `vod_id`
- 详情结果中 `vod_play_url` 里的剧集 id

例外：

- 外站直链媒体地址
- 网盘分享地址
- 本就不是站内详情/播放页的第三方链接

## 审计策略

采用“全量审计，按需修复”的方式。

### 第一步：识别是否违规

重点检查：

- 列表和搜索是否直接把完整详情 URL 赋值给 `vod_id`
- 详情页播放列表是否直接把完整播放 URL 塞进 `vod_play_url`
- `detailContent` 是否把传入值直接当 URL 请求
- `playerContent` 是否把传入值直接当完整播放页 URL 使用

若 Spider 已满足以下任一条件，则视为合规：

- 使用站点内部短路径字符串
- 使用纯数字或 API 原生主键
- 使用当前 Spider 已有可逆紧凑 payload

### 第二步：最小修复

对违规 Spider 只做以下最小改动：

- 添加 `encode/decode` helper，或复用现有 helper
- 将列表/搜索返回的完整 URL 改为短路径
- 将详情播放项中的完整播放 URL 改为短路径
- 在 `detailContent/playerContent` 中添加还原逻辑

不做额外重构，不调整字段命名，不重写不相关逻辑。

## 当前预期违规对象

基于当前代码初步审计，明确违规的对象至少包括：

- `低端影视.py`
- `滴答影视.py`

这两个 Spider 当前存在以下问题：

- 列表/搜索直接返回完整详情 URL 作为 `vod_id`
- `detailContent` 直接把传入的 `vod_id` 当完整 URL 请求

对于其他 Spider：

- `libvio.py`、`剧迷.py`、`youknow.py`、`橘子TV.py`、`乌云影视.py`、`剧圈圈.py`
  当前实现看起来已经使用可逆短 id 或站点主键
  本次只做确认，不做无意义修改

## 测试策略

每个被修改的 Spider 至少补以下回归测试：

- 列表页返回短路径 `vod_id`
- 搜索页返回短路径 `vod_id`（若该 Spider 支持搜索）
- `detailContent` 接受短路径 id 并正确还原详情 URL
- 详情播放列表返回短路径或紧凑播放 id
- `playerContent` 接受短路径或紧凑播放 id 并正确还原播放请求地址

测试全部使用 mock HTML / JSON，不依赖外网。

## 验收标准

- 审计范围内 Spider 不再对外暴露完整站内详情/播放 URL
- 仅对实际违规 Spider 做代码修改
- 每个被修正的 Spider 都有对应测试覆盖
- 现有已合规 Spider 不发生接口格式回退
