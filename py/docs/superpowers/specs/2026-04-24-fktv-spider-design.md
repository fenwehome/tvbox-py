# FKTV Python 爬虫设计

## 目标

在当前 Python 仓库中新增一个符合 `base.spider.Spider` 接口的凡客TV爬虫，行为参考用户提供的 FKTV JS 版本，但实现形式遵循仓库现有的单文件 Spider 约定。

本次实现范围：

- 首页分类
- 分类浏览
- 搜索
- 详情解析
- 多线路剧集组装
- 播放接口直链优先
- 接口失败时回退详情页

本次不实现：

- 弹幕
- 页面嗅探
- 本机 `curl` 回退
- 验证码绕过

## 方案选择

采用“详情页解析状态，播放时调用官方切换接口”的方案，而不是只依赖详情页内嵌 `play_links`。

原因如下：

- FKTV 的剧集和线路是两套独立状态，详情页内嵌 `play_links` 可能只对应当前默认剧集
- 如果只复用默认 `play_links`，用户切换到别的剧集时容易串集
- 参考实现的核心可靠性来自 `link_id + line_id` 组合后再请求官方播放接口
- 在当前 Python 仓库里保留接口直链优先、失败回退页面，已经覆盖核心需求，不必移植 OmniBox 专属能力

## 模块边界

新增 `py/凡客TV.py`，不修改 `py/base/`。

模块对外实现：

- `init`
- `getName`
- `homeContent`
- `homeVideoContent`
- `categoryContent`
- `searchContent`
- `detailContent`
- `playerContent`

模块内部 helper 负责：

- 请求头与 cookie 管理
- HTML / JSON 请求
- 列表卡片解析
- 详情页状态脚本解析
- 线路 tab 提取
- `play_id` 编解码
- 播放接口请求与结果归一化
- 直链与回退结果构造

## 站点策略

固定站点参数：

- host：`https://fktv.me`
- 固定桌面端 `User-Agent`
- 固定 cookie：`_did=57nTmEknMZ146xw4KXGHDCHk1MjshRyY`

请求策略：

- 列表、搜索、详情页使用普通 GET
- 播放切换接口使用 POST
- 播放接口请求头必须包含：
  - `User-Agent`
  - `Referer`
  - `Origin`
  - `X-Requested-With`
  - `Content-Type: application/x-www-form-urlencoded; charset=UTF-8`
  - 固定 cookie

## 分类与首页

`homeContent` 返回固定分类：

- `1` 电影
- `2` 剧集
- `4` 动漫
- `3` 综艺
- `8` 短剧
- `6` 纪录片
- `7` 解说
- `5` 音乐

`homeVideoContent` 不单独抓推荐，返回空列表，和仓库中多个站点保持一致。

分类 URL 固定为：

- `/channel?page={page}&cat_id={type_id}&page_size=32&order=new`

分类页解析规则：

- 优先从 `.meta-wrap` 所在卡片提取数据
- 兜底解析 `.hover-wrap`
- 提取详情链接中的 `/movie/detail/{id}`
- 提取标题、封面、标签和备注
- `vod_id` 保留短 ID，不返回完整 URL

返回结构遵循仓库当前约定：

- `page`
- `limit`
- `total`
- `list`

不返回 `pagecount`。

## 搜索

搜索 URL 固定为：

- `/search?keyword=<urlencoded keyword>`

搜索页解析复用分类卡片逻辑：

- 提取详情短 ID、标题、封面、标签
- 去重后返回
- 关键字为空时直接返回空列表

搜索返回：

- `page`
- `limit`
- `total`
- `list`

不返回 `pagecount`。

## 详情解析

详情页 URL 固定为：

- `/movie/detail/{vod_id}`

详情页需要同时解析 HTML 可见信息和页面脚本状态。

基础元信息：

- `vod_id`
- `vod_name`
- `vod_pic`
- `vod_content`
- `vod_remarks`

页面脚本状态：

- `movieId`
- `linkId`
- `links`
- `play_links`
- `play_error_type`

其中：

- `links` 代表剧集列表，是详情页组装剧集的主数据源
- `play_links` 仅用于诊断和线路兜底，不作为目标剧集的真值来源

线路提取规则：

- 优先从带 `data-line` 的线路 tab 提取线路 ID 和线路名
- 如果页面没有线路 tab，则退化使用 `play_links` 中的线路 ID 和名称
- 如果两者都没有，则详情页返回空播放字段

