# 双星 Python 爬虫设计

**日期：** 2026-04-29

## 目标

在当前 Python Spider 仓库中新增独立单站蜘蛛 `双星.py`。

目标站点主域名固定为：

- `https://1.star2.cn`

行为边界以用户提供的 Python 参考实现为准，并对齐当前仓库蜘蛛接口：

- 支持固定分类输出
- 支持分类分页列表
- 支持关键字搜索
- 支持详情页标题和网盘链接整理
- `playerContent` 只透传已识别的网盘分享链接
- 不做站内播放页解析

## 范围

本次实现包含：

- 新增蜘蛛文件 `py/双星.py`
- 新增测试文件 `py/tests/test_双星.py`
- 补充对应 spec 和 plan 文档

本次实现不包含：

- 抽取新的公共盘站基类
- 修改 `base/` 公共层
- 增加站内直链解析
- 接入外部聚合蜘蛛
- 实现多备用域名 failover

## 现状

仓库中已经存在多份结构接近的网盘聚合站蜘蛛，尤其是：

- `py/欧歌.py`
- `py/闪电.py`
- `py/二小.py`

这些实现已经验证了当前仓库对同类站点的稳定接入方式：

- `homeContent/homeVideoContent/categoryContent/searchContent/detailContent/playerContent` 作为统一入口
- `vod_id` 保持为站内短路径
- `detailContent` 只负责把详情页里的网盘分享链接整理成播放线路
- `playerContent` 不做二次路由，直接对支持的网盘链接透传

双星和上述盘站不同的一点是：

- 首次访问首页后需要缓存响应 cookie，后续列表、搜索和详情请求都要带回该 cookie

因此，本次工作的重点是：

- 在现有盘站模式下补上 cookie 初始化链路
- 按双星页面结构实现列表、搜索和详情解析
- 保持 `playerContent` 返回形状与仓库现有蜘蛛兼容

## 方案选择

采用“独立单站实现 + 仓库接口适配”的方案。

### 方案 A：推荐

- 新增 `py/双星.py`
- 参考用户给出的 Python 逻辑实现 cookie 初始化和 DOM 解析
- 对外接口对齐仓库现有 `Spider` 约定
- 使用 `unittest` 做离线单测

优点：

- 与当前仓库现有调用链兼容
- 风险边界小
- 测试可直接复用已有盘站蜘蛛的断言模式

### 方案 B：不采用

- 严格照搬用户参考中的 `route/id` 分发模式

不采用原因：

- 与当前仓库 `playerContent` 返回结构不一致
- 会在单站蜘蛛里引入额外的路由语义
- 对当前调用方没有直接收益

## Spider 对外行为

### 文件

- `py/双星.py`
- `py/tests/test_双星.py`

### `init`

初始化时访问首页：

- URL：`https://1.star2.cn`
- 请求头至少包含 `User-Agent` 和 `Referer`
- `allow_redirects=False`

从首页响应 cookies 中提取 `name=value`，按 `; ` 拼接后缓存到实例字段中。

设计约束：

- `init` 失败不做复杂重试
- 后续请求统一通过 helper 带上缓存 cookie
- 如果 cookie 为空，后续请求仍然允许继续发送基础请求头

### `homeContent`

返回固定 7 个分类：

- `ju -> 国剧`
- `zy -> 综艺`
- `mv -> 电影`
- `rh -> 日韩`
- `ym -> 英美`
- `wj -> 外剧`
- `dm -> 动漫`

返回结构：

```python
{"class": [...]}
```

不返回筛选项。

### `homeVideoContent`

返回：

```python
{"list": []}
```

### `categoryContent`

分类 URL：

- `/{cate_id}_{page}/`

例如：

- `/ju_1/`

解析容器：

- `body > div > div > main > div > ul > li`

每个列表项提取：

- `vod_id`：`div.a > a[href]`
- `vod_name`：`div.a > a` 文本
- `vod_pic`：固定空字符串
- `vod_remarks`：固定空字符串

结果结构包含：

- `page`
- `limit`
- `total`
- `list`

不返回 `pagecount`。

`limit` 采用站点参考中的每页基准值 `15`，`total` 采用仓库当前惯例的保守估算：

- `total = (page - 1) * 15 + len(list)`

这样可以避免伪造不可验证的总页数。

### `searchContent`

搜索 URL：

- `/search/?keyword={quote(keyword)}&page={page}`

空关键词直接返回：

```python
{"page": page, "total": 0, "list": []}
```

解析容器与字段同分类页：

- `body > div > div > main > div > ul > li`
- `vod_id`：`div.a > a[href]`
- `vod_name`：`div.a > a` 文本
- `vod_pic`：空字符串
- `vod_remarks`：空字符串

返回结构包含：

- `page`
- `total`
- `list`

### `detailContent`

输入 `vod_id` 为站内相对路径，例如：

- `/post/123`

内部请求时用 `urljoin` 拼成完整详情 URL。

详情页提取：

- 标题：`body > div > div.s20erx.erx-m-bot.erx-content > main > article > h1`
- 分享链接：`#maximg > div.dlipp-cont-wp > div > div.dlipp-cont-bd > a[href]`

输出字段：

- `vod_id`
- `vod_name`
- `vod_pic`
- `vod_remarks`
- `vod_content`
- `vod_director`
- `vod_actor`
- `vod_play_from`
- `vod_play_url`

其中：

- `vod_pic` 固定空字符串
- `vod_remarks` 固定空字符串
- `vod_content` 固定空字符串
- `vod_director` 固定空字符串
- `vod_actor` 固定空字符串

