# 不太灵 Python 爬虫设计

## 目标

在当前 Python 仓库中新增一个符合 `base.spider.Spider` 接口的不太灵站点爬虫，直接对接 `https://web5.mukaku.com/prod/api/v1/`，覆盖以下能力：

- 首页分类
- 首页推荐
- 分类列表
- 搜索
- 详情解析
- 网盘分享链接透传播放

实现以用户提供的 JS 版本为行为参考，但最终产物遵循当前仓库的单文件 Spider 约定，不引入 JS 端的网盘驱动依赖。

## 范围

本次实现包含：

- 新增独立脚本，文件名为 `不太灵.py`
- 使用单一 API 根地址 `https://web5.mukaku.com/prod/api/v1/`
- 支持 `home/category/detail/search/player` 主链路
- 首页返回固定五个分类
- 电影和电视剧支持 API 筛选参数映射
- 详情页提取影片元数据和网盘分享资源
- 网盘资源按分享链接独立成线路
- `playerContent` 对分享链接做原样透传
- 为新增行为补齐 `unittest`

本次实现不包含：

- 参考 JS 中的磁力画质线路输出
- 网盘驱动匹配、`getVod` 预解析或 `play` 二次解析
- 提取码自动补链
- 浏览器执行、反爬绕过或多域名探活
- 修改 `base/` 公共层

## 方案选择

采用仓库现有的“单站点单文件 + 单测”方案：

- 对外保持 `Spider` 接口兼容
- 对内拆分为 API 请求、参数归一、列表项归一、分页处理、网盘类型识别、详情播放源提取几个 helper
- 保留参考 JS 的核心接口映射和过滤参数含义，但输出改为仓库可直接消费的 `vod_play_from` / `vod_play_url`

不复刻参考 JS 的驱动解析逻辑，原因是：

- 当前 Python 仓库没有对应的运行时网盘驱动注入机制
- 用户已明确要求“直接返回分享链接”
- 单测应保持纯离线，不依赖外部驱动行为

## 模块边界

新增脚本只在站点文件内部维护逻辑，不修改 `base/`。

脚本内部职责拆分如下：

- `init`
  - 初始化 API 地址、鉴权参数、请求头、分类和缓存
- `homeContent`
  - 返回固定 `class`，并附带电影/电视剧筛选项
- `homeVideoContent`
  - 调用热门接口，返回首页推荐
- `categoryContent`
  - 根据分类和扩展参数请求对应 API，并归一化结果
- `searchContent`
  - 请求搜索接口，做名称过滤、本地去重和分页
- `detailContent`
  - 请求详情接口，提取影片元数据与网盘分享线路
- `playerContent`
  - 对分享链接直接透传
- 私有辅助函数
  - 构造带鉴权的 API URL
  - 发送请求并解析 JSON
  - 归一化列表与详情对象
  - 解析扩展筛选参数
  - 本地去重与分页
  - 识别网盘类型并构造播放线路

## API 与请求策略

固定配置如下：

- API 根地址：`https://web5.mukaku.com/prod/api/v1/`
- `app_id`：`83768d9ad4`
- `identity`：`23734adac0301bccdcb107c4aa21f96c`

接口映射如下：

- `homeContent`
  - `getVideoTypeList`
- `homeVideoContent`
  - `getVideoList`，参数 `sc=3`
- `categoryContent`
  - 电影、电视剧：`getVideoMovieList`
  - 热门分类：`getVideoList`
- `searchContent`
  - `getVideoList`
- `detailContent`
  - `getVideoDetail`

请求原则：

- 统一通过 `self.fetch` 发起 GET 请求
- 超时固定为 10 秒
- 请求头包含桌面浏览器 `User-Agent`
- JSON 解析兼容普通 JSON 字符串和带 `callback(...)` 包装的响应
- 请求失败时返回空列表或空对象，不抛出未处理异常
- 不额外引入重试和持久缓存

## 分类与筛选设计

首页固定分类为：

- `1 -> 电影`
- `2 -> 电视剧`
- `3 -> 近日热门`
- `4 -> 本周热门`
- `5 -> 本月热门`

`homeContent` 返回：

- `class`
- `filters`

筛选项只对电影和电视剧提供，来源于 `getVideoTypeList`，字段沿用参考实现：

- `sc` 影视类型
- `sd` 制片地区
- `se` 上映年份
- `sf` 资源画质
- `sh` 影视标签
- `sg` 排序方式
- `iswp` 仅网盘资源
- `status` 剧集状态，仅电视剧可用

筛选值归一原则：

- `不限`、`0`、空字符串统一视为未设置
- 排序默认值使用 `1`
- `iswp` 只接受 `0/1`
- `ext` 兼容 JSON、URL 编码 JSON 和 Base64 JSON

## 列表、搜索与分页设计

