# 爱奇艺蜘蛛设计

**日期：** 2026-05-06

## 目标

新增一个爱奇艺蜘蛛实现，参考用户提供的现成脚本，但收敛到当前仓库真正需要的核心能力：分类、首页推荐、筛选、详情、搜索和播放透传。实现需要保持仓库统一的蜘蛛接口，优先保证可测试性和后续维护成本，而不是机械复刻参考代码的全部细节。

## 范围

本次工作只涉及爱奇艺蜘蛛及其测试：

- 新增 [爱奇艺.py](/home/harold/workspace/tvbox-resources/py/爱奇艺.py)
- 新增 [tests/test_爱奇艺.py](/home/harold/workspace/tvbox-resources/py/tests/test_爱奇艺.py)

不做以下内容：

- 不改动其他蜘蛛
- 不引入新依赖
- 不修改公共基类
- 不在仓库内实现爱奇艺真实播放直链解析

## 设计原则

- 保留参考实现中对爱奇艺站点必要的协议约定
- 收敛状态和辅助函数数量，避免难测逻辑扩散
- 以仓库现有测试风格为准，所有网络行为都必须可 mock
- 只输出当前仓库实际消费的字段，不额外制造站点特有复杂结构

## 对外行为

### 1. 基本信息

- `getName()` 返回 `爱奇艺`
- `init()` 初始化随机设备 ID `did`
- 分类翻页使用实例级 `sid` 保存会话
- `isVideoFormat()` 返回 `True`
- `manualVideoCheck()` 返回 `False`
- `destroy()` 返回 `None`
- `localProxy()` 返回 `None`

### 2. 站点配置

实现内固定以下主机：

- 页面主站：`https://www.iqiyi.com`
- 列表与搜索接口：`https://mesh.if.iqiyi.com`
- 详情与分页接口：`https://miniapp.iqiyi.com`

公共请求头保留浏览器 UA、`Origin` 和 `Referer`，与参考实现一致，用于接口正常返回 JSON 数据。

### 3. 首页分类与筛选

`homeContent(filter)` 返回固定分类：

- 全部：`1009`
- 电影：`1`
- 剧集：`2`
- 综艺：`6`
- 动漫：`4`
- 儿童：`15`
- 微剧：`35`
- 纪录片：`3`

同时为每个分类调用标签接口并生成筛选结构。筛选值直接沿用参考实现的 Base64 包装结果，不在仓库内维护爱奇艺标签字段映射。

返回结构：

- `class`
- `filters`

### 4. 首页推荐

`homeVideoContent()` 调用推荐接口，遍历推荐模块中的视频卡片，只保留同时具备以下条件的数据：

- 可用的专辑或视频 ID
- 可用的图片
- 可用的页面 URL

输出字段：

- `vod_id`
- `vod_name`
- `vod_pic`
- `vod_year`
- `vod_remarks`

其中 `vod_id` 使用：

- `{album_or_tv_id}@{base64(page_url)}`

这个结构允许详情逻辑在专辑和单视频两条路径之间复用同一个 ID 方案。

### 5. 分类列表

`categoryContent(tid, pg, filter, extend)` 保留参考实现依赖的爱奇艺会话分页机制。

行为约定：

- 当 `pg == "1"` 时清空 `sid`
- 将 `extend` 中每个筛选值做 Base64 解码
- 解码结果按 `k=v` 形式合并为爱奇艺接口需要的 `filter` 查询串
- 请求列表接口后读取响应中的 `session` 覆盖实例 `sid`
- 仅从标准视频条目中生成列表卡片，跳过无 ID 或明显非视频卡片

列表输出字段固定为：

- `list`
- `page`
- `limit`
- `total`

`categoryContent()` 不返回 `pagecount`。

### 6. 详情页

`detailContent(ids)` 只处理 `ids[0]`。先按 `@` 拆分输入 ID，并解码其中的页面 URL。

详情逻辑分两条路径：

#### 专辑路径

优先请求专辑详情接口。如果响应中存在：

- `data.playInfo`
- `data.videoList.videos`

则构造专辑信息并生成选集列表：

