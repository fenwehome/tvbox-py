# 酷我听书 Python 爬虫设计

## 目标

在当前 Python 仓库中新增一个符合 `base.spider.Spider` 接口的酷我听书爬虫，行为参考用户提供的 JS 版本，但交付物遵循现有仓库的单文件 Spider 结构和测试约定。

本次设计覆盖以下能力：

- 首页分类与筛选
- 首页推荐
- 分类浏览
- 搜索
- 专辑详情
- 章节播放
- VIP 章节外部解析

## 范围

本次实现包含：

- 新增独立脚本 `py/酷我听书.py`
- 新增独立测试 `py/tests/test_酷我听书.py`
- 固定站点分类、筛选项和默认排序
- 首页按四个主分类聚合推荐
- 分类接口支持子类型、权限、排序筛选
- 详情页输出专辑元数据和章节列表
- 免费章节走酷我官方播放接口
- VIP 章节保留外部解析接口支持
- 针对非标准搜索 JSON、空页翻页和付费判断补齐离线测试

本次实现不包含：

- 修改 `base/` 公共层
- 引入新的第三方依赖
- 新增缓存层、持久化状态或代理层
- 对公益解析接口做探活、限流或多地址切换
- 真实联网集成测试

## 方案选择

采用“Python 原生适配，保留核心能力”的方案，而不是直接翻译参考 JS。

原因如下：

- 当前仓库的交付物是 Python `Spider` 单文件，不是 Express 风格插件
- 仓库约定中分类和搜索结果通常返回 `page/limit/total/list`，且多数模块不返回 `pagecount`
- 参考实现中的全局状态、路由入口和长播放 URL 更适合在 Python 中收敛成内部 helper
- 参考实现的核心能力仍可完整保留：固定分类、筛选、强制翻页、详情、免费播放、VIP 解析

## 模块边界

新增模块 `py/酷我听书.py` 仅负责该站点逻辑，不修改 `base/`。

模块对外实现以下接口：

- `init`
- `getName`
- `homeContent`
- `homeVideoContent`
- `categoryContent`
- `detailContent`
- `searchContent`
- `playerContent`

模块内部使用 helper 收敛行为：

- `_api_get`
  - 访问主站 API `http://tingshu.kuwo.cn`
- `_search_get`
  - 访问搜索接口 `http://search.kuwo.cn`
- `_normalize_vod`
  - 统一列表项字段
- `_format_play_count`
  - 格式化播放量显示
- `_is_paid_track`
  - 判断章节是否为 VIP
- `_parse_search_payload`
  - 兼容搜索接口返回的非标准 JSON
- `_fetch_category_page`
  - 获取分类页原始数据
- `_force_page_fetch`
  - 处理空页补齐和本地 VIP 过滤
- `_build_filters`
  - 组装首页筛选结构
- `_build_play_id`
  - 构造短播放 ID
- `_resolve_free_play`
  - 解析免费章节直链
- `_resolve_vip_play`
  - 解析 VIP 章节外部接口

## 站点配置

固定配置来源于参考实现，直接内置在模块常量中：

- 站点名：`酷我听书`
- 主站：`http://tingshu.kuwo.cn`
- 搜索站：`http://search.kuwo.cn`
- 播放站：`http://mobi.kuwo.cn`
- VIP 解析接口：`https://music-api.gdstudio.xyz/api.php`
- 默认请求头：
  - `User-Agent: kwplayer_ar_9.1.8.1_tvivo.apk`

固定分类如下：

- `2 -> 有声小说`
- `37 -> 音乐金曲`
- `5 -> 相声评书`
- `62 -> 影视原声`

固定筛选项沿用参考实现：

- 每个主分类带一个 `class` 子类型筛选
- 所有分类追加统一的 `vip` 权限筛选
- 所有分类追加统一的 `sort` 排序筛选

其中：

- `vip`
  - `全部权限`
  - `免费权限`
  - `会员权限`
- `sort`
  - `综合排序`
  - `最新上架`
  - `按总播放`

## 首页设计

`homeContent` 只返回静态分类和筛选定义，并附带首页推荐列表。

返回结构包含：

- `class`
- `filters`
- `list`

`homeVideoContent` 会按四个主分类分别请求默认子分类第一页，每类提取列表后聚合返回。默认子分类取该分类第一个筛选项的 `init` 值。

列表项统一映射为：

- `vod_id`
  - `albumId`
- `vod_name`
  - `albumName`
- `vod_pic`
  - `coverImg`
- `vod_remarks`
  - `会员|免费 + 播放量 + 分类名或作者`

播放量格式化规则：

- `>= 1e8` 显示为 `x.x亿`
- `>= 1e4` 显示为 `x.x万`
- 其他按整数原样显示

## 分类与分页设计

`categoryContent` 支持主分类、页码和扩展筛选参数。

筛选参数映射如下：

- `class`
  - 子类型 ID，默认取当前分类的 `init`
- `vip`
  - `""`、`0`、`1`
- `sort`
  - `tsScore`、`pubDate`、`playCnt`

返回遵循仓库现有习惯：

- `page`
- `limit`
- `total`
- `list`

默认不返回 `pagecount`。

上游分类接口可能出现中间页为空的情况，因此保留参考实现中的“强制翻页补齐”策略：

- 用户请求第 `pg` 页时，从该页开始请求
- 若当前页无数据，则继续尝试后续页
- 最多尝试 `maxPage=10` 次
- 一旦拿到有效数据，则将该页作为当前返回数据源

VIP 权限筛选在本地二次处理：

- `vip=""`
  - 不过滤
- `vip="0"`
  - 仅保留免费专辑
- `vip="1"`
  - 仅保留会员专辑

`total` 和 `limit` 处理原则：

