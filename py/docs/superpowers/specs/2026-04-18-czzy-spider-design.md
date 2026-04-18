# 厂长资源 Python 爬虫设计

## 目标

在当前仓库中新增一个符合 `base.spider.Spider` 接口的厂长资源爬虫，覆盖以下能力：

- 分类列表
- 详情页
- 搜索
- 播放解析

实现以网页抓取为主，不依赖私有 API，不改动 `base/` 公共层。

## 范围

本次实现包含：

- 新增独立站点脚本，暂定文件名为 `厂长资源.py`
- 内置站点主机列表：
  - `https://www.cz01.org`
  - `https://www.czzy89.com`
- 支持站内播放链接解析
- 支持网盘资源保留并透传给上层

本次实现不包含：

- 通用网页源框架抽象
- 持久化 host 健康检查缓存
- 对站点全部历史分类页面做完全覆盖

## 方案选择

采用 `requests + lxml` 直接抓取网页 DOM，并吸收参考插件 `plugin_czzy` 中已经验证过的页面结构与播放器解析规则。

不选择直接平移整份 JS 逻辑到 Python，原因是：

- Python 代码可读性会更高
- 更容易适配当前 `Spider` 接口
- 只保留确实需要的站点规则，减少无关实现

## 模块边界

新增脚本只在站点文件内部维护逻辑，不修改 `base/`。

脚本内部职责拆分如下：

- `init`
  - 初始化 host 列表、请求头、分类映射和运行期缓存
- `homeContent`
  - 返回固定分类与筛选定义
- `categoryContent`
  - 按分类拼接列表页 URL 并解析卡片
- `detailContent`
  - 解析影片基础信息与播放列表
- `searchContent`
  - 调用站内搜索页并复用卡片解析
- `playerContent`
  - 解析剧集页和播放器 iframe，产出最终播放 URL
- 若干私有辅助函数
  - host 回退
  - 页面请求
  - 卡片解析
  - 详情解析
  - 剧集解析
  - iframe 播放解析

## Host 策略

站点域名容易变更，因此实现内置候选 host 列表。请求策略如下：

1. 优先使用当前可用 host
2. 若请求失败、返回空页面、或关键节点缺失，则依次尝试下一候选 host
3. 一旦发现可用 host，将其提升为当前优先 host

判定页面是否可用时，不只看 HTTP 200，还要检查关键 DOM 是否存在，例如：

- 分类页是否存在媒体卡片
- 搜索页是否存在结果卡片或搜索结果容器
- 详情页是否存在标题或播放列表容器

## 分类设计

分类使用稳定的字符串 ID，而不是数字 ID，避免额外映射层。首批支持以下分类：

- `movie`
- `tv`
- `anime`
- `cn_movie`
- `in_movie`
- `ru_movie`
- `ca_movie`
- `jp_movie`
- `kr_movie`
- `western_movie`
- `cn_drama`
- `jp_drama`
- `us_drama`
- `kr_drama`
- `intl_drama`

每个分类映射到站点的固定路径，例如：

- `movie -> /movie_bt/movie_bt_series/dyy/page/{pg}`
- `tv -> /movie_bt/movie_bt_series/dianshiju/page/{pg}`

首页推荐 `homeVideoContent` 保持空列表，避免额外抓取首页并降低不稳定性。

## 列表与搜索解析

分类页与搜索页共用同一套卡片解析逻辑 `parse_media_cards(html)`。

卡片提取策略：

- 详情链接：优先取卡片内主链接 `href`
- 标题：优先取图片 `alt`，其次链接 `title`，再回退到卡片文本
- 图片：依次尝试 `data-original`、`data-src`、`src`
- 备注：优先取集数或清晰度角标，如 `jidi`、`hdinfo`

输出字段：

- `vod_id`
  - 直接使用详情页相对路径或绝对路径，避免额外查表
- `vod_name`
- `vod_pic`
- `vod_remarks`

分页策略：

- `page = 当前页`
- `limit = 24` 或按实际卡片数返回
- `pagecount = pg + 1` 作为保守值
- `total` 采用近似值，不依赖站点总数统计

