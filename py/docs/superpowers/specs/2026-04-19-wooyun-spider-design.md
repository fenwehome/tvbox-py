# 乌云影视 Python 爬虫设计

## 目标

在当前 Python 仓库中新增一个符合 `base.spider.Spider` 接口的乌云影视站点爬虫，覆盖以下能力：

- 首页分类与筛选
- 首页推荐视频
- 分类列表
- 搜索
- 详情解析
- 播放解析

实现基于站点现有 JSON API，不依赖浏览器自动化，不修改 `base/` 公共层。

## 范围

本次实现包含：

- 新增独立脚本，文件名为 `乌云影视.py`
- 使用单一站点主域：`https://wooyun.tv`
- 支持 `home/homeVideo/category/detail/search/player` 全链路
- 支持年份、地区、类型、语言、排序筛选
- 支持多季播放列表
- 支持播放接口直链优先与播放回退

本次实现不包含：

- 多域名自动回退
- 登录态或会员内容适配
- 站点反爬绕过
- 通用 JSON 影视站抽象层
- 参考 JS 的 Fastify 路由封装

## 方案选择

采用仓库现有的“单站点单文件 + 单测”方案：

- 对外保持 `Spider` 接口兼容
- 对内拆分为请求封装、分类过滤构造、列表映射、详情解析、播放载荷编码几个 helper
- 保留参考实现的核心行为，但去掉服务端路由与日志包装层

不直接照搬参考 JS 包装层的原因是：

- 当前仓库只需要站点 Spider，不需要 HTTP 路由注册
- Python 版单文件 Spider 更符合现有项目结构
- 测试重点应放在参数构造和解析结果，而不是中间层框架逻辑

## 模块边界

新增脚本只在站点文件内部维护逻辑，不修改 `base/`。

脚本内部职责拆分如下：

- `init`
  - 初始化主域、请求头、默认分类、默认分页参数
- `homeContent`
  - 拉取菜单接口，构造 `class` 与 `filters`
- `homeVideoContent`
  - 拉取首页推荐接口，返回首页卡片列表
- `categoryContent`
  - 组装搜索接口请求体，返回分页列表
- `detailContent`
  - 组合基础详情、扩展详情和剧集列表，整理成 TVBox 详情结构
- `searchContent`
  - 复用搜索接口执行关键字查询
- `playerContent`
  - 解析编码后的播放载荷，优先返回直链，必要时回查剧集接口
- 私有辅助函数
  - 安全文本转换
  - 相对地址补全
  - 筛选数据归一化
  - 分类与筛选构造
  - 卡片映射
  - 播放载荷编码与解码
  - 兜底剧集地址查找

## Host 与请求策略

本次只实现单域：

- `https://wooyun.tv`

请求统一走站点 JSON API，固定请求头至少包含：

- `Accept`
- `Origin`
- `Referer`
- `User-Agent`

其中：

- GET/POST 都走 `self.fetch` / `self.post`
- 默认超时使用站点级固定值，优先取 10 秒到 15 秒
- 非 2xx 响应视为失败并回退为空结果或播放解析

不做：

- 自动重试
- 动态 host 探活
- 本地缓存持久化

## 分类与筛选设计

菜单接口：

- `/movie/category/menu`

分类优先保留以下根分类：

- `movie -> 电影`
- `tv_series -> 电视剧`
- `animation -> 动画`
- `variety -> 综艺`
- `short_drama -> 短剧`

同时补充特殊年份分类：

- `THIS_YEAR -> 今年`
- `LAST_YEAR -> 去年`

筛选定义从菜单接口动态生成，按站点字段映射为：

- `year -> 年份`
- `region -> 地区`
- `genre -> 类型`
- `lang -> 语言`
- `sort -> 排序`

排序候选固定为：

- `default`
- `latest`
- `hot`
- `score`

`homeContent` 返回：

- `class`
- `filters`

分类接口请求体使用：

- `menuCodeList`
- `pageIndex`
- `pageSize`
- `searchKey`
- `sortCode`
- `topCode`

其中 `THIS_YEAR` 和 `LAST_YEAR` 不作为 `topCode`，只作为 `menuCodeList` 过滤项，`topCode` 仍回落到 `movie`。

## 首页与列表设计