- `limit` 固定返回 `21`
- 若还有后续可翻页空间，`total` 返回一个足够大的估算值，以维持翻页体验
- 若已无后续数据，则 `total` 退化为当前页结果长度

## 搜索设计

`searchContent` 访问 `search.kuwo.cn` 的专辑搜索接口，关键词参数对应参考实现的 `all`。

搜索接口的响应可能是单引号 JSON 或普通 JSON 字符串，因此需要容错解析：

- 优先按字符串读取
- 若存在单引号包裹的对象结构，先做最小修正再解析
- 解析失败则返回空结果

搜索结果映射字段：

- `vod_id`
  - `DC_TARGETID`
- `vod_name`
  - `name`
- `vod_pic`
  - `img`
- `vod_remarks`
  - `会员|免费 + artist`

搜索返回结构：

- `page`
- `limit`
  - 固定 `21`
- `total`
- `list`

搜索空关键词时直接返回空结果：

- `{"page": 1, "limit": 0, "total": 0, "list": []}`

## 详情设计

`detailContent` 根据专辑 ID 请求专辑详情接口，返回单个专辑对象。

详情字段映射：

- `vod_id`
  - 专辑 ID
- `vod_name`
  - 根级 `name`
- `vod_pic`
  - 根级 `img`，若为相对路径则补全为完整封面地址
- `vod_remarks`
  - `会员|免费 + 完结状态 + 集数 + 总播放量`
- `vod_content`
  - `info`，回退 `title`
- `vod_actor`
  - `artist`
- `vod_director`
  - `company`
- `vod_year`
  - 从 `pub` 提取年份，格式为 `2026年`
- `vod_area`
  - `lang`
- `vod_lang`
  - `lang`
- `vod_time`
  - `pub`
- `vod_tag`
  - `完结` 或 `连载`

章节列表使用单线路输出：

- `vod_play_from = "酷我听书"`
- `vod_play_url = 章节1$播放ID#章节2$播放ID...`

章节名称规则：

- 使用章节名 `track.name`
- 缺失时回退为 `第N集`
- VIP 章节前面加 `💎`

### 播放 ID 设计

不直接把长播放 URL 写进详情，而是构造成短载荷：

- 免费章节：`free|<musicrid>`
- VIP 章节：`vip|<musicrid>`

这样可以把真实播放解析逻辑集中在 `playerContent`，降低 `vod_play_url` 的耦合度，也方便单测断言。

## 播放设计

`playerContent` 根据播放 ID 类型分两条链路处理。

### 免费章节

当播放 ID 形如 `free|musicrid` 时：

- 请求 `http://mobi.kuwo.cn/mobi.s`
- 参数：
  - `f=web`
  - `type=convert_url_with_sign`
  - `rid=<musicrid>`
  - `br=320kmp3`
- 若接口返回 JSON 中存在最终音频 URL，则返回直链播放

输出结构：

- `parse: 0`
- `url: <final url>`
- `header`
  - `User-Agent`
  - `Referer`

### VIP 章节

当播放 ID 形如 `vip|musicrid` 时：

- 请求外部解析接口 `https://music-api.gdstudio.xyz/api.php`
- 保留参考实现中的固定查询参数
- 若返回 `url` 字段，则作为最终音频地址

输出结构：

- `parse: 0`
- `url: <final url>`
- `header`
  - `User-Agent: LX-Music-Mobile`
  - `Referer: https://music-api.gdstudio.xyz`

### 回退策略

若播放解析失败：

- 免费章节返回一个基于 `musicrid` 拼装的官方播放请求地址作为兜底 `url`
- VIP 章节返回外部解析接口请求地址作为兜底 `url`
- 不抛出未处理异常

## 错误处理

整体遵循当前仓库的“失败返回空结果或兜底结果”策略。

- 首页、分类、搜索接口失败
  - 返回空列表结果
- 详情接口失败或章节为空
  - 返回 `{"list": []}`
- 搜索 JSON 解析失败
  - 返回空结果，不中断流程
- 播放解析失败
  - 返回兜底 `url`，保持 `playerContent` 可消费

所有网络请求都通过 `self.fetch` 实现，便于在单测中统一 mock。

## 测试设计

测试采用 `unittest + SourceFileLoader + unittest.mock`，全部离线执行，不依赖真实网络。

覆盖范围：

- `homeContent`
  - 固定分类、筛选结构、`vip/sort` 追加逻辑
- `homeVideoContent`
  - 四类首页推荐聚合、分类名写入 `vod_remarks`
- `categoryContent`
  - 分类参数映射、空页后移、VIP 本地过滤、不返回 `pagecount`
- `searchContent`
  - 非标准 JSON 解析、字段映射、空关键词返回空结果
- `detailContent`
  - 专辑元数据映射、封面补全、章节名和播放 ID 构造
- `playerContent`
  - 免费章节直链解析
  - VIP 章节外部解析
  - 失败回退路径
- helper
  - 播放量格式化
  - VIP 判断
  - 播放 ID 编解码

## 风险与约束

- 搜索接口返回结构不是严格标准 JSON，解析策略需要尽量保守，避免误替换内容
- 公益解析接口是外部依赖，稳定性不可控，因此必须保留失败回退
- 详情章节数可能很大，播放列表生成应保持简单，不在本次实现中引入额外排序和缓存
- 站点是音频内容，不涉及仓库里常见的视频网盘线路，因此 `playerContent` 返回头信息时应按音频接口的需求最小化设置

## 交付物

- `py/酷我听书.py`
- `py/tests/test_酷我听书.py`

本次设计已经明确：

- 站点模块名使用 `酷我听书`
- VIP 外部解析接口默认保留并启用
- 结果结构遵循当前 Python 仓库习惯，而不是直接复刻 JS 插件路由层行为
