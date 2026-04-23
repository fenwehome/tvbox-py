# 即看影视 Python 蜘蛛设计

## 目标

在当前 Python 仓库中新增一个符合 `base.spider.Spider` 接口的即看影视蜘蛛，覆盖以下能力：

- 首页分类与筛选
- 首页推荐列表
- 分类列表
- 搜索
- 详情解析
- 播放解析

实现以用户提供的 Node/JS 版本为行为参考，但落地形式遵循当前仓库的单文件 Spider 约定。

## 范围

本次实现包含：

- 新增独立脚本，文件名为 `即看影视.py`
- 使用即看影视的 `SKApp` 加密协议
- 启动时通过 `https://skyappdata-1321528676.cos.accelerate.myqcloud.com/4kapp/appipr.txt` 获取真实 `API_HOST`
- 通过 `/get_config` 获取授权 token
- 通过 `/app/config` 获取应用配置
- 支持 `home/homeVideo/category/search/detail/player` 全链路
- 为新增行为补齐 `unittest`

本次实现不包含：

- 参考代码中的 HTTP 路由导出层
- 公共 `SKApp` helper 抽象
- 动态播放规则配置
- 重试、缓存持久化和多域名探活

## 方案选择

候选方案有三种：

1. 单文件简化版
2. 单文件加初始化缓存
3. 抽公共 `SKApp` helper

选用方案 2。

原因：

- 保持与仓库现有蜘蛛的一致结构
- 避免在一次 Spider 生命周期内重复拉取 `appipr.txt`、`/get_config` 和 `/app/config`
- 不扩大本次任务范围到公共层改造

## 模块边界

新增脚本只在站点文件内部维护逻辑，不修改 `base/`。

文件内部按职责拆分为以下私有 helper：

- `_ensure_ready`
  - 负责初始化 `API_HOST`、加密参数、token 和应用配置
- `_resolve_api_host`
  - 请求 `appipr.txt` 并提取真实 host
- `_fetch_auth_token`
  - 调用 `/get_config` 获取 Bearer token
- `_fetch_app_config`
  - 调用 `/app/config` 获取播放相关配置
- `_sk_decrypt`
  - 处理 `FROMSKZZJM` 前缀响应
- `_ck_encrypt`
  - 生成 `/get_config` 所需的 `ck`
- `_fetch_api`
  - 统一拼接查询参数、附加认证头、发起请求和解密 JSON
- `_fetch_filters`
  - 逐分类请求 `/sk-api/type/alltypeextend` 并转换筛选结构

Spider 对外方法：

- `init`
- `homeContent`
- `homeVideoContent`
- `categoryContent`
- `searchContent`
- `detailContent`
- `playerContent`

## 初始化与鉴权设计

固定配置保留在站点文件内部：

- `host_config_url`
  - `https://skyappdata-1321528676.cos.accelerate.myqcloud.com/4kapp/appipr.txt`
- `aes_key`
  - `ygcnbckhcuvygdyb`
- `aes_iv`
  - `4023892775143708`
- `ck_key`
  - `ygcnbcrvaervztmw`
- `ck_iv`
  - `1212164105143708`
- `user_agent`
  - `Dart/2.10 (dart:io)`

当前 `appipr.txt` 解析出的真实地址为：

- `https://appsky2025999.ideasz.net`

初始化流程：

1. 读取 `appipr.txt` 得到 `API_HOST`
2. 校验 AES key/iv 长度为 16
3. 计算 `sign=md5(aes_key + aes_iv)`
4. 生成 `ck=<API_HOST>##5483##<timestamp>##ckzmbc` 后做 `ckEncrypt`
5. POST `/get_config` 获取授权 token
6. GET `/app/config` 获取应用配置
7. 将 `API_HOST`、`AUTH_TOKEN`、`CONFIG_DATA` 缓存在 Spider 实例上

`_ensure_ready` 在首次请求时执行，后续方法复用缓存。

## 数据映射设计

### 首页

`homeContent` 请求 `/sk-api/type/list`。

分类映射：

- 输出 `type_id`
- 输出 `type_name`

筛选映射：

