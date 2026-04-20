# 黑猫 APP Python 爬虫设计

## 目标

在当前 Python 仓库中新增一个符合 `base.spider.Spider` 接口的黑猫 APP 爬虫，覆盖以下能力：

- 首页分类与筛选
- 分类列表
- 搜索
- 详情解析
- 播放解析

实现以用户提供的 Node/JS 版本为行为参考，但落地形式遵循当前仓库的单文件 Spider 约定。

## 范围

本次实现包含：

- 新增独立脚本，文件名为 `黑猫APP.py`
- 使用黑猫 APP 的 AES-CBC 接口协议
- 支持固定 `url`，并为后续动态 `site` 获取 host 预留扩展
- 支持 `home/category/detail/search/player` 全链路
- 支持分类排序、分类屏蔽和分类重命名
- 支持地区融合和年份自动补充
- 支持线路排序、线路重命名和线路屏蔽
- 为新增行为补齐 `unittest`

本次实现不包含：

- Node/Fastify 路由层
- OCR 服务联调或真实验证码识别
- 修改 `base/` 公共层
- 多站点自动探活
- 本地缓存和重试机制

## 方案选择

采用仓库现有的“单站点单文件 + 单测”方案：

- 对外保持 `Spider` 接口兼容
- 对内拆分成配置、AES 加解密、API 调用、分类处理、详情解析、播放解析几个 helper
- 保留参考 JS 的主要业务分支，但移除与仓库无关的 HTTP 路由包装

不直接照搬参考 JS 导出层的原因是：

- 当前仓库消费的是 Spider 方法，不是独立 HTTP 服务
- 单文件 Spider 与现有项目结构一致，测试成本最低
- Python 版重点应落在字段映射、短 ID 与播放分支，而不是请求分发

## 模块边界

新增脚本只在站点文件内部维护逻辑，不修改 `base/`。

脚本内部职责拆分如下：

- `init`
  - 初始化 host、API path、AES key/iv、UA、分类配置、地区融合配置、线路配置
- `homeContent`
  - 拉取初始化接口，输出分类与筛选
- `homeVideoContent`
  - 返回空列表
- `categoryContent`
  - 请求分类筛选接口，必要时执行大陆地区聚合
- `searchContent`
  - 请求搜索接口，执行本地结果过滤
- `detailContent`
  - 请求详情接口并整理影片元数据与播放列表
- `playerContent`
  - 根据线路模式、解析类型和 `vodParse` 结果输出播放信息
- 私有辅助函数
  - AES 加解密
  - API 请求
  - 年份补全
  - 地区融合
  - 线路整理
  - OCR 预留

## Host 与请求策略

默认主域使用配置中的：

- `http://app1-0-0.87333.cc`

请求策略：

- 接口路径按 `api=1` 组装为 `/api.php/getappapi.index/<endpoint>`
- 请求方法统一为 `POST`
- 请求头默认只带 `User-Agent` 与 `Accept-Encoding`
- 返回体中的 `data` 字段先做 AES-CBC 解密，再解析 JSON

扩展策略：

- 如果后续配置了 `site`，则先请求 `site` 取得真实 host，再继续后续接口请求
- 若初始化接口中出现 `system_search_verify_status`，则把搜索验证码状态置为开启

异常策略：

- 单次请求失败时尽量返回空结果，不向上抛出未处理异常
- 某个详情接口失败时允许切换备用端点继续尝试
- 播放解析失败时返回空 URL 或回退系统解析，而不是抛异常

## 配置设计

站点文件内部维护默认配置对象，至少包含：

- `name`
- `url`
- `api`
- `dataKey`
- `dataIv`
- `init`
- `search`
- `version`
- `ua`
- `headers`
- `categories`
- `areaMerge`
- `ocr`

分类管理配置：

- `blockedNames`
- `renameMap`
- `forceOrder`

地区融合配置：

- `enabled`
- `displayName`
- `mergeList`

线路管理配置：

- 线路匹配关键字
- 显示名
- 排序权重
- 解析模式
- 是否启用

这样可以把黑猫的站点差异保持在站点文件内部，避免污染公共层。

## 分类与筛选设计

`homeContent` 的输入来源是初始化接口返回的 `type_list`。

分类处理规则：

- 屏蔽名称包含在 `blockedNames` 里的分类，例如 `伦理`
- 对命中的分类名应用 `renameMap`
- 若配置了 `forceOrder`，则按配置顺序重排已保留分类

筛选转换规则：

- 将接口中的 `class/area/lang/year/sort` 转成仓库常用的筛选结构
- `sort` 对外统一映射为 `by`
- 显示名映射为 `类型/地区/语言/年份/排序`

特殊筛选处理：

- 地区筛选启用融合时，把 `中国大陆/大陆/内地` 合并显示为单个 `大陆`
- 年份筛选自动补入当前年份；若列表里无当前年份，则插入到 `全部` 后面

首页返回字段：

- `class`
- `filters`
- `list`

其中 `list` 直接复用初始化返回的分类推荐数据。

## 列表与搜索设计

分类列表使用接口：

- `typeFilterVodList`

请求参数包括：

- `type_id`
- `page`
- `area`
- `year`
- `sort`
- `lang`
- `class`