列表项统一映射为：

- `vod_id`
  - 使用上游 `doub_id`
- `vod_name`
  - 使用 `title`
- `vod_pic`
  - 使用 `image` 或 `epic`
- `vod_remarks`
  - 优先 `ejs`，回退 `zqxd`
- `vod_year`
  - 使用 `years`
- `vod_content`
  - 使用 `abstract`
- `vod_actor`
  - 使用 `performer`
- `vod_director`
  - 使用 `director`
- `vod_area`
  - 使用 `production_area`

分类处理分两类：

- 电影、电视剧
  - 直接使用后端分页接口 `getVideoMovieList`
  - 单页结果按 `doub_id` 去重
  - 返回 `page/limit/total/list`
- 热门分类
  - 因上游分页不稳定，固定抓取较大批量结果后本地去重和分页
  - 返回 `page/limit/total/list`

搜索处理规则：

- 调用 `getVideoList`
- 为避免非标题命中造成噪声，额外按标题包含关键字做一次过滤
- 结果按 `doub_id` 去重
- 再做本地分页

为了符合仓库当前约定，分类和搜索结果不返回 `pagecount`。

## 详情页设计

详情页输出单个视频对象，字段至少包含：

- `vod_id`
- `vod_name`
- `vod_pic`
- `vod_remarks`
- `vod_year`
- `vod_content`
- `vod_actor`
- `vod_director`
- `vod_area`
- `vod_play_from`
- `vod_play_url`

详情数据源直接使用 `getVideoDetail` 返回对象，不依赖列表缓存。

播放源策略只处理 `movies_online_seed`：

- 忽略参考 JS 中的 `ecca` 和 `all_seeds` 磁力资源
- 遍历 `movies_online_seed` 的每个分享项
- 每个有效分享链接独立生成一条线路
- 线路名格式为 `驱动类型#序号`，例如 `quark#1`、`baidu#2`
- 如果无法识别类型，则归类为 `other#序号`
- 同一链接去重，避免详情页重复输出

`vod_play_from` 示例：

- `baidu#1$$$quark#1$$$aliyun#1`

`vod_play_url` 示例：

- `baidu#1$https://pan.baidu.com/s/xxx$$$quark#1$https://pan.quark.cn/s/yyy`

## 网盘类型识别设计

按分享链接域名识别常见网盘类型：

- `pan.quark.cn` -> `quark`
- `pan.baidu.com` -> `baidu`
- `pan.xunlei.com` -> `xunlei`
- `www.alipan.com` 或 `aliyundrive.com` -> `aliyun`
- `123865.com`、`123684.com`、`123pan.com` -> `a123`
- 其余 -> `other`

如果 API 返回的分组名本身包含可用类型，但链接域名识别不到，则回退使用分组名归一后的结果。

## 播放设计

`playerContent` 不做任何解析：

- 如果传入的是普通分享链接，直接返回 `{"parse": 0, "url": link}`
- 如果未来上层传入了 `push://` 前缀，也兼容去前缀后返回原始分享链接

本次不支持：

- 直链视频嗅探
- 网盘二次跳转
- 播放头注入
- 网盘分享码自动处理

## 错误处理设计

错误处理以“返回空结果，不中断链路”为原则：

- API 请求失败
  - 列表接口返回空列表
  - 详情接口返回空对象，`detailContent` 最终返回空列表
- JSON 解析失败
  - 记录日志后按空结果处理
- 详情中无网盘资源
  - 返回正常元信息，`vod_play_from` 和 `vod_play_url` 置空
- 搜索关键字为空
  - 直接返回空列表

## 测试设计

按 TDD 补充 `py/tests/test_灵机搜盘.py`，全部使用 `unittest.mock` 隔离网络请求。

首批测试覆盖：

1. `homeContent` 返回固定分类，并只给电影、电视剧生成筛选项。
2. `homeVideoContent` 使用 `sc=3` 请求热门列表并归一化字段。
3. `categoryContent` 在电影分类下正确构造筛选参数，并且不返回 `pagecount`。
4. `categoryContent` 对热门分类执行本地去重分页。
5. `searchContent` 对标题关键字做二次过滤并去重。
6. `detailContent` 能把多个网盘链接拆成独立线路并生成 `quark#1` 这类线路名。
7. `detailContent` 忽略磁力资源，只保留网盘分享链接。
8. `playerContent` 直接透传分享链接或去掉 `push://` 前缀。
9. 网盘类型识别覆盖百度、夸克、迅雷、阿里、123 盘和兜底类型。

## 实施约束

- 文件命名使用中文站点名：`不太灵.py`
- 保持 helper 粒度适中，避免把 API 参数、详情播放源和分页逻辑堆在单个大函数里
- 不修改现有 Spider 的行为
- 先写测试并验证失败，再写实现代码