- 逐分类请求 `/sk-api/type/alltypeextend`
- 将 `extendtype/area/lang/year` 分别映射成 `类型/地区/语言/年份`
- 增加固定排序项：
  - `最新 -> updateTime`
  - `人气 -> hot`
  - `评分 -> score`

首页最终返回：

- `class`
- `filters`
- `list`

其中 `list` 由 `homeVideoContent` 提供。

### 首页推荐

`homeVideoContent` 请求：

- `/sk-api/vod/list?page=1&limit=12&type=randomlikeindex`

返回：

- `{"list": data.data or []}`

### 分类

`categoryContent` 请求 `/sk-api/vod/list`，参数为：

- `typeId=tid`
- `page=pg`
- `limit=18`
- `type=extend.sort or updateTime`
- `area=extend.area or ""`
- `lang=extend.lang or ""`
- `year=extend.year or ""`
- `mtype=""`
- `extendtype=extend.class or ""`

返回结构遵循仓库约定：

- `page`
- `limit`
- `total`
- `list`

不返回 `pagecount`。

### 搜索

`searchContent` 请求 `/sk-api/search/pages`，参数为：

- `keyword`
- `page`
- `limit=10`
- `typeId=-1`

返回结构同分类列表，不返回 `pagecount`。

### 详情

`detailContent` 请求 `/sk-api/vod/one?vodId=<id>`。

优先策略：

- 如果上游 `data.data` 已经是仓库可直接消费的标准 `vod` 结构，则直接返回
- 如果上游字段不完整，再做最小必要字段补齐

详情阶段不引入额外二次端点回退，保持与参考实现一致。

## 播放设计

用户确认的固定规则是：

- 总是先请求 `/sk-api/vod/skjson`
- 失败后回退原始 `id`

`playerContent` 逻辑：

1. 调用 `/sk-api/vod/skjson?url=<id>&skjsonindex=0`
2. 如果返回 `data.url` 且为 `http` 链接，则返回：
   - `parse=0`
   - `jx=0`
   - `url=<playUrl>`
3. 如果解析失败，则回退原始 `id`
4. 如果原始 `id` 命中 `iqiyi/qq/youku/mgtv/bilibili` 域名，则返回：
   - `parse=0`
   - `jx=1`
   - `url=<id>`
5. 其他情况返回：
   - `parse=0`
   - `jx=0`
   - `url=<id>`

播放器请求头固定为移动 Safari UA，以保持与参考实现一致。

本次不实现基于 `/app/config` 中 `direct_json_link` 或 `direct_link` 的动态分支，`CONFIG_DATA` 仅作为初始化链路保留。

## 容错策略

- `_sk_decrypt` 只在响应带 `FROMSKZZJM` 前缀时尝试解密，否则按明文返回
- `appipr.txt` 为空、解密失败、JSON 解析失败时，抛出明确异常给站点内部处理
- `homeContent` 获取筛选时，单个分类失败仅跳过该分类筛选
- 列表和搜索接口异常时返回空结果结构
- 详情接口异常时返回空 `list`
- 播放解析异常时回退原始 `id`

## 测试设计

新增 `tests/test_即看影视.py`，使用 `unittest` 和 `unittest.mock`，不访问真实网络。

首轮测试覆盖：

1. 读取 `appipr.txt` 并解析真实 `API_HOST`
2. `_sk_decrypt` 对明文和加密前缀响应的处理
3. `_ck_encrypt` 返回非空密文
4. `homeContent` 正确输出分类和筛选
5. `homeVideoContent` 返回推荐列表
6. `categoryContent` 参数映射正确且不返回 `pagecount`
7. `searchContent` 返回标准分页结构
8. `detailContent` 返回 `{"list": [vod]}` 或空列表
9. `playerContent` 优先使用 `skjson` 结果
10. `playerContent` 在 `skjson` 失败时回退原始链接，并对站外视频域名设置 `jx=1`

测试顺序：

- 先跑单模块测试
- 再确认该模块无回归

## 风险与边界

- `appipr.txt` 返回的真实域名可能变化，测试中必须 mock，不依赖当前线上值
- `/app/config` 当前在简化版里不驱动播放分支，后续如果站点改成强依赖配置，播放器逻辑需要补齐
- 若上游详情字段不是标准 `vod` 结构，可能需要在实现阶段补一个轻量映射层，但范围仅限当前站点文件
