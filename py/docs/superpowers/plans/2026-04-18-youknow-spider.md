# YouKnowTV Spider Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在当前 Python 仓库中新增一个符合 `base.spider.Spider` 接口的 YouKnowTV 爬虫，支持 `home/homeVideo/category/detail/search/player` 全链路。

**Architecture:** 采用单文件站点脚本 `youknow.py` 承担 YouKnowTV 规则，内部拆分为 URL/ID 归一化、列表卡片解析、详情字段解析、多线路剧集对齐和播放候选直链解析几组辅助方法。测试沿用当前仓库 `unittest + SourceFileLoader + mock` 风格，优先覆盖纯解析函数和高层方法的 mock 网络流程，不依赖真实站点网络。

**Tech Stack:** Python 3, `requests`, `lxml`, `unittest`, `unittest.mock`, `json`, `base64`, `re`, `urllib.parse`

---

## File Structure

- Create: `youknow.py`
  - YouKnowTV 站点实现，继承 `base.spider.Spider`
  - 暴露 `init`、`homeContent`、`homeVideoContent`、`categoryContent`、`detailContent`、`searchContent`、`playerContent`
  - 私有方法负责 URL/ID 归一化、列表卡片解析、详情解析、剧集 payload 序列化与播放候选直链解析
- Create: `tests/test_youknow.py`
  - 用 `SourceFileLoader` 加载 `youknow.py`
  - 用 HTML/JS 片段与 mock response 测试首页、分类、搜索、详情和播放器解析

### Task 1: Scaffold Spider, Home Flow, And List/Search Parsing

**Files:**
- Create: `tests/test_youknow.py`
- Create: `youknow.py`

- [ ] **Step 1: Write the failing test**

```python
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
MODULE = SourceFileLoader("youknow_spider", str(ROOT / "youknow.py")).load_module()
Spider = MODULE.Spider


class TestYouKnowSpider(unittest.TestCase):
    def setUp(self):
        self.spider = Spider()
        self.spider.init()

    def test_home_content_exposes_expected_categories(self):
        content = self.spider.homeContent(False)
        class_ids = [item["type_id"] for item in content["class"]]
        self.assertEqual(class_ids, ["index", "drama", "movie", "variety", "anime", "short", "doc"])

    def test_parse_list_cards_extracts_compact_vod_id(self):
        html = """
        <a class="module-poster-item" href="/v/1234.html" title="示例影片" data-original="/cover.jpg">
          <div class="module-item-note">更新至10集</div>
        </a>
        """
        cards = self.spider._parse_list_cards(html)
        self.assertEqual(
            cards,
            [{
                "vod_id": "1234",
                "vod_name": "示例影片",
                "vod_pic": "https://www.youknow.tv/cover.jpg",
                "vod_remarks": "更新至10集",
            }],
        )

    @patch.object(Spider, "_request_html")
    def test_home_video_content_uses_today_updates_page(self, mock_request_html):
        mock_request_html.return_value = """
        <a class="module-poster-item" href="/v/111.html" title="今日更新" data-original="/recent.jpg">
          <div class="module-item-note">HD</div>
        </a>
        """
        result = self.spider.homeVideoContent()
        self.assertEqual(result["list"][0]["vod_id"], "111")
        self.assertEqual(result["list"][0]["vod_name"], "今日更新")

    @patch.object(Spider, "_request_html")
    def test_category_content_builds_page_result(self, mock_request_html):
        mock_request_html.return_value = """
        <a class="module-poster-item" href="/v/222.html" title="分类影片" data-original="/cate.jpg">
          <div class="module-item-note">完结</div>
        </a>
        """
        result = self.spider.categoryContent("movie", "2", False, {})
        self.assertEqual(result["page"], 2)
        self.assertEqual(result["list"][0]["vod_id"], "222")

    @patch.object(Spider, "_request_html")
    def test_search_content_reuses_card_parser(self, mock_request_html):
        mock_request_html.return_value = """
        <a class="module-poster-item" href="/v/333.html" title="搜索影片" data-original="/search.jpg">
          <div class="module-item-note">抢先版</div>
        </a>
        """
        result = self.spider.searchContent("繁花", False, "1")
        self.assertEqual(result["list"][0]["vod_id"], "333")
        self.assertEqual(result["list"][0]["vod_name"], "搜索影片")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_youknow.TestYouKnowSpider -v`