- 首页视频列表直接取当前响应中的 `videoList.videos`
- 若 `totalPages > 1`，继续并发请求后续分页接口补全选集
- 每个选集输出为 `{shortTitle}${pageUrl}`

详情输出字段固定为：

- `vod_name`
- `type_name`
- `vod_year`
- `vod_remarks`
- `vod_actor`
- `vod_director`
- `vod_content`
- `vod_play_from`
- `vod_play_url`

`vod_play_from` 固定为 `爱奇艺`。

#### 单视频回退路径

若专辑结构不存在，则请求单视频详情接口，使用返回的 `playInfo` 组装单条播放信息，播放地址直接回退为输入 ID 中解码出的页面 URL。

这条路径用于电影、单片、预告或不具备专辑选集结构的内容。

### 7. 搜索

`searchContent(key, quick, pg)` 直接调用爱奇艺搜索 JSON 接口。

搜索逻辑保留参考实现的核心行为：

- 先取 `data.templates`
- 若模板中有 `intentAlbumInfos`，则将这些精确命中结果插入到遍历列表前端
- 统一从 `albumInfo` 中抽取卡片字段

输出字段：

- `vod_id`
- `vod_name`
- `vod_pic`
- `vod_year`
- `vod_remarks`

返回结构固定为：

- `list`
- `page`

### 8. 播放

`playerContent(flag, id, vipFlags)` 不做爱奇艺站内解析，直接返回解析型结果：

- `parse: 1`
- `jx: 1`
- `url: id`
- `header: ""`

这样与用户给出的参考实现保持一致，同时避免在仓库里引入额外播放器协议逻辑。

## 内部实现

### 辅助函数

实现保留少量站点专用 helper：

- `e64(text)`：Base64 编码
- `d64(text)`：Base64 解码
- `random_str(length)`：生成十六进制随机设备 ID
- `fetch_page_data(page, album_id)`：拉取详情分页中的额外选集
- `getf(body)`：拉取分类标签并转换为筛选结构

不抽象为通用基类能力，因为这些逻辑只服务爱奇艺。

### 并发策略

允许在两个点使用并发：

- `homeContent()` 中并发拉取各分类筛选
- `detailContent()` 中并发拉取后续分页选集

并发仅用于独立 JSON 请求，不跨方法共享复杂可变状态。

### 错误处理

- 主流程不做全局吞错，便于测试直接暴露解析问题
- 后续分页补全集数属于非关键路径，单页失败可跳过
- Base64 编解码失败时返回空字符串
- 搜索、列表、详情的关键路径仍按正常异常暴露，避免静默返回错误数据

## 测试设计

新增 [tests/test_爱奇艺.py](/home/harold/workspace/tvbox-resources/py/tests/test_爱奇艺.py)，全部通过 mock `fetch()` 隔离网络。

测试覆盖以下行为：

1. `getName()` 返回 `爱奇艺`
2. `e64()` 和 `d64()` 能往返处理普通页面 URL
3. `homeContent()` 返回固定分类，并把标签接口结果转换成 `filters`
4. `homeVideoContent()` 能过滤无效推荐项，并生成 `id@base64(url)` 形式的 `vod_id`
5. `categoryContent()` 能解码并合并多个筛选值，请求里包含正确的 `filter` 参数，并在翻页时更新 `sid`
6. `detailContent()` 的专辑路径能合并首页和额外分页选集
7. `detailContent()` 的单视频回退路径能生成单条播放地址
8. `searchContent()` 会把 `intentAlbumInfos` 前置，并统一解析 `albumInfo`
9. `playerContent()` 返回 `parse=1`、`jx=1` 的透传结构
10. `random_str()` 生成固定长度的十六进制字符串

## 验收标准

1. [爱奇艺.py](/home/harold/workspace/tvbox-resources/py/爱奇艺.py) 能被仓库现有加载方式直接使用
2. [tests/test_爱奇艺.py](/home/harold/workspace/tvbox-resources/py/tests/test_爱奇艺.py) 运行通过且不依赖真实网络
3. 实现结构明显收敛于当前需求，不保留参考脚本中无必要的杂项占位逻辑
4. 详情、搜索、分类三条主链路都保持和参考实现同等的外部能力
5. 该实现不修改公共基类，不影响其他蜘蛛的现有行为
