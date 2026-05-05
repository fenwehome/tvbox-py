# 爱看简化重写设计

**日期：** 2026-05-05

## 目标

将现有 [爱看.py](/home/harold/workspace/tvbox-resources/py/爱看.py) 收敛为接近参考实现的简单版本，保留仓库当前蜘蛛接口约定，去掉不必要的增强逻辑，使列表、详情、搜索和播放链路更直接、更易维护。

## 范围

本次只调整爱看蜘蛛本身及其对应测试：

- 修改 [爱看.py](/home/harold/workspace/tvbox-resources/py/爱看.py)
- 修改 [tests/test_爱看.py](/home/harold/workspace/tvbox-resources/py/tests/test_爱看.py)

不做以下内容：

- 不改其他蜘蛛
- 不引入新依赖
- 不做通用基类重构
- 不保留当前播放页二次探测的增强逻辑

## 设计原则

- 贴近用户提供的参考实现
- 优先使用页面短路径，不把内部 `vod_id` 再压缩成额外编码格式
- 解析逻辑保持单文件内聚，避免无意义抽象
- 测试聚焦对外行为，而不是历史内部实现细节

## 目标行为

### 1. 基本信息

- `host` 固定为 `https://v.ikanbot.com`
- `getName()` 返回 `Ikanbot`
- `baseHeaders()` 与 `playerHeaders()` 分离，分别用于普通页面和播放器请求

### 2. 首页与分类

- `homeContent()` 只返回固定分类：
  - 电影：`/hot/index-movie-热门.html`
  - 电视剧：`/hot/index-tv-热门.html`
- `homeVideoContent()` 抓取首页并调用列表解析器
- `categoryContent()` 支持以下分页规则：
  - 普通热榜路径：第一页原路径，第二页起替换为 `-p-{page}.html`
  - `kanlist` 和 `article` 路径：第一页 `{host}/{tag}.html`，第二页起 `{host}/{tag}-p-{page}.html`
- 分类结果保持当前仓库常见分页结构：
  - 返回 `page`
  - 返回 `pagecount`
  - 返回 `limit`
  - 返回 `total`
  - 返回 `list`

虽然仓库说明提到当前蜘蛛通常不返回 `pagecount`，但用户给出的参考实现明确包含该字段，本次按参考实现对齐。

### 3. 列表项约定

首页、分类、搜索统一输出：

- `vod_id`: `路径$$$标题$$$图片`
- `vod_name`: 标题
- `vod_pic`: 海报
- `vod_remarks`: 卡片角标或备注文本

这里保留 `title` 和 `pic` 到 `vod_id`，目的是让 `detailContent()` 在详情页字段缺失时仍能回退展示参考值。这是参考实现的核心约定，应直接保留。

### 4. 详情页

`detailContent(ids)` 输入第一项 `ids[0]`，按 `$$$` 拆分：

- 第 1 段为详情页路径
- 第 2 段为标题回退值
- 第 3 段为封面回退值

详情页行为：

- 请求详情 HTML
- 提取隐藏字段：
  - `current_id`
  - `mtype`
  - `e_token`
- 使用参考算法 `get_tks(video_id, e_token)` 生成 token
- 调用：
  - `/api/getResN?videoId={current_id}&mtype={mtype}&token={token}`
- 遍历返回的 `data.list[].resData`
- 每个 `resData` 是 JSON 数组，生成：
  - `vod_play_from`
  - `vod_play_url`

详情输出字段按参考实现保留这些重点字段：

- `vod_id`
- `vod_name`
- `vod_pic`
- `vod_year`
- `vod_area`
- `vod_actor`
- `vod_content`
- `type_name`
- `vod_remarks`
- `vod_director`
- `vod_play_from`
- `vod_play_url`

其中：

- `vod_name` 优先用 `vod_id` 内回退标题
- `vod_pic` 优先用 `vod_id` 内回退图片
- `vod_year`、`vod_area`、`vod_actor`、`vod_director` 通过页面选择器取值
- 页面缺值时返回空字符串，不做额外推断

### 5. 播放信息

`playerContent()` 不再解析播放页、不再 base64 包装播放 ID。

直接返回：

- `parse: 0`
- `playUrl: ""`
- `url: id`
- `header: playerHeaders()`

这意味着 `vod_play_url` 中写入的必须是最终线路 URL，而不是站内播放页路径。实现上应按参考实现从 `resData` 中直接提取可播放地址。

### 6. 搜索

- 搜索第一页：`/search?q={key}`
- 第二页起：`/search?q={key}&p={page}`
- 搜索结果解析器不再做当前增强版的“相关性过滤”
- 只解析页面中真实出现的结果卡片

## 解析策略

### 列表解析

列表解析器负责兼容首页、分类卡片：

- 提取 `href`
- 提取标题，优先 `img alt`，其次标题节点文本
- 提取 `img data-src` 或 `src`
- 提取 `label` 文本作为 `vod_remarks`
- 拼接 `vod_id = 路径$$$标题$$$图片`

### 搜索解析

搜索解析器负责兼容搜索结果卡片：

- 提取首个可用链接
- 提取标题
- 提取图片
- 提取备注
- 不额外做关键词筛选

### 文本与截取辅助

保留轻量辅助函数：

- `extract(text, left, right)`：简单字符串截取
- `text(html, css)`：基于现有基类 `html()` + XPath/CSS 取文本
- 允许保留一个简单的文本清洗函数，处理空白和 `\xa0`

不保留当前实现里的这些复杂逻辑：

- base64 播放 ID 编码/解码
- 站内播放页二次解析
- 搜索结果相关性判断
- 线路排序映射增强

## 错误处理

- 页面请求失败时返回空列表或空字段，不抛出异常
- `resData` 非法 JSON 时跳过该线路
- 缺少 `current_id`、`mtype`、`e_token` 时详情页返回基础信息和空播放列表

## 测试设计

测试按 TDD 重写，覆盖以下行为：

1. `getName()` 返回 `Ikanbot`
2. `get_tks()` 与参考算法一致
3. 列表解析能输出 `路径$$$标题$$$图片` 结构的 `vod_id`
4. `homeContent()` 只返回固定分类
5. `homeVideoContent()` 复用列表解析
6. `categoryContent()` 生成正确分页 URL，并返回 `pagecount`
7. `detailContent()` 能按 `vod_id` 的三段结构回退标题和图片
8. `detailContent()` 能从接口结果生成 `vod_play_from` 和 `vod_play_url`
9. `playerContent()` 直接回传线路 URL 和播放器请求头
10. `searchContent()` 构造正确搜索 URL，并按页面结果原样解析

## 实现边界

本次简化版目标不是最大化兼容所有站点变体，而是让代码结构、数据流和参考实现一致。若后续发现站点页面结构存在额外变体，再基于这版简单实现做增量修正，而不是先保留增强逻辑。
