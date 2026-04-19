# 滴答影视 Python 爬虫设计

## 目标

在当前 Python 仓库中新增一个符合 `base.spider.Spider` 接口的滴答影视站点爬虫，覆盖以下能力：

- 首页分类与筛选
- 分类列表
- 搜索
- 详情解析
- 播放解析

实现基于站点 HTML 页面结构，不引入服务端路由层，不修改 `base/` 公共层，并且仅保留网盘资源。

## 范围

本次实现包含：

- 新增独立脚本，文件名为 `滴答影视.py`
- 使用单一站点主域：`https://www.didahd.pro`
- 支持 `home/category/detail/search/player` 主链路
- 首页返回固定分类与静态筛选配置
- 详情页仅保留网盘资源，不输出普通播放线路
- `playerContent` 仅处理网盘分享链接透传

本次实现不包含：

- 普通站内播放线路解析
- 播放页解密、直链提取与中间页跳转
- 网盘驱动对象注入和驱动缓存映射
- 多域名探活与自动切换
- 登录态、反爬绕过和浏览器自动化

## 方案选择

采用仓库现有的“单站点单文件 + 单测”方案：

- 对外保持 `Spider` 接口兼容
- 对内拆分为 URL 处理、静态筛选配置、列表卡片解析、详情页网盘资源提取和播放分流几个 helper
- 保留参考实现的筛选配置和 URL 规则，但只实现 Python Spider 需要的部分

不直接照搬参考 JS 路由层的原因是：

- 当前仓库只消费 Spider 接口，不消费站内 HTTP API
- Python 版已有稳定的 HTML 爬虫实现风格，应延续既有结构
- 本次重点是详情页网盘资源保留，不是驱动管理或中间层封装

## 模块边界

新增脚本只在站点文件内部维护逻辑，不修改 `base/`。

脚本内部职责拆分如下：

- `init`
  - 初始化主域、请求头、固定分类、静态筛选项与默认筛选值
- `homeContent`
  - 返回固定 `class` 与 `filters`
- `homeVideoContent`
  - 返回空列表，不额外抓首页推荐
- `categoryContent`
  - 按筛选模板构造分类 URL，请求 HTML 并解析卡片
- `detailContent`
  - 请求详情页，提取影片元数据和网盘资源
- `searchContent`
  - 使用站内搜索页并复用卡片解析
- `playerContent`
  - 对网盘分享链接直接透传
- 私有辅助函数
  - URL 补全
  - 筛选路径拼接
  - 卡片解析
  - 详情元信息提取
  - 网盘资源面板提取
  - 网盘线路排序与去重

## Host 与请求策略

本次只实现单域：

- `https://www.didahd.pro`

请求统一通过 `self.fetch` 发起，固定请求头至少包含：

- `User-Agent`
- `Referer`

请求原则：

- HTML 请求超时固定为 10 秒
- 请求失败时返回空 HTML 或空结果，不抛出未处理异常
- 不引入压缩解码、JS 执行或 cookie 持久化

## 分类与筛选设计

首页分类固定为：

- `1 -> 电影`
- `2 -> 电视剧`
- `5 -> 综艺`
- `4 -> 动漫`
- `3 -> 纪录片`

筛选配置直接内置到脚本中，复用用户提供的筛选定义，主要字段包括：

- `class`
- `area`
- `year`
- `lang`
- `sort`

筛选 URL 规则采用模板拼接：

- `{{fl.cateId}}-{{fl.area}}-{{fl.sort}}-{{fl.class}}-{{fl.lang}}-{{fl.letter}}---{{fypage}}---{{fl.year}}`

规则说明：

- `cateId` 来自当前分类默认配置
- 其他字段来自传入的 `extend`
- 若第一页无特殊缩略规则，仍显式保留分页段
- 当页无结果时返回当前页，避免上层无限翻页

`homeContent` 返回：

- `class`
- `filters`

不返回首页推荐列表。

## 列表与搜索设计

