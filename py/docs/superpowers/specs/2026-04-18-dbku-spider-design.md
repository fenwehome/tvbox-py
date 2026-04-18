# 独播库 Python 爬虫设计

## 目标

在当前 Python 仓库中新增一个符合 `base.spider.Spider` 接口的独播库站点爬虫，覆盖以下能力：

- 分类列表
- 详情页
- 搜索
- 播放解析

实现基于网页 DOM 抓取，不依赖站点私有 API，不修改 `base/` 公共层。

## 范围

本次实现包含：

- 新增独立脚本，暂定文件名为 `独播库.py`
- 使用单一站点主域：`https://www.dbku.tv`
- 支持列表页、搜索页、详情页和站内播放解析

本次实现不包含：

- 多域名自动回退
- 网盘资源解析
- 通用网页源抽象框架

## 方案选择

采用 `requests + lxml` 直接抓取网页 HTML，并吸收参考插件 `plugin_dbku` 中已经验证过的 DOM 结构与 `player_data` 解析规则。

不直接把整份 JS 逐行平移到 Python，原因是：

- Python 代码更容易维护
- 更贴合当前仓库的 `Spider` 接口
- 只保留独播库真正需要的站点规则，减少噪音

## 模块边界

新增脚本只在站点文件内部维护逻辑，不修改 `base/`。

脚本内部职责拆分如下：

- `init`
  - 初始化主域、请求头、分类映射
- `homeContent`
  - 返回固定分类
- `categoryContent`
  - 请求分类页并解析媒体卡片
- `searchContent`
  - 请求搜索页并解析搜索结果
- `detailContent`
  - 提取影片基础信息和剧集列表
- `playerContent`
  - 解析剧集页中的 `player_data`，得到最终播放地址
- 私有辅助函数
  - URL 归一化
  - 列表卡片解析
  - 搜索结果解析
  - 详情页解析
  - `player_data` 提取与解码

## Host 策略

本次只实现单域：

- `https://www.dbku.tv`

请求失败时不做多域切换，只返回空结果或空播放地址。后续如果该站常态化换域，再补 host 回退。

## 分类设计

分类 ID 直接使用参考实现中的键，避免额外映射层：

- `index`
- `movie`
- `variety`
- `anime`
- `hk`
- `luju`

分类 URL 映射如下：

- `index -> /vodtype/2--------{pg}---.html`
- `movie -> /vodtype/1--------{pg}---.html`
- `variety -> /vodtype/3--------{pg}---.html`
- `anime -> /vodtype/4--------{pg}---.html`
- `hk -> /vodtype/20--------{pg}---.html`
- `luju -> /vodtype/13--------{pg}---.html`

首页推荐 `homeVideoContent` 维持空列表，避免额外抓站点首页。

## 列表与搜索解析

### 分类页

分类页主要解析 `myui-vodlist__box` 卡片。

每张卡片提取规则：

- 链接：优先选择 `href` 含 `/voddetail/` 的链接
- 标题：优先链接 `title`，回退到节点文本
- 封面：优先取 `data-original`，其次 `src`
- 描述：优先取类名含 `pic-text` 的文本，回退到卡片中首个有意义的附加文本

输出字段：

- `vod_id`
  - 直接使用详情页绝对 URL
- `vod_name`
- `vod_pic`
- `vod_remarks`

### 搜索页

搜索 URL：

- `/vodsearch/-------------.html?wd=<keyword>&submit=`

搜索结果优先解析 `#searchList` 容器内的卡片；若没有搜索容器或解析结果为空，则回退到普通列表卡片解析，以兼容不同模板。

### 分页策略

返回分页字段：

- `page = 当前页`
- `pagecount = pg + 1`，若当页无内容则为当前页
- `limit = 实际条目数`
- `total = 近似值`

不依赖站点总数统计。

## 详情页设计

`detailContent` 使用 `vod_id` 请求详情页，提取：

- `vod_name`
- `vod_pic`
- `vod_year`
- `vod_area`
- `vod_actor`
- `vod_director`
- `vod_content`

播放列表只保留站内源：

- `vod_play_from = "独播库"`

剧集项格式：

- `标题$剧集页URL`

若发现多组播放列表，先按页面顺序合并同站剧集，去重后输出为单一播放源。

## 播放解析设计

独播库播放解析核心是剧集页中的 `player_data`。

实现步骤：

1. 请求剧集页
2. 提取页面脚本中的 `player_data` JSON
3. 读取：
   - `url`
   - `from`
   - `encrypt`
4. 按 `encrypt` 解码播放地址

解码规则：

- `encrypt = 0`
  - 原样返回
- `encrypt = 1`
  - 执行 `unescape` 等价解码
- `encrypt = 2`
  - `base64` 解码后再尝试 URL 解码
- `encrypt = 3`
  - 按参考实现做裁剪后的 `base64` 变体解码

如果解码后的 URL 仍是站内中间页而不是最终播放地址，则继续请求该页面并再次尝试提取 `player_data` 或直链，直到：

- 得到最终可播放 URL
- 无法继续解析，此时返回空 URL

返回格式：

- `parse = 0`
- `playUrl = ""`
- `url = 最终播放地址`
- `header = {"User-Agent": "...", "Referer": "..."}`

## 请求与兼容性

统一请求头至少包含：

- 浏览器 `User-Agent`
- 需要时补 `Referer`

本次优先采用无状态请求；如果验证时发现独播库对 cookie 敏感，再补最小 cookie 维护。

## 错误处理

实现遵循“失败返回空，不抛异常中断”的原则：

- 页面请求失败时返回空列表或空播放 URL
- DOM 节点缺失时字段回退为空字符串
- `player_data` 解析失败时继续尝试回退规则
- 最终失败则返回 `{"parse": 0, "playUrl": "", "url": ""}`

日志只保留必要调试信息。

## 测试设计

采用测试优先方式实现，先给纯解析函数写测试，再补生产代码。

测试重点：

1. 分类卡片解析
   - 断言能从 `myui-vodlist__box` 提取详情链接、标题、封面和描述
2. 搜索结果解析
   - 断言优先使用 `#searchList`
   - 断言缺失时会回退到普通列表解析
3. 详情页解析
   - 断言影片元信息提取正确
   - 断言剧集列表生成正确并去重
4. `player_data` 解码
   - 覆盖 `encrypt = 0/1/2/3`
5. `playerContent`
   - 断言能从剧集页解析到最终播放地址

优先使用 `unittest` 和 mock，避免测试依赖真实站点网络。

## 实施顺序

1. 新增独播库测试文件，覆盖卡片、搜索、详情和播放器解析
2. 新增 `独播库.py` 基本骨架与分类映射
3. 实现分类页和搜索页抓取
4. 实现详情页和剧集列表
5. 实现 `player_data` 解码与高层 `playerContent`
6. 运行测试并做最小手工验证

## 风险

- 页面模板可能调整
- `player_data` 格式或 `encrypt` 规则可能变化
- 个别剧集可能存在站内二跳或额外播放器包装

对应策略：

- 列表和搜索解析都保留回退路径
- 播放解析按 `encrypt` 分类处理
- 测试覆盖所有已知解码路径，降低回归风险