Expected: FAIL with `FileNotFoundError` for `youknow.py` or missing methods.

- [ ] **Step 3: Write minimal implementation**

```python
# coding=utf-8
import re
import sys
from urllib.parse import quote

from base.spider import Spider as BaseSpider

sys.path.append("..")


class Spider(BaseSpider):
    def __init__(self):
        self.name = "YouKnowTV"
        self.host = "https://www.youknow.tv"
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/137.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        self.categories = [
            {"type_name": "今日更新", "type_id": "index"},
            {"type_name": "剧集", "type_id": "drama"},
            {"type_name": "电影", "type_id": "movie"},
            {"type_name": "综艺", "type_id": "variety"},
            {"type_name": "动漫", "type_id": "anime"},
            {"type_name": "短剧", "type_id": "short"},
            {"type_name": "纪录片", "type_id": "doc"},
        ]
        self.category_paths = {
            "index": "/label/new/",
            "drama": "/show/1--------{pg}---/",
            "movie": "/show/2--------{pg}---/",
            "variety": "/show/3--------{pg}---/",
            "anime": "/show/4--------{pg}---/",
            "short": "/show/55--------{pg}---/",
            "doc": "/show/5--------{pg}---/",
        }

    def init(self, extend=""):
        return None

    def getName(self):
        return self.name

    def homeContent(self, filter):
        return {"class": self.categories}

    def _build_url(self, href):
        raw = str(href or "").strip()
        if not raw:
            return ""
        if raw.startswith(("http://", "https://")):
            return raw
        if raw.startswith("//"):
            return "https:" + raw
        return self.host + "/" + raw.lstrip("/")

    def _extract_vod_id(self, href):
        raw = str(href or "").strip()
        matched = re.search(r"/v/(\d+)\.html", raw)
        if matched:
            return matched.group(1)
        if re.fullmatch(r"\d+", raw):
            return raw
        return ""

    def _parse_list_cards(self, html):
        root = self.html(html)
        if root is None:
            return []
        results = []
        seen = set()
        for card in root.xpath("//*[contains(@class,'module-poster-item') or contains(@class,'module-card-item-poster')]"):
            href = ((card.xpath("./@href") or [""])[0]).strip()
            vod_id = self._extract_vod_id(href)
            title = ((card.xpath("./@title") or [""])[0]).strip() or ((card.xpath(".//@alt") or [""])[0]).strip()
            pic = (
                (card.xpath("./@data-original") or [""])[0].strip()
                or (card.xpath("./@data-src") or [""])[0].strip()
                or (card.xpath(".//@src") or [""])[0].strip()
            )
            remarks = "".join(card.xpath(".//*[contains(@class,'module-item-note') or contains(@class,'module-item-text')][1]//text()")).strip()
            if not vod_id or vod_id in seen or not title:
                continue
            seen.add(vod_id)
            results.append({
                "vod_id": vod_id,
                "vod_name": title,
                "vod_pic": self._build_url(pic),
                "vod_remarks": remarks,
            })
        return results

    def _request_html(self, path_or_url, expect_xpath=None, referer=None):
        target = path_or_url if str(path_or_url).startswith("http") else self._build_url(path_or_url)
        headers = dict(self.headers)
        headers["Referer"] = referer or (self.host + "/")
        response = self.fetch(target, headers=headers, timeout=10)
        if response.status_code != 200:
            return ""
        return response.text or ""

    def _page_result(self, items, pg):
        page = int(pg)
        pagecount = page + 1 if items else page
        return {"list": items, "page": page, "pagecount": pagecount, "limit": len(items), "total": pagecount * max(len(items), 1)}

    def homeVideoContent(self):
        html = self._request_html("/label/new/", expect_xpath="//*[contains(@class,'module-poster-item')]")
        return {"list": self._parse_list_cards(html)}

    def categoryContent(self, tid, pg, filter, extend):
        path = self.category_paths.get(tid, self.category_paths["movie"]).format(pg=pg)
        html = self._request_html(path, expect_xpath="//*[contains(@class,'module-poster-item') or contains(@class,'module-card-item-poster')]")
        return self._page_result(self._parse_list_cards(html), pg)

    def searchContent(self, key, quick, pg="1"):
        path = "/search/-------------.html?wd={0}".format(quote(key))
        html = self._request_html(path, expect_xpath="//*[contains(@class,'module-poster-item') or contains(@class,'module-card-item-poster')]")
        return self._page_result(self._parse_list_cards(html), pg)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_youknow.TestYouKnowSpider -v`