分类页、搜索页卡片结构统一按 `.myui-vodlist__box` 解析。

每张卡片提取：

- 链接：主 `a[href]`
- 标题：`.title a` 的 `title` 或文本
- 封面：`.lazyload` 的 `data-original` 或 `src`
- 备注：`.pic-text`

输出统一卡片结构：

- `vod_id`
- `vod_name`
- `vod_pic`
- `vod_remarks`

搜索接口使用：

- `/search/-------------.html?wd=<关键词>`

搜索结果优先解析搜索结果容器；若页面结构回退，则仍复用通用卡片解析。

分页策略采用保守估计：

- `limit` 固定为 12
- 当页有结果时，`pagecount = page + 1`
- 当页无结果时，`pagecount = page`

## 详情页设计

详情页只解析网盘资源，不保留普通播放线路。

元信息提取范围：

- 标题
- 封面
- 年份、地区、类型
- 导演、主演
- 剧情简介

详情输出字段至少包含：

- `vod_id`
- `vod_name`
- `vod_pic`
- `vod_content`
- `vod_remarks`
- `vod_year`
- `vod_area`
- `vod_class`
- `vod_director`
- `vod_actor`
- `vod_play_from`
- `vod_play_url`

### 网盘资源

详情页应定位“视频下载”或等价的下载面板，提取其中网盘链接。

支持识别的网盘线路包括：

- `quark`
- `baidu`
- `xunlei`
- `uc`
- `aliyun`

每个网盘资源条目格式：

- `标题$分享链接`

去重规则：

- 同一线路内按分享链接去重，不按标题去重
- 保留首次出现的标题文案

排序规则：

- `baidu`
- `quark`
- `uc`
- `aliyun`
- `xunlei`
- 其他未识别网盘名按原始顺序排最后

如果详情页不存在任何网盘资源：

- `vod_play_from` 为空字符串
- `vod_play_url` 为空字符串

## 播放设计

`playerContent(flag, id, vipFlags)` 仅处理网盘分享链接。

### 网盘线路

当 `id` 本身已经是网盘分享链接时，直接透传：

- `parse = 0`
- `playUrl = ""`
- `url = 原始分享链接`

识别范围至少包括：

- `drive.uc.cn`
- `pan.quark.cn`
- `pan.baidu.com`
- `pan.xunlei.com`
- `alipan.com`
- `aliyundrive.com`

### 非网盘线路

普通线路视为不支持，直接返回空：

- `parse = 0`
- `playUrl = ""`
- `url = ""`

这样可以明确表达“本 Spider 只保留网盘资源，不负责普通播放”。

## 错误处理

实现遵循“失败可回退、最终返回空结果而非抛异常”的原则：

- 页面请求失败时返回空结果
- 单条网盘资源解析失败时跳过，不影响其他条目
- 详情页缺失字段时返回空字符串
- 搜索或分类页无结果时返回空列表

## 测试设计

采用测试优先方式实现，先补单测，再写生产代码。

测试重点放在纯解析逻辑和结果结构，不依赖真实网络：

1. 首页内容
   - 断言固定分类和筛选项输出正确
2. 分类列表
   - 断言 URL 构造正确
   - 断言卡片解析正确
3. 搜索
   - 断言搜索 URL 正确
   - 断言搜索结果卡片可解析
4. 详情
   - 断言只保留网盘资源，不保留普通线路
   - 断言网盘资源按链接去重和优先级排序
5. 播放
   - 断言网盘分享链接直接透传
   - 断言普通线路返回空 URL

测试文件命名：

- `tests/test_滴答影视.py`

## 验收标准

满足以下条件即视为完成：

- 新增 `滴答影视.py`，可被仓库按现有方式加载
- `homeContent/categoryContent/detailContent/searchContent/playerContent` 返回符合当前项目习惯的数据结构
- 详情页只输出网盘线路
- 网盘资源按分享链接去重，并按优先级排序
- 播放阶段对网盘分享链接直接透传
- 新增单测通过，且不破坏现有测试
