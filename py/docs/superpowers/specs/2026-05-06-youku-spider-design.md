# 优酷蜘蛛设计

**日期：** 2026-05-06

## 目标

新增一个优酷蜘蛛实现，参考用户给出的现成规则脚本，但收敛到当前仓库真正需要的核心能力：固定分类、完整分类过滤项、首页推荐、分类分页、详情选集、搜索和播放透传。实现需要保持仓库统一的 Python 蜘蛛接口，并优先保证可测试性，而不是机械照搬规则运行时。

## 范围

本次工作只涉及优酷蜘蛛及其测试：

- 新增 [优酷.py](/home/harold/workspace/tvbox-resources/py/优酷.py)
- 新增 [tests/test_优酷.py](/home/harold/workspace/tvbox-resources/py/tests/test_优酷.py)

不做以下内容：

- 不改动其他蜘蛛
- 不引入新依赖
- 不修改公共基类
- 不在仓库内实现优酷真实播放直链解析
- 不复刻参考脚本的 `setItem/getItem` 这类运行时存储接口

## 设计原则

- 尽量保留参考规则的站点协议和外部能力
- 用 Python 实例状态替代规则脚本的全局运行时状态
- 分类过滤项必须完整保留，不做删减
- 详情元信息获取失败不能影响剧集列表和播放地址输出
- 所有网络行为都必须可通过 `fetch()` mock 隔离

## 对外行为

### 1. 基本信息

- `getName()` 返回 `优酷`
- `init()` 初始化分类翻页会话字典 `category_sessions`
- `isVideoFormat()` 返回 `True`
- `manualVideoCheck()` 返回 `False`
- `destroy()` 返回 `None`
- `localProxy()` 返回 `None`

### 2. 站点配置

实现内固定以下主机和接口：

- 主站：`https://www.youku.com`
- 分类接口：`https://www.youku.com/category/data`
- 搜索接口：`https://search.youku.com/api/search`
- 播放页主机：`https://v.youku.com`

公共请求头保留桌面浏览器 UA、`Referer`，并允许注入参考规则里的固定 Cookie。Cookie 不要求真实可用，但代码结构要允许后续替换。

### 3. 首页分类与完整过滤项

`homeContent(filter)` 返回固定分类：

- `电视剧`
- `电影`
- `综艺`
- `动漫`
- `少儿`
- `纪录片`
- `文化`
- `亲子`
- `教育`
- `搞笑`
- `生活`
- `体育`
- `音乐`
- `游戏`

同时返回完整 `filters`，内容直接按用户提供的参考规则内置，不做删减或二次裁剪。过滤项按分类名称索引，而不是数值型频道 ID。

过滤定义保留以下特征：

- 过滤项键名与优酷接口保持一致，例如 `main_area`、`tags`、`year`、`pay_type`
- 展示文案和候选值与参考规则一致
- 某些值允许逗号拼接，例如 `喜剧,搞笑`
- 年份区间、状态枚举和专题推荐项全部保留

### 4. 首页推荐

`homeVideoContent()` 直接复用 `categoryContent("电视剧", "1", False, {})` 的前 20 条结果，不单独引入第二套首页推荐协议。

这样做的原因：

- 用户需求核心是优酷分类与过滤能力
- 当前仓库并不依赖站点首页特殊推荐模块
- 复用分类第一页可以减少不可测的页面 HTML 抽取逻辑

### 5. 分类列表与翻页会话

`categoryContent(tid, pg, filter, extend)` 调用 `/category/data` JSON 接口。

请求参数设计：

- `pageNo` 使用页码 `pg`
- 第 1 页默认携带 `optionRefresh=1`
- 过滤参数整体编码为 `params=<urlencoded-json>`
- 当 `pg > 1` 且当前分类已有会话时，改为带 `session=<urlencoded-json>`

过滤参数编码规则：

- 基础对象始终包含 `type=tid`
- 将 `extend` 中非空筛选项合并进该对象
- 最终用紧凑 JSON 序列化并 URL 编码

翻页会话替代方案：

- 使用 `self.category_sessions[tid]` 保存接口返回的 `session`
- 第 1 页成功响应后写入 session
- 后续页优先使用已缓存 session
- 新响应若返回新 session，则覆盖旧值

列表解析规则：

- 读取 `data.filterData.listData`
- 每个条目取 `title`、`img`、`summary`、`subTitle`、`videoLink`
- 如果 `videoLink` 中包含 `id_`，则提取 show id
- 如果提取不到 show id，则把 `vod_id` 编码为 `url:<show_episode_search_api_url>`，其中 URL 直接使用分类条目标题作为搜索关键字，请求 `search.youku.com/api/search`
- `vod_pic` 使用 `img`
- `vod_remarks` 使用 `summary`
- `vod_content` 使用 `subTitle`

返回结构固定为：

- `list`
- `page`
- `limit`
- `total`

`limit` 固定为 `20`，`total` 使用 `page * 20 + 1` 的保守可翻页值，不返回 `pagecount`。

### 6. 搜索

`searchContent(key, quick, pg)` 调用搜索接口：

- `https://search.youku.com/api/search?pg=<pg>&keyword=<urlencoded-keyword>`

搜索解析规则：

- 遍历 `pageComponentList`
- 只处理含 `commonData` 的条目
- 从 `commonData` 中提取 `showId`、`titleDTO.displayName`、`posterDTO.vThumbUrl`、`stripeBottom`、`updateNotice`、`feature`
- `vod_id` 统一编码为 `show:<showId>`
- `vod_remarks` 使用 `stripeBottom`
- `vod_content` 使用 `updateNotice + feature`