剧集提取规则：

- 逐个读取 `links` 中的剧集项
- 每个剧集至少提取 `id` 和展示名
- 如果没有名称，则按 `name`、`title`、`id` 顺序兜底

详情页播放字段组装规则：

- `vod_play_from` 为线路名称列表，使用 `$$$` 拼接
- `vod_play_url` 为每条线路下的剧集列表，使用 `#` 拼接单集、`$$$` 拼接线路
- 每个单集条目格式为 `剧集名$play_id`

这里会为每条线路复用同一批剧集。原因是 FKTV 的线路和剧集是分离状态：

- 剧集由 `links` 定义
- 线路由线路 tab 或 `play_links` 定义
- 真正播放地址必须在 `playerContent` 中通过 `link_id + line_id` 实时换取

`vod_remarks` 只保留少量站点状态提示：

- `play_error_type == captcha` 时提示站点需要验证码
- `play_error_type == need_vip` 时提示站点存在 VIP 限制

## Play ID 设计

`play_id` 不直接保存页面 URL，而是编码为一个紧凑 JSON 字符串，至少包含：

- `movie_id`
- `link_id`
- `line_id`
- `line_name`
- `episode_name`
- `type`
- `page`

设计目标：

- 播放时能准确定位目标剧集和目标线路
- 即使详情阶段只拿到短 ID，也能回退到详情页
- 在测试里可以稳定断言 `play_id` 的结构和往返解码行为

## 播放解析

`playerContent` 分三层处理。

第一层，直接透传：

- 如果传入就是 `.m3u8`、`.mp4`、`.flv` 等明显媒体直链，直接返回 `parse=0`

第二层，播放接口直链优先：

- 解码 `play_id`
- 回读详情页，重新获取当前 `movieId`、默认 `linkId` 和页面状态
- 使用 `play_id` 中的 `link_id` 作为目标剧集，缺失时回退页面默认 `linkId`
- POST `https://fktv.me/movie/detail/{movie_id}`
- 表单固定为 `link_id={link_id}&is_switch=1`
- 从响应 JSON 的 `data.play_links` 中提取各线路直链
- 如果指定了 `line_id`，则只返回对应线路
- 如果没有指定 `line_id`，则返回该剧集下接口给出的全部线路

第三层，失败回退：

- 接口没有可播地址
- 接口返回 `need_vip`
- `play_id` 非法但还能推导出详情页
- 详情页能打开但无法换取直链

这些场景统一返回 `parse=1`，回退到详情页地址。

## 播放结果规范

直链结果：

- `parse=0`
- `playUrl=""`
- `url` 为首个可播地址
- `header` 至少包含：
  - `User-Agent`
  - `Referer`
  - `Origin`

当接口返回多线路时：

- 额外返回 `urls`
- 每项格式为 `{"name": "<线路名>", "url": "<直链>"}`

回退结果：

- `parse=1`
- `playUrl=""`
- `url` 为详情页地址
- `header` 带页面请求所需的 `User-Agent` 和 `Referer`

不实现页面嗅探，不返回 OmniBox 风格的额外字段。

## 测试策略

新增 `py/tests/test_凡客TV.py`，全部使用离线 HTML / JSON fixture 和 mock，不做真实联网。

重点覆盖：

- `homeContent` 返回固定分类
- `categoryContent` 正确构造 `/channel` URL 并解析卡片
- `searchContent` 正确构造 `/search` URL，空关键字直接返回空列表
- 详情页状态解析：`movieId`、`linkId`、`links`、`play_links`、`play_error_type`
- 线路 tab 提取和剧集名称兜底
- `detailContent` 组装 `vod_play_from` / `vod_play_url`
- `play_id` 编解码往返一致
- `playerContent` 对直链直接返回
- `playerContent` 请求官方切换接口并按 `line_id` 过滤
- `playerContent` 在线路未指定时返回全部接口线路
- `playerContent` 在 `need_vip`、空结果、非法标识等场景下回退详情页

## 风险与边界

- FKTV 详情页里的脚本状态依赖站点当前模板，本次只兼容参考结构
- 固定 cookie 未来可能失效，失效后播放接口可能退化为页面回退
- 如果站点把线路 tab 或脚本变量名称整体改版，详情组装和播放接口都需要同步调整
- 不实现验证码处理，遇到 `captcha` 只给出提示并回退页面
- 不做 `curl` 回退和页面嗅探，意味着接口彻底失效时只能降级到页面解析