对外筛选字段中的 `by` 在请求时还原成接口所需的 `sort`。

大陆地区融合开启且用户选择融合值时：

- 不直接请求一次 `area=大陆`
- 改为依次请求 `中国大陆/大陆/内地`
- 按 `vod_id` 去重后合并结果

搜索使用接口：

- `searchList`，也允许通过配置覆盖

搜索额外规则：

- 若初始化要求验证码，且 OCR 关闭或识别失败，则返回空列表和错误信息
- 本地过滤掉 `vod_class` 包含 `伦理` 的结果
- 如果有搜索词，则只保留标题、备注或分类文本中包含关键词的结果

分页返回字段遵循仓库当前约定：

- `page`
- `limit`
- `total`
- `list`

不返回 `pagecount`。

## 详情设计

详情优先尝试两个端点：

- `vodDetail`
- `vodDetail2`

只要任一端点成功即可继续解析。

输出字段至少包含：

- `vod_id`
- `vod_name`
- `vod_pic`
- `vod_remarks`
- `vod_content`
- `vod_actor`
- `vod_director`
- `vod_year`
- `vod_area`
- `vod_play_from`
- `vod_play_url`

详情线路处理规则：

- 线路名来自 `vod_play_list[].player_info.show`
- 若线路名包含 `防走丢/群/防失群/官网` 等无意义提示词，则回退为 `1线/2线...`
- 同名线路追加序号避免冲突
- 被线路配置禁用的线路直接跳过
- 线路显示名、排序权重和解析模式从线路配置读取

每个播放条目输出为：

- `<剧集名>$<线路名>@@<模式>@@<payload>`

其中 `payload` 由以下字段拼接：

- `parse_api`
- `play_url`
- `token`
- `player_parse_type`
- `parse_type`

多集用 `#` 连接，多线路用 `$$$` 连接。

## 播放解析设计

`playerContent` 输入的 `id` 实际承载详情阶段拼好的内部播放串。

解析顺序如下：

第一层，线路被禁用：

- 直接返回空地址

第二层，自动解析线路：

- 若线路模式为 `auto`
- 则按配置里的解析器优先级调用对应 app 解析器
- 任意解析器返回可用 `url` 即结束

第三层，按 `parse_type` 直接分支：

- `parse_type == 0`
  - 认为 `play_url` 已是直链
  - 返回 `parse=0`
- `parse_type == 2`
  - 返回 `parse=1`
  - URL 为 `parse_api + play_url`

第四层，按 `player_parse_type == 2` 尝试解析接口：

- 直接请求 `parse_api + play_url`
- 如果响应 JSON 中存在 `url`，则返回直链

第五层，回退 `vodParse`：

- 先把 `play_url` 做 AES-CBC 加密
- 调用 `vodParse`
- 从返回 JSON 里提取真实 URL

返回字段统一为：

- `parse`
- `jx`
- `url`
- `header`

其中直链场景返回 `parse=0, jx=0`；需要二次解析的场景返回 `parse=1, jx=1`。

## 验证码与 OCR 设计

首版只做结构预留，不把 OCR 作为通过条件。

保留两个辅助函数：

- `replaceCode`
- `getVerificationCode`

行为约束：

- 只有在初始化明确声明搜索需要验证码时才尝试获取
- 若 `ocr.enabled` 为 `false`，则搜索直接返回空列表和错误信息
- 不在单测中依赖真实 OCR 服务

## 测试设计

新增 `tests/test_黑猫APP.py`，覆盖最小可验证行为：

- 初始化后首页分类会按配置过滤与重排
- 地区筛选会把大陆相关值合并
- 年份筛选会补入当前年份
- 分类请求会把 `by` 映射为 `sort`
- 选择融合地区时会发起多次请求并按 `vod_id` 去重
- 搜索会过滤 `伦理` 内容并做关键词匹配
- 详情会清洗线路名、处理重复线路名并按排序输出
- 播放解析会覆盖 `parse_type=0`
- 播放解析会覆盖 `parse_type=2`
- 播放解析会覆盖 `player_parse_type=2` 的直连分支
- 播放解析会覆盖 `vodParse` 回退分支

测试实现手段：

- 使用 `unittest`
- 通过 `patch.object` mock `_api_post`、`fetch`、`post`
- 使用固定 JSON fixture，不访问真实站点和 OCR 服务

## 风险与约束

主要风险：

- 黑猫接口 host 可能变动
- 某些接口返回结构可能在不同部署之间存在细微差异
- OCR 验证码链路依赖外部服务，不适合首版强耦合

约束处理：

- 通过站点配置与 helper 隔离 host、key、路径差异
- 详情接口按双端点兜底
- 搜索验证码默认走可关闭策略，避免首版被外部依赖卡死

## 验收标准

满足以下条件即可视为本次实现完成：

- 新增 `黑猫APP.py`，可被仓库按普通 Spider 加载
- 首页返回分类和筛选，且体现分类过滤、地区融合和年份补全
- 分类、搜索、详情、播放四条链路都有对应单测
- 单测不依赖真实网络
- 新增结果字段格式与仓库现有 Spider 保持一致
- 分类和搜索结果不返回 `pagecount`