Expected: PASS for the five new tests.

- [ ] **Step 5: Commit**

```bash
git add tests/test_youknow.py youknow.py
git commit -m "feat: scaffold youknow list parsing"
```

### Task 2: Add Detail Parsing And Multi-Source Episode Payloads

**Files:**
- Modify: `tests/test_youknow.py`
- Modify: `youknow.py`

- [ ] **Step 1: Write the failing test**

```python
class TestYouKnowSpider(unittest.TestCase):
    def test_parse_detail_page_extracts_fields_and_aligns_episode_sources(self):
        html = """
        <div class="module-info-poster">
          <img data-original="/poster.jpg" />
        </div>
        <div class="module-info-heading">
          <h1>示例剧</h1>
        </div>
        <div class="module-info-content">
          <div><span>类型：</span><a>剧情</a></div>
          <div><span>地区：</span><a>大陆</a></div>
          <div><span>年份：</span><a>2026</a></div>
          <div><span>导演：</span><a>张三</a></div>
          <div><span>主演：</span><a>李四</a><a>王五</a></div>
          <div><span>语言：</span><a>国语</a></div>
          <div><span>备注：</span><span>更新至2集</span></div>
          <div><span>简介：</span><p>一段剧情简介</p></div>
        </div>
        <div data-dropdown-value="线路A"></div>
        <div data-dropdown-value="线路B"></div>
        <div class="module-play-list">
          <a href="/p/888-1-1/">第1集</a>
          <a href="/p/888-1-2/">第2集</a>
        </div>
        <div class="module-play-list">
          <a href="/p/888-2-1/">第1集</a>
          <a href="/p/888-2-2/">第2集</a>
        </div>
        """
        result = self.spider._parse_detail_page(html, "888")
        vod = result["list"][0]
        self.assertEqual(vod["vod_id"], "888")
        self.assertEqual(vod["path"], "https://www.youknow.tv/v/888.html")
        self.assertEqual(vod["vod_name"], "示例剧")
        self.assertEqual(vod["type_name"], "剧情")
        self.assertEqual(vod["vod_area"], "大陆")
        self.assertEqual(vod["vod_year"], "2026")
        self.assertEqual(vod["vod_lang"], "国语")
        self.assertEqual(vod["vod_remarks"], "更新至2集")
        self.assertEqual(vod["vod_director"], "张三")
        self.assertEqual(vod["vod_actor"], "李四,王五")
        self.assertEqual(vod["vod_content"], "一段剧情简介")
        self.assertEqual(vod["vod_play_from"], "YouKnowTV")
        first_episode = vod["vod_play_url"].split("#")[0]
        self.assertTrue(first_episode.startswith("第1集$"))
        payload = self.spider._decode_episode_payload(first_episode.split("$", 1)[1])
        self.assertEqual(payload["vod_id"], "888")
        self.assertEqual(payload["episode_index"], 1)
        self.assertEqual(len(payload["candidates"]), 2)

    @patch.object(Spider, "_request_html")
    def test_detail_content_builds_detail_request_url_from_vod_id(self, mock_request_html):
        mock_request_html.return_value = '<h1>详情影片</h1><div class="module-play-list"><a href="/p/123-1-1/">第1集</a></div>'
        result = self.spider.detailContent(["123"])
        self.assertEqual(mock_request_html.call_args.args[0], "https://www.youknow.tv/v/123.html")
        self.assertEqual(result["list"][0]["vod_id"], "123")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_youknow.TestYouKnowSpider.test_parse_detail_page_extracts_fields_and_aligns_episode_sources tests.test_youknow.TestYouKnowSpider.test_detail_content_builds_detail_request_url_from_vod_id -v`
Expected: FAIL with missing detail helpers or incorrect payload structure.

- [ ] **Step 3: Write minimal implementation**