返回结构固定为：

- `list`
- `page`

不额外返回 `pagecount` 或 `total`。

### 7. 详情与选集

`detailContent(ids)` 只处理传入列表中的第一项，并按两条路径工作。

#### 7.1 主路径：show id 详情

当 `vod_id` 为 `show:<showId>` 时：

1. 请求 `show_episode` 接口获取剧集列表
2. 读取返回中的 `serisesList`、`sourceName`
3. 若存在剧集，使用首集 `videoId` 拼出 `https://v.youku.com/v_show/id_<videoId>.html`
4. 再请求首集页面 HTML，尽量提取 `window.__INITIAL_DATA__`
5. 若成功解析页面数据，则补齐海报、标题、类型、备注、简介

剧集列表输出规则：

- 每集地址统一为 `https://v.youku.com/v_show/id_<videoId>.html`
- 标题优先用 `title`
- 展示备注优先用 `showVideoStage`，否则回退 `displayName`
- `vod_play_url` 用 `#` 拼接 `标题$页面URL`
- `vod_play_from` 使用 `sourceName`

详情字段输出：

- `vod_name`
- `vod_pic`
- `type_name`
- `vod_remarks`
- `vod_content`
- `vod_play_from`
- `vod_play_url`

#### 7.2 回退路径：搜索 URL 或缺失 show id

当 `vod_id` 为 `url:<value>`，或搜索结果需要先查出 show id 时：

1. 先请求保存的搜索 URL
2. 从 `pageComponentList[0].commonData.showId` 中提取 show id
3. 再回到主路径处理

若最终仍拿不到 show id，则返回最小详情结构和空播放列表。

### 8. 优酷人机校验与非自家源降级

详情页元信息允许降级，但剧集与播放地址尽量保留。

具体规则：

- 如果播放页 HTML 中取不到 `window.__INITIAL_DATA__`，视为可能触发人机校验
- 此时保留首集封面、标题近似值和首集 URL，并把 `vod_content` 标记为元信息获取失败但不影响播放
- 如果 `sourceName` 不是 `优酷`，则仍保留剧集列表，但简介降级为“非自家播放源，暂无完整简介”

这类降级只影响海报和文案，不影响 `vod_play_url`。

### 9. 播放

`playerContent(flag, id, vipFlags)` 不做优酷站内解析，直接返回解析型结果：

- `parse: 1`
- `jx: 1`
- `url: id`
- `header: self.headers`

与用户给出的参考规则保持一致，只负责把播放页 URL 交给外部解析器。

## 内部实现

### 辅助函数

实现保留少量站点专用 helper：

- `_headers()`：返回请求头副本
- `_abs_url(value)`：规范化图片和页面 URL
- `_encode_params(tid, extend)`：把分类和筛选项编码成接口需要的 JSON 字符串
- `_make_category_card(item)`：把分类接口条目转成仓库卡片结构
- `_extract_show_id(video_link)`：从优酷链接中提取 show id
- `_build_episode_api(show_id)`：生成 `show_episode` 接口 URL
- `_parse_initial_data(html)`：从播放页 HTML 中提取 `window.__INITIAL_DATA__`

helper 只服务优酷，不提升到公共基类。

### 详情元信息提取

从 `window.__INITIAL_DATA__` 解析时，只抽取当前仓库实际消费的字段：

- 标题
- 海报
- 类型
- 更新信息或副标题
- 简介

如果页面结构不匹配，直接降级，不做深度 DOM 兼容层。

### 错误处理

- 分类和搜索 JSON 解析失败时返回空列表
- 详情接口失败时返回最小详情结构
- 首集页面元信息解析失败时不影响播放列表
- 缺失字段时统一回退为空字符串，而不是抛出 `KeyError`

## 测试设计

新增 [tests/test_优酷.py](/home/harold/workspace/tvbox-resources/py/tests/test_优酷.py)，全部通过 mock `fetch()` 隔离网络。

测试覆盖以下行为：

1. `getName()` 返回 `优酷`
2. `homeContent()` 返回固定分类，并包含完整过滤项字典
3. `categoryContent()` 能编码筛选参数并解析列表卡片
4. `categoryContent()` 在第 2 页起会使用实例内保存的 `session`
5. `searchContent()` 能从 `pageComponentList.commonData` 解析卡片
6. `detailContent()` 能从 `show:<id>` 路径构造选集列表和详情字段
7. `detailContent()` 在搜索 URL 路径下会先解析 show id 再回到主路径
8. `detailContent()` 在元信息缺失时仍输出可播放剧集列表
9. `playerContent()` 返回 `parse=1`、`jx=1` 的透传结构
10. 非优酷源时 `vod_play_from` 仍保留来源名，且简介走降级文案

## 验收标准

1. [优酷.py](/home/harold/workspace/tvbox-resources/py/优酷.py) 能被仓库现有加载方式直接使用
2. [tests/test_优酷.py](/home/harold/workspace/tvbox-resources/py/tests/test_优酷.py) 运行通过且不依赖真实网络
3. 分类过滤项完整覆盖用户提供的参考规则
4. 分类、搜索、详情和播放四条主链路都具备可用输出
5. 人机校验或详情元信息失败时，播放列表仍然可用
6. 该实现不修改公共基类，不影响其他蜘蛛的现有行为