首页推荐接口：

- `/movie/media/home/custom/classify/1/3?limit=<n>`

推荐列表从区块数据中提取 `mediaResources`，按 `id` 去重后映射为统一卡片结构：

- `vod_id`
- `vod_name`
- `vod_pic`
- `type_id`
- `type_name`
- `vod_remarks`
- `vod_year`
- `vod_douban_score`
- `vod_actor`
- `vod_director`

列表与搜索都复用相同映射逻辑，封面优先级为：

- `posterUrlS3`
- `posterUrl`
- `thumbUrlS3`
- `thumbUrl`

分类接口：

- `POST /movie/media/search`

分页字段返回：

- `page`
- `pagecount`
- `limit`
- `total`
- `list`

其中 `limit` 固定为 24，与参考实现保持一致。

## 详情页设计

详情阶段使用三个接口并行组合：

- `/movie/media/base/detail?mediaId=<id>`
- `/movie/media/detail?mediaId=<id>`
- `/movie/media/video/list?mediaId=<id>&lineName=&resolutionCode=`

详情合并规则：

- 优先使用扩展详情接口字段
- 基础详情作为兜底
- 剧集列表单独解析播放源

输出字段至少包含：

- `vod_id`
- `vod_name`
- `vod_pic`
- `type_id`
- `type_name`
- `vod_remarks`
- `vod_year`
- `vod_area`
- `vod_actor`
- `vod_director`
- `vod_content`
- `vod_douban_score`
- `vod_play_from`
- `vod_play_url`

多季播放列表按季拆分：

- 多季时 `vod_play_from` 为 `第1季$$$第2季...`
- 单季时 `vod_play_from` 使用线路名或站点名兜底

每个剧集条目名称优先按 `第N集` 生成，存在备注时拼接为 `第N集 <remark>`，无法取到集数时回退 `正片`。

## 播放设计

播放列表中的每一集不直接暴露站点原始对象，而是把最小必要字段编码为可逆载荷：

- `mediaId`
- `seasonNo`
- `epNo`
- `videoId`
- `playUrl`
- `name`

编码格式为 base64url JSON 字符串。

`playerContent` 处理流程：

1. 解码播放载荷
2. 若载荷内已有 `playUrl`，直接返回补全后的绝对地址
3. 若没有 `playUrl` 但有 `mediaId`，回查剧集接口并按 `seasonNo/videoId/epNo` 找到目标地址
4. 若仍拿不到地址，回退为 `parse=1` 并把原始 `id` 交给外层解析

直链返回头只保留播放必要字段：

- `Referer`
- `Origin`
- `User-Agent`

## 搜索设计

搜索复用：

- `POST /movie/media/search`

请求体固定：

- `menuCodeList = []`
- `pageIndex = pg`
- `pageSize = 24`
- `searchKey = keyword`
- `sortCode = ""`
- `topCode = ""`

空关键字直接返回空列表，不发请求。

## 错误处理

核心策略保持简单明确：

- HTTP 非 2xx 直接抛错
- JSON 结构中若存在站点失败标记，也抛错
- `home/homeVideo/category/search/detail` 失败时返回空结构或上层调用感知异常
- `playerContent` 失败时优先回退到 `parse=1`

不增加复杂的错误码映射，只保留对调用方有意义的最小错误信息。

## 测试设计

测试文件：

- `tests/test_乌云影视.py`

单测覆盖以下边界：

- 菜单数据能够构造固定分类与动态筛选
- 首页推荐区块能去重并映射统一卡片结构
- 分类请求体能正确处理根分类与年份特殊分类
- 分类结果能返回正确分页字段
- 详情页能合并详情字段并生成多季播放列表
- 播放载荷编码解码可逆
- 播放回查逻辑能按 `videoId` 或 `epNo` 命中剧集地址
- 搜索空关键字直接返回空结构
- 播放在没有直链时回退 `parse=1`

测试以 mock HTTP 返回和纯函数解析为主，不依赖真实网络。

## 实现约束

- 不修改 `base/spider.py`
- 不引入新第三方依赖
- 维持仓库现有返回结构命名
- 代码以 ASCII 为主，中文仅用于站点名和用户可见字段
- 与现有站点脚本风格保持一致，优先单文件内聚实现