```python
import base64
import json

    def _extract_play_meta(self, href):
        raw = str(href or "").strip()
        matched = re.search(r"/p/(\d+)-(\d+)-(\d+)/?$", raw)
        if not matched:
            return None
        return {
            "vod_id": matched.group(1),
            "source_id": matched.group(2),
            "episode_index": int(matched.group(3)),
        }

    def _build_detail_request_url(self, vod_id):
        return f"{self.host}/v/{self._extract_vod_id(vod_id)}.html"

    def _encode_episode_payload(self, payload):
        raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")

    def _decode_episode_payload(self, value):
        text = str(value or "")
        padded = text + "=" * (-len(text) % 4)
        return json.loads(base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8"))

    def _clean_text(self, text):
        return re.sub(r"\s+", " ", str(text or "").replace("\xa0", " ")).strip()

    def _extract_detail_field(self, root, label, joiner=""):
        nodes = root.xpath(f'.//*[contains(normalize-space(.), "{label}：")][1]')
        if not nodes:
            return ""
        node = nodes[0]
        texts = [self._clean_text(text) for text in node.xpath(".//text()")]
        value = "".join([text for text in texts if text and text != label + "："])
        if joiner and node.xpath(".//a"):
            return joiner.join([self._clean_text(text) for text in node.xpath(".//a//text()") if self._clean_text(text)])
        return value

    def _parse_detail_page(self, html, vod_id):
        root = self.html(html)
        title = ((root.xpath("//*[contains(@class,'module-info-heading')]//h1[1]//text()") or [""])[0]).strip()
        pic = (
            (root.xpath("//*[contains(@class,'module-info-poster')]//img/@data-original") or [""])[0].strip()
            or (root.xpath("//*[contains(@class,'module-info-poster')]//img/@src") or [""])[0].strip()
        )
        source_names = [self._clean_text(value) for value in root.xpath("//*[@data-dropdown-value]/@data-dropdown-value")]
        play_groups = root.xpath("//*[contains(@class,'module-play-list')]")
        aligned = {}
        for group_index, group in enumerate(play_groups):
            source_name = source_names[group_index] if group_index < len(source_names) else f"线路{group_index + 1}"
            for anchor in group.xpath(".//a[@href]"):
                href = (anchor.xpath("./@href") or [""])[0]
                meta = self._extract_play_meta(href)
                if not meta:
                    continue
                key = meta["episode_index"]
                aligned.setdefault(key, {"vod_id": meta["vod_id"], "episode_index": key, "title": self._clean_text("".join(anchor.xpath(".//text()"))), "candidates": []})
                aligned[key]["candidates"].append({"source": source_name, "source_id": meta["source_id"], "episode_url": self._build_url(href)})
        play_urls = []
        for episode_index in sorted(aligned):
            record = aligned[episode_index]
            payload = self._encode_episode_payload(record)
            title_text = record["title"] or f"第{episode_index}集"
            play_urls.append(f"{title_text}${payload}")
        vod = {
            "vod_id": vod_id,
            "path": self._build_detail_request_url(vod_id),
            "vod_name": title,
            "vod_pic": self._build_url(pic),
            "vod_tag": "",
            "vod_time": "",
            "vod_remarks": self._extract_detail_field(root, "备注"),
            "vod_play_from": "YouKnowTV",
            "vod_play_url": "#".join(play_urls),
            "type_name": self._extract_detail_field(root, "类型"),
            "vod_content": self._extract_detail_field(root, "简介"),
            "vod_year": self._extract_detail_field(root, "年份"),
            "vod_area": self._extract_detail_field(root, "地区"),
            "vod_lang": self._extract_detail_field(root, "语言"),
            "vod_director": self._extract_detail_field(root, "导演", joiner=","),
            "vod_actor": self._extract_detail_field(root, "主演", joiner=","),
        }
        return {"list": [vod]}

    def detailContent(self, ids):
        vod_id = ids[0]
        html = self._request_html(self._build_detail_request_url(vod_id), expect_xpath="//*[contains(@class,'module-play-list')]")
        return self._parse_detail_page(html, vod_id)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_youknow.TestYouKnowSpider.test_parse_detail_page_extracts_fields_and_aligns_episode_sources tests.test_youknow.TestYouKnowSpider.test_detail_content_builds_detail_request_url_from_vod_id -v`
Expected: PASS for the two new tests.