如果当页没有结果，则返回空列表，并将 `pagecount` 设为当前页，避免上层无限翻页。

## 详情页设计

`detailContent` 通过 `vod_id` 请求详情页，提取：

- `vod_name`
- `vod_pic`
- `vod_year`
- `vod_area`
- `vod_actor`
- `vod_director`
- `vod_content`

剧集来源分为两组：

1. 站内播放
   - 来自 `paly_list_btn`
2. 网盘资源
   - 来自 `ypbt_down_list`

播放源组织方式：

- `vod_play_from = "厂长资源$$$网盘资源"`
- `vod_play_url = "<站内剧集串>$$$<网盘资源串>"`

这样上层可以明确区分站内播放与网盘分享链接，不会混在同一条线路里。

剧集项格式：

- 站内播放：`标题$剧集页URL`
- 网盘资源：`标题$分享链接`

如果某一来源没有数据，则只返回存在的来源，不保留空占位。

## 播放解析设计

`playerContent(flag, id, vipFlags)` 的行为按来源分流：

### 站内播放

1. 请求剧集页
2. 提取页面中的 `iframe src`
3. 请求 iframe 页面，并带正确 `Referer`
4. 按顺序尝试以下解析方式：
   - 解析 `var player` 和 `var rand`，做 AES 解密后读取 `url`
   - 读取并解混淆 `data`
   - 直接提取 `mysvg`
   - 直接提取 `art.url`
   - 解析包含 `window.wp_nonce` 的脚本作为兜底
5. 成功后返回：
   - `parse = 0`
   - `url = 最终播放 URL`
   - `playUrl = ""`
   - `header = {"User-Agent": "...", "Referer": "..."}`

### 网盘资源

不做二次解析，直接返回原始分享链接，让上层播放器或网盘插件处理：

- `parse = 0`
- `url = 原始分享链接`
- `playUrl = ""`

## 请求与兼容性

统一请求头：

- 浏览器 `User-Agent`
- 详情页与 iframe 页设置正确 `Referer`

必要时维护简单 cookie jar，用于：

- 首次访问站点后记录下发 cookie
- 后续请求带回同域 cookie

优先先做无状态请求；若验证发现某些页面必须依赖 cookie，再补上轻量 cookie 维护。

## 错误处理

实现遵循“失败可回退、最终返回空而非抛出”的原则：

- 单个 host 请求失败时切换到备选 host
- 单种播放器解析失败时继续尝试下一种规则
- 所有规则失败时返回空 URL，而不是抛出异常中断调用
- 详情页缺失部分字段时返回空字符串，不影响剧集列表输出

日志仅保留必要调试信息，避免刷屏。

## 测试设计

采用测试优先方式实现，先为关键解析逻辑补测试，再写生产代码。

测试重点放在纯解析函数，不依赖真实网络：

1. 分类卡片解析
   - 输入参考 HTML 片段
   - 断言标题、封面、备注、详情链接解析正确
2. 详情页剧集解析
   - 断言能区分站内播放与网盘资源
   - 断言重复链接会去重
3. iframe 播放解析
   - 覆盖 `iframe src` 提取
   - 覆盖 `mysvg`、`art.url`、`data` 等直接解析路径
4. host 回退
   - 模拟首个 host 失败、第二个成功
   - 断言当前 host 被更新

集成验证以手工调用为辅：

- `homeContent`
- `categoryContent`
- `searchContent`
- `detailContent`
- `playerContent`

如果当前仓库尚无正式测试框架，本次可以新增最小化 `unittest` 测试文件。

## 实施顺序

1. 新增测试文件，覆盖纯解析与 host 回退
2. 新增 `厂长资源.py` 基本骨架与分类映射
3. 实现列表页和搜索页抓取
4. 实现详情页和播放列表组织
5. 实现播放器多策略解析
6. 运行测试与基础手工验证

## 风险

- 站点 HTML 结构可能随时变化
- 播放器页混淆规则可能变更
- 某些 host 可能对 Referer 或 cookie 敏感

对应策略：

- 解析逻辑采用多重回退
- host 失败时自动切换
- 测试覆盖核心解析函数，降低回归风险