### `playerContent`

对已识别网盘分享链接返回：

```python
{"parse": 0, "playUrl": "", "url": id}
```

对未识别链接返回：

```python
{"parse": 0, "playUrl": "", "url": ""}
```

不返回 `route/id` 风格结构。

## URL 与请求设计

### 主域名

- `https://1.star2.cn`

### 基础请求头

- `User-Agent`：沿用用户给定的浏览器 UA
- `Referer`：`https://1.star2.cn`

### 请求 helper

实现两个内部 helper：

- `_headers()`：生成带 cookie 的请求头
- `_get_html(url)`：统一请求 HTML 文本

`_headers()` 规则：

- 始终带 `User-Agent`
- 始终带 `Referer`
- 仅在缓存 cookie 非空时追加 `cookie`

`_get_html(url)` 规则：

- 统一通过 `self.fetch` 请求
- 失败时返回空字符串或由上层解析成空结果
- 不在 helper 内猜测页面编码之外的站点行为

## 页面解析策略

### HTML 解析方式

优先使用仓库现有 `self.html()` + XPath，而不是引入 `BeautifulSoup` 新依赖。

原因：

- 与当前仓库其他蜘蛛一致
- 单测更容易直接构造 HTML 片段
- 避免为一个站点引入不同解析风格

### 列表与搜索卡片

站点参考选择器较深，但字段实际很少，只提取以下最稳定的数据：

- `href`
- 文字标题

如节点缺失，直接跳过当前卡片，不做兜底猜测。

### 详情页分享链接

详情页只收集 `a[href]` 中真实可用的分享链接：

- 空链接跳过
- 重复链接去重
- 未识别网盘类型的链接跳过

## 网盘线路规则

支持识别以下 9 类网盘：

- `quark`：夸克
- `ali`：阿里
- `115`：115
- `tianyi`：天翼
- `uc`：UC
- `baidu`：百度
- `xunlei`：迅雷
- `123pan`：123
- `yd`：移动云盘

域名识别规则：

- `quark`：`quark`
- `115`：`115.com`
- `tianyi`：`cloud.189.cn`
- `uc`：`drive.uc.cn` 或 `uc.cn`
- `baidu`：`pan.baidu.com`
- `xunlei`：`xunlei`
- `123pan`：`123pan`
- `yd`：`caiyun` 或 `139.com`
- `ali`：`aliyundrive` 或 `alipan`

### 排序与命名

线路输出顺序固定为：

1. `quark`
2. `ali`
3. `115`
4. `tianyi`
5. `uc`
6. `baidu`
7. `xunlei`
8. `123pan`
9. `yd`

每个线路名使用稳定 key，而不是展示中文：

- `vod_play_from = "quark$$$ali$$$baidu"...`

每个线路内的剧集项使用展示名加 `$` 拼接：

- `夸克资源$https://pan.quark.cn/s/demo`
- `百度资源$https://pan.baidu.com/s/demo`

多个同类链接使用 `#` 拼接。

### 组装规则

详情页提取到的分享链接经过以下流程：

1. 去空
2. 去重
3. 识别网盘类型
4. 按预定义顺序分组
5. 生成 `vod_play_from`
6. 生成 `vod_play_url`

设计上不为同类链接额外制造 `夸克1/夸克2` 这样的条目名。

原因：

- 当前仓库同类盘站一般使用统一展示名
- 用户最终消费的是分享链接，不依赖人工编号
- 可减少无意义字符串差异，便于测试断言

## 异常与空结果策略

### 分类页 / 搜索页

当请求失败、HTML 为空或解析不到卡片时，返回空列表，但结构保持稳定。

### 详情页

当请求失败或解析失败时，返回：

- `{"list": []}`

不返回半残缺占位对象。

原因：

- 当前仓库多数新蜘蛛对详情失败采取空列表回退
- 比返回字段为空但看似成功的对象更容易让调用方识别失败

### `playerContent`

不尝试修正、跳转或二次解析链接：

- 支持的网盘链接直接透传
- 非支持链接直接返回空 `url`

## 测试设计

测试文件：

- `py/tests/test_双星.py`

使用 `unittest` 与 `unittest.mock`，全部通过 mock 隔离网络访问。

核心测试点：

1. `homeContent` 返回固定 7 个分类
2. `homeVideoContent` 返回空列表
3. `init` 能从首页响应 cookies 组装出 `a=1; b=2` 形式的缓存 cookie
4. `_headers()` 在 cookie 存在和不存在时都返回正确请求头
5. `categoryContent` 组装正确 URL 并解析列表卡片
6. `searchContent` 组装正确搜索 URL 并解析结果
7. `searchContent` 对空关键词直接返回空列表
8. `detailContent` 能提取标题和多类网盘链接
9. `detailContent` 会去重、过滤未知链接并按固定顺序组装线路
10. `detailContent` 在详情页请求失败时返回空列表
11. `playerContent` 透传支持的网盘链接
12. `playerContent` 拒绝非网盘链接

## 实现约束

- 不引入新的第三方依赖
- 不修改 `base/` 公共行为
- 不在 `playerContent` 中引入路由分发语义
- 不伪造 `pagecount`
- 不把完整 URL 存成列表页 `vod_id`

## 验收标准

完成后应满足：

- `homeContent(False)` 返回预期分类
- `categoryContent/searchContent` 能按参考 URL 组织请求并解析基础卡片
- `detailContent` 正确输出 `vod_play_from` 和 `vod_play_url`
- `playerContent` 对支持网盘链接返回可直接消费的透传结构
- 新增单测全部通过