- [ ] **Step 5: Commit**

```bash
git add tests/test_youknow.py youknow.py
git commit -m "feat: add youknow detail parsing"
```

### Task 3: Add Player Candidate Parsing And Direct URL Resolution

**Files:**
- Modify: `tests/test_youknow.py`
- Modify: `youknow.py`

- [ ] **Step 1: Write the failing test**

```python
class TestYouKnowSpider(unittest.TestCase):
    def test_extract_player_config_reads_player_aaaa(self):
        html = '<script>var player_aaaa={"url":"https%3A%2F%2Fcdn.example%2Fa.m3u8","encrypt":"1"};</script>'
        data = self.spider._parse_player_config(html)
        self.assertEqual(data["encrypt"], "1")

    def test_decode_player_url_supports_encrypt_1_and_2(self):
        self.assertEqual(
            self.spider._decode_player_url("https%3A%2F%2Fvideo.example%2Fa.m3u8", "1"),
            "https://video.example/a.m3u8",
        )
        encoded = "aHR0cHMlM0ElMkYlMkZ2aWRlby5leGFtcGxlJTJGYi5tM3U4"
        self.assertEqual(
            self.spider._decode_player_url(encoded, "2"),
            "https://video.example/b.m3u8",
        )

    @patch.object(Spider, "_request_html")
    def test_player_content_collects_candidates_from_page_and_iframe(self, mock_request_html):
        payload = self.spider._encode_episode_payload(
            {
                "vod_id": "888",
                "episode_index": 1,
                "title": "第1集",
                "candidates": [{"source": "线路A", "source_id": "1", "episode_url": "https://www.youknow.tv/p/888-1-1/"}],
            }
        )
        mock_request_html.side_effect = [
            '<script>var player_aaaa={"url":"https%3A%2F%2Fvideo.example%2Fpage.m3u8","encrypt":"1"};</script><iframe class="embed-responsive-item" src="/embed/player.html?url=https%3A%2F%2Fvideo.example%2Fiframe.m3u8"></iframe>',
            '<html><body>https://video.example/iframe-final.m3u8</body></html>',
        ]
        result = self.spider.playerContent("YouKnowTV", payload, {})
        self.assertEqual(result["parse"], 0)
        self.assertEqual(result["url"], "https://video.example/page.m3u8")
        self.assertEqual(result["header"]["Referer"], "https://www.youknow.tv/")

    @patch.object(Spider, "_request_html")
    def test_player_content_tries_next_candidate_when_first_fails(self, mock_request_html):
        payload = self.spider._encode_episode_payload(
            {
                "vod_id": "888",
                "episode_index": 1,
                "title": "第1集",
                "candidates": [
                    {"source": "线路A", "source_id": "1", "episode_url": "https://www.youknow.tv/p/888-1-1/"},
                    {"source": "线路B", "source_id": "2", "episode_url": "https://www.youknow.tv/p/888-2-1/"},
                ],
            }
        )
        mock_request_html.side_effect = [
            '<html><body>empty</body></html>',
            '<html><body>https://video.example/backup.m3u8</body></html>',
        ]
        result = self.spider.playerContent("YouKnowTV", payload, {})
        self.assertEqual(result["url"], "https://video.example/backup.m3u8")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_youknow.TestYouKnowSpider.test_extract_player_config_reads_player_aaaa tests.test_youknow.TestYouKnowSpider.test_decode_player_url_supports_encrypt_1_and_2 tests.test_youknow.TestYouKnowSpider.test_player_content_collects_candidates_from_page_and_iframe tests.test_youknow.TestYouKnowSpider.test_player_content_tries_next_candidate_when_first_fails -v`
Expected: FAIL with missing player helpers or unresolved final URL.

- [ ] **Step 3: Write minimal implementation**

```python
from urllib.parse import unquote

    def _safe_unquote(self, value):
        try:
            return unquote(str(value or ""))
        except Exception:
            return str(value or "")

    def _base64_decode(self, value):
        text = str(value or "").replace("-", "+").replace("_", "/")
        text += "=" * (-len(text) % 4)
        try:
            return base64.b64decode(text.encode("utf-8")).decode("utf-8", errors="ignore")
        except Exception:
            return ""

    def _normalize_play_url(self, value):
        text = str(value or "").strip().replace("\\/", "/").replace("\\u0026", "&")
        if text.startswith("//"):
            return "https:" + text
        if text.startswith("/"):
            return self.host + text
        return text

    def _parse_player_config(self, html):
        matched = re.search(r"player_aaaa\s*=\s*(\{[\s\S]*?\})\s*;?", str(html or ""), re.I)
        if not matched:
            return None
        try:
            return json.loads(matched.group(1))
        except Exception:
            return None

    def _collect_direct_media_urls(self, html):
        text = str(html or "").replace("\\/", "/")
        urls = re.findall(r'https?:\/\/[^"\'\s]+?\.(?:m3u8|mp4|flv)(?:\?[^"\'\s]*)?', text, re.I)
        proto_less = ["https:" + item for item in re.findall(r'\/\/[^"\'\s]+?\.(?:m3u8|mp4|flv)(?:\?[^"\'\s]*)?', text, re.I)]
        out = []
        for value in urls + proto_less:
            normalized = self._normalize_play_url(value)
            if normalized and normalized not in out:
                out.append(normalized)
        return out

    def _decode_player_url(self, raw_url, encrypt):
        mode = str(encrypt or "0")
        if mode == "1":
            return self._normalize_play_url(self._safe_unquote(raw_url))
        if mode == "2":
            seeds = [str(raw_url or ""), self._safe_unquote(raw_url), self._safe_unquote(self._safe_unquote(raw_url))]
            candidates = []
            for seed in seeds:
                for value in [seed, self._base64_decode(seed)]:
                    if not value:
                        continue
                    candidates.append(value)
                    candidates.append(self._safe_unquote(value))
                    candidates.append(self._safe_unquote(self._safe_unquote(value)))
            for value in candidates:
                normalized = self._normalize_play_url(value)
                if any(ext in normalized.lower() for ext in (".m3u8", ".mp4", ".flv")):
                    return normalized
        return self._normalize_play_url(raw_url)

    def _collect_playable_urls_from_html(self, html):
        urls = []
        config = self._parse_player_config(html)
        if config and config.get("url"):
            decoded = self._decode_player_url(config.get("url", ""), config.get("encrypt", "0"))
            if decoded:
                urls.append(decoded)
        for value in self._collect_direct_media_urls(html):
            if value not in urls:
                urls.append(value)
        iframe = ((self.html(html).xpath("//*[contains(@class,'embed-responsive-item')][1]/@src")) or [""])[0]
        return urls, self._build_url(iframe) if iframe else ""

    def playerContent(self, flag, id, vipFlags):
        payload = self._decode_episode_payload(id)
        candidates = payload.get("candidates", []) if isinstance(payload, dict) else []
        for candidate in candidates:
            episode_url = str(candidate.get("episode_url", "")).strip()
            if not episode_url:
                continue
            page_html = self._request_html(episode_url, referer=self.host + "/")
            page_urls, iframe_url = self._collect_playable_urls_from_html(page_html)
            if iframe_url:
                iframe_html = self._request_html(iframe_url, referer=episode_url)
                iframe_urls, _ = self._collect_playable_urls_from_html(iframe_html)
                for value in iframe_urls:
                    if value not in page_urls:
                        page_urls.append(value)
            if page_urls:
                return {
                    "parse": 0,
                    "playUrl": "",
                    "url": page_urls[0],
                    "header": {"User-Agent": self.headers["User-Agent"], "Referer": self.host + "/"},
                }
        return {"parse": 0, "playUrl": "", "url": ""}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_youknow.TestYouKnowSpider.test_extract_player_config_reads_player_aaaa tests.test_youknow.TestYouKnowSpider.test_decode_player_url_supports_encrypt_1_and_2 tests.test_youknow.TestYouKnowSpider.test_player_content_collects_candidates_from_page_and_iframe tests.test_youknow.TestYouKnowSpider.test_player_content_tries_next_candidate_when_first_fails -v`
Expected: PASS for the four new tests.

- [ ] **Step 5: Run the full suite**

Run: `python -m unittest tests.test_youknow -v`
Expected: PASS with all `youknow` tests green.

- [ ] **Step 6: Commit**

```bash
git add tests/test_youknow.py youknow.py
git commit -m "feat: add youknow player parsing"
```
