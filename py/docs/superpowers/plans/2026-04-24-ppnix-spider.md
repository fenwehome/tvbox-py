# PPnix Spider Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a PPnix spider in `py/PPnix.py` with static categories and stable filters, deterministic HTML parsing, short IDs, direct m3u8 playback, and matching unit tests.

**Architecture:** Keep the spider in one file following the repository's existing adapter pattern. Use small parsing helpers for URL building, card extraction, detail metadata extraction, and compact play-ID encoding so each behavior can be tested in isolation with embedded HTML fixtures.

**Tech Stack:** Python 3.14, `unittest`, `unittest.mock`, `requests` via `base.spider.Spider.fetch`, `beautifulsoup4`, `urllib.parse`, `re`

---

### Task 1: Add failing tests for static metadata, URL builders, and card parsing

**Files:**
- Create: `py/tests/test_PPnix.py`
- Create: `py/PPnix.py`
- Test: `py/tests/test_PPnix.py`

- [ ] **Step 1: Write the failing tests**

```python
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE = SourceFileLoader("ppnix_spider", str(ROOT / "PPnix.py")).load_module()
Spider = MODULE.Spider


class TestPPnixSpider(unittest.TestCase):
    def setUp(self):
        Spider._instance = None
        self.spider = Spider()
        self.spider.init()

    def test_home_content_exposes_expected_categories_and_filter_keys(self):
        content = self.spider.homeContent(False)
        self.assertEqual([item["type_id"] for item in content["class"]], ["1", "2"])
        self.assertEqual([item["key"] for item in content["filters"]["1"]], ["class", "by"])
        self.assertEqual([item["key"] for item in content["filters"]["2"]], ["class", "by"])

    def test_build_category_url_maps_first_page_and_sort_values(self):
        self.assertEqual(
            self.spider._build_category_url("1", "1", {}),
            "https://www.ppnix.com/cn/movie/----newstime.html",
        )
        self.assertEqual(
            self.spider._build_category_url("2", "3", {"class": "爱情", "by": "hits"}),
            "https://www.ppnix.com/cn/tv/爱情---2-onclick.html",
        )

    def test_build_search_url_uses_ppnix_pattern(self):
        self.assertEqual(
            self.spider._build_search_url("繁花", "1"),
            "https://www.ppnix.com/cn/search/%E7%B9%81%E8%8A%B1--.html",
        )
        self.assertEqual(
            self.spider._build_search_url("繁花", "2"),
            "https://www.ppnix.com/cn/search/%E7%B9%81%E8%8A%B1--.html-page-2",
        )

    def test_parse_cards_extracts_short_vod_id_title_cover_and_remarks(self):
        html = '''
        <ul>
          <li>
            <a class="thumbnail" href="/cn/movie/123.html">
              <img class="thumb" src="/poster.jpg" alt="示例影片" />
            </a>
            <footer><span class="rate">HD</span></footer>
          </li>
        </ul>
        '''
        self.assertEqual(
            self.spider._parse_cards(html),
            [
                {
                    "vod_id": "movie/123.html",
                    "vod_name": "示例影片",
                    "vod_pic": "https://www.ppnix.com/poster.jpg",
                    "vod_remarks": "HD",
                }
            ],
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest py/tests/test_PPnix.py -v`  
Expected: FAIL because `py/PPnix.py` does not exist yet or required methods are missing

- [ ] **Step 3: Write minimal implementation**

```python
# coding=utf-8
import re
import sys
from urllib.parse import quote

from bs4 import BeautifulSoup
from base.spider import Spider as BaseSpider

sys.path.append("..")


class Spider(BaseSpider):
    def __init__(self):
        self.name = "PPnix[采]"
        self.host = "https://www.ppnix.com"
        self.lang_path = "/cn"
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/145.0.0.0 Safari/537.36"
            ),
            "Referer": self.host + self.lang_path + "/",
        }
        self.classes = [
            {"type_id": "1", "type_name": "电影"},
            {"type_id": "2", "type_name": "电视剧"},
        ]
        self.filters = {
            "1": [
                {"key": "class", "name": "类型", "init": "", "value": [{"n": "全部", "v": ""}, {"n": "动作", "v": "动作"}]},
                {"key": "by", "name": "排序", "init": "time", "value": [{"n": "按时间", "v": "time"}, {"n": "按人气", "v": "hits"}, {"n": "按评分", "v": "score"}]},
            ],
            "2": [
                {"key": "class", "name": "类型", "init": "", "value": [{"n": "全部", "v": ""}, {"n": "爱情", "v": "爱情"}]},
                {"key": "by", "name": "排序", "init": "time", "value": [{"n": "按时间", "v": "time"}, {"n": "按人气", "v": "hits"}, {"n": "按评分", "v": "score"}]},
            ],
        }

    def init(self, extend=""):
        return None

    def getName(self):
        return self.name

    def homeContent(self, filter):
        return {"class": self.classes, "filters": self.filters}

    def _build_url(self, value):
        raw = str(value or "").strip()
        if not raw:
            return self.host + self.lang_path + "/"
        if raw.startswith(("http://", "https://")):
            return raw
        if raw.startswith("/"):
            return self.host + raw
        return self.host + "/" + raw

    def _map_type_slug(self, tid):
        return "tv" if str(tid) == "2" else "movie"

    def _map_sort(self, value):
        return {"time": "newstime", "hits": "onclick", "score": "rating"}.get(str(value or "time"), "newstime")

    def _build_category_url(self, tid, pg, extend):
        extend = extend or {}
        slug = self._map_type_slug(tid)
        genre = str(extend.get("class", "") or "")
        page = max(int(pg), 1)
        page_part = "" if page <= 1 else str(page - 1)
        sort = self._map_sort(extend.get("by", "time"))
        return self._build_url(f"{self.lang_path}/{slug}/{genre}---{page_part}-{sort}.html")

    def _build_search_url(self, keyword, pg):
        page = max(int(pg), 1)
        suffix = "" if page <= 1 else f"-page-{page}"
        return self._build_url(f"{self.lang_path}/search/{quote(str(keyword or '').strip())}--.html{suffix}")

    def _parse_cards(self, html):
        soup = BeautifulSoup(html or "", "html.parser")
        items = []
        for node in soup.select("li"):
            anchor = node.select_one("a.thumbnail") or node.select_one("h2 a") or node.select_one("a")
            image = node.select_one("img.thumb")
            if not anchor:
                continue
            href = (anchor.get("href") or "").strip()
            match = re.search(r"/cn/(movie|tv)/\d+\.html", href)
            if not match:
                continue
            items.append(
                {
                    "vod_id": href.replace("/cn/", "").lstrip("/"),
                    "vod_name": ((image.get("alt") if image else "") or anchor.get_text(" ", strip=True)).strip(),
                    "vod_pic": self._build_url((image.get("src") if image else "") or ""),
                    "vod_remarks": (node.select_one("footer .rate") or node.select_one("footer") or "").get_text(" ", strip=True),
                }
            )
        return items
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m unittest py/tests/test_PPnix.py -v`  
Expected: PASS for the four tests above

- [ ] **Step 5: Commit**

```bash
git add py/PPnix.py py/tests/test_PPnix.py
git commit -m "feat: add PPnix spider skeleton"
```

### Task 2: Add failing tests for homepage, category, and search flows

**Files:**
- Modify: `py/tests/test_PPnix.py`
- Modify: `py/PPnix.py`
- Test: `py/tests/test_PPnix.py`

- [ ] **Step 1: Write the failing tests**

```python
from unittest.mock import patch

    @patch.object(Spider, "_request_html")
    def test_home_video_content_merges_movie_and_tv_cards(self, mock_request_html):
        mock_request_html.return_value = '''
        <div class="lists-content">
          <ul>
            <li><a class="thumbnail" href="/cn/movie/101.html"><img class="thumb" src="/m.jpg" alt="电影一" /></a><footer><span class="rate">HD</span></footer></li>
          </ul>
        </div>
        <div class="lists-content">
          <ul>
            <li><a class="thumbnail" href="/cn/tv/201.html"><img class="thumb" src="/t.jpg" alt="剧集一" /></a><footer><span class="rate">更新中</span></footer></li>
          </ul>
        </div>
        '''
        result = self.spider.homeVideoContent()
        self.assertEqual([item["vod_id"] for item in result["list"]], ["movie/101.html", "tv/201.html"])

    @patch.object(Spider, "_request_html")
    def test_category_content_uses_expected_listing_url(self, mock_request_html):
        mock_request_html.return_value = '''
        <div class="lists-content"><ul>
          <li><a class="thumbnail" href="/cn/movie/301.html"><img class="thumb" src="/c.jpg" alt="分类影片" /></a><footer><span class="rate">HD</span></footer></li>
        </ul></div>
        '''
        result = self.spider.categoryContent("1", "2", False, {"class": "动作", "by": "score"})
        self.assertEqual(
            mock_request_html.call_args.args[0],
            "https://www.ppnix.com/cn/movie/动作---1-rating.html",
        )
        self.assertEqual(result["page"], 2)
        self.assertEqual(result["list"][0]["vod_id"], "movie/301.html")
        self.assertNotIn("pagecount", result)

    @patch.object(Spider, "_request_html")
    def test_search_content_parses_only_movie_and_tv_ids(self, mock_request_html):
        mock_request_html.return_value = '''
        <div class="lists-content"><ul>
          <li><a class="thumbnail" href="/cn/movie/401.html"><img class="thumb" src="/s1.jpg" alt="搜索电影" /></a></li>
          <li><a class="thumbnail" href="/cn/topic/ignore.html"><img class="thumb" src="/s2.jpg" alt="忽略条目" /></a></li>
        </ul></div>
        '''
        result = self.spider.searchContent("搜索词", False, "1")
        self.assertEqual(
            mock_request_html.call_args.args[0],
            "https://www.ppnix.com/cn/search/%E6%90%9C%E7%B4%A2%E8%AF%8D--.html",
        )
        self.assertEqual([item["vod_id"] for item in result["list"]], ["movie/401.html"])
        self.assertNotIn("pagecount", result)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest py/tests/test_PPnix.py -v`  
Expected: FAIL because `_request_html`, `homeVideoContent`, `categoryContent`, and `searchContent` are incomplete or missing

- [ ] **Step 3: Write minimal implementation**

```python
    def _request_html(self, path_or_url, referer=None, extra_headers=None):
        target = path_or_url if str(path_or_url).startswith("http") else self._build_url(path_or_url)
        headers = dict(self.headers)
        headers["Referer"] = referer or self.headers["Referer"]
        if isinstance(extra_headers, dict):
            headers.update(extra_headers)
        response = self.fetch(target, headers=headers, timeout=10)
        if response.status_code != 200:
            return ""
        return response.text or ""

    def _dedupe(self, items):
        seen = set()
        result = []
        for item in items:
            key = item.get("vod_id")
            if not key or key in seen:
                continue
            seen.add(key)
            result.append(item)
        return result

    def homeVideoContent(self):
        html = self._request_html(self.lang_path + "/")
        soup = BeautifulSoup(html or "", "html.parser")
        blocks = soup.select(".lists-content ul")
        items = []
        if len(blocks) > 0:
            items.extend(self._parse_cards(str(blocks[0])))
        if len(blocks) > 1:
            items.extend(self._parse_cards(str(blocks[1])))
        return {"list": self._dedupe(items)[:20]}

    def categoryContent(self, tid, pg, filter, extend):
        page = max(int(pg), 1)
        items = self._parse_cards(self._request_html(self._build_category_url(tid, pg, extend or {})))
        slug = self._map_type_slug(tid)
        items = [item for item in items if item["vod_id"].startswith(slug + "/")]
        return {"page": page, "limit": 24, "total": page * 24 + len(items), "list": items}

    def searchContent(self, key, quick, pg="1"):
        page = max(int(pg), 1)
        items = self._parse_cards(self._request_html(self._build_search_url(key, pg)))
        return {"page": page, "limit": 24, "total": page * 24 + len(items), "list": items[:10] if quick else items}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m unittest py/tests/test_PPnix.py -v`  
Expected: PASS for homepage, category, and search tests

- [ ] **Step 5: Commit**

```bash
git add py/PPnix.py py/tests/test_PPnix.py
git commit -m "feat: add PPnix list and search parsing"
```

### Task 3: Add failing tests for detail parsing and direct player URLs

**Files:**
- Modify: `py/tests/test_PPnix.py`
- Modify: `py/PPnix.py`
- Test: `py/tests/test_PPnix.py`

- [ ] **Step 1: Write the failing tests**

```python
    def test_extract_m3u8_items_reads_infoid_and_episode_names(self):
        html = """
        <script>
        var infoid = 7788;
        var m3u8 = ["第1集", "第2集"];
        </script>
        """
        self.assertEqual(
            self.spider._extract_m3u8_items(html),
            {"info_id": "7788", "items": ["第1集", "第2集"]},
        )

    @patch.object(Spider, "_request_html")
    def test_detail_content_builds_ppnix_play_group(self, mock_request_html):
        mock_request_html.return_value = '''
        <h1 class="product-title">示例剧 (2025)</h1>
        <header class="product-header"><img class="thumb" src="/poster.jpg" /></header>
        <div class="product-excerpt">导演：<span>导演甲</span></div>
        <div class="product-excerpt">主演：<span>演员甲 / 演员乙</span></div>
        <div class="product-excerpt">简介：一段剧情简介</div>
        <script>
        var infoid = 8899;
        var m3u8 = ["第1集", "第2集"];
        </script>
        '''
        result = self.spider.detailContent(["tv/8899.html"])
        vod = result["list"][0]
        self.assertEqual(vod["vod_id"], "tv/8899.html")
        self.assertEqual(vod["vod_name"], "示例剧")
        self.assertEqual(vod["vod_pic"], "https://www.ppnix.com/poster.jpg")
        self.assertEqual(vod["vod_year"], "2025")
        self.assertEqual(vod["vod_director"], "导演甲")
        self.assertEqual(vod["vod_actor"], "演员甲,演员乙")
        self.assertEqual(vod["vod_content"], "一段剧情简介")
        self.assertEqual(vod["vod_play_from"], "PPnix")
        self.assertEqual(vod["vod_play_url"], "第1集$8899|%E7%AC%AC1%E9%9B%86#第2集$8899|%E7%AC%AC2%E9%9B%86")

    def test_player_content_returns_direct_m3u8_url(self):
        result = self.spider.playerContent("PPnix", "8899|%E7%AC%AC1%E9%9B%86", {})
        self.assertEqual(result["parse"], 0)
        self.assertEqual(result["jx"], 0)
        self.assertEqual(result["url"], "https://www.ppnix.com/info/m3u8/8899/%E7%AC%AC1%E9%9B%86.m3u8")
        self.assertEqual(result["header"]["Origin"], "https://www.ppnix.com")

    def test_player_content_falls_back_when_play_id_is_invalid(self):
        result = self.spider.playerContent("PPnix", "broken", {})
        self.assertEqual(result["parse"], 1)
        self.assertEqual(result["jx"], 1)
        self.assertEqual(result["url"], "broken")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest py/tests/test_PPnix.py -v`  
Expected: FAIL because detail and player helpers are still missing

- [ ] **Step 3: Write minimal implementation**

```python
from urllib.parse import quote, unquote

    def _extract_m3u8_items(self, html):
        body = html or ""
        info_match = re.search(r"infoid\s*=\s*(\d+)", body)
        list_match = re.search(r"m3u8\s*=\s*\[(.*?)\]", body, re.S)
        items = re.findall(r"'([^']*)'|\"([^\"]*)\"", list_match.group(1) if list_match else "")
        return {
            "info_id": info_match.group(1) if info_match else "",
            "items": [a or b for a, b in items if (a or b).strip()],
        }

    def _build_play_id(self, info_id, param):
        return f"{str(info_id).strip()}|{quote(str(param).strip())}"

    def _parse_play_id(self, play_id):
        parts = str(play_id or "").split("|", 1)
        if len(parts) != 2 or not parts[0] or not parts[1]:
            return {"info_id": "", "param": ""}
        return {"info_id": parts[0].strip(), "param": unquote(parts[1].strip())}

    def detailContent(self, ids):
        vod_id = str(ids[0] if isinstance(ids, list) and ids else ids or "").strip().lstrip("/")
        if not vod_id:
            return {"list": []}
        html = self._request_html(self._build_url("/" + self.lang_path.strip("/") + "/" + vod_id))
        soup = BeautifulSoup(html or "", "html.parser")
        title_raw = (soup.select_one("h1.product-title") or soup.select_one("title"))
        title_text = title_raw.get_text(" ", strip=True) if title_raw else ""
        info = self._extract_m3u8_items(html)
        play_urls = []
        for item in info["items"]:
            play_urls.append(f"{item}${self._build_play_id(info['info_id'], item)}")
        return {
            "list": [
                {
                    "vod_id": vod_id,
                    "vod_name": re.sub(r"\s*\([^)]*\)\s*$", "", title_text).strip(),
                    "vod_pic": self._build_url((soup.select_one('header.product-header img.thumb') or {}).get("src", "")),
                    "type_name": "电视剧" if vod_id.startswith("tv/") else "电影",
                    "vod_year": (re.search(r"\((\d{4})\)", title_text) or [None, ""])[1],
                    "vod_director": self._extract_excerpt_text(soup, "导演："),
                    "vod_actor": self._extract_excerpt_text(soup, "主演：").replace(" / ", ","),
                    "vod_content": self._extract_excerpt_text(soup, "简介："),
                    "vod_play_from": "PPnix" if play_urls else "",
                    "vod_play_url": "#".join(play_urls),
                }
            ]
        }

    def _extract_excerpt_text(self, soup, label):
        for node in soup.select(".product-excerpt"):
            text = node.get_text(" ", strip=True)
            if label in text:
                return text.replace(label, "", 1).strip()
        return ""

    def playerContent(self, flag, id, vipFlags):
        meta = self._parse_play_id(id)
        if not meta["info_id"] or not meta["param"]:
            return {"parse": 1, "jx": 1, "url": str(id or ""), "header": {}}
        encoded = quote(meta["param"])
        return {
            "parse": 0,
            "jx": 0,
            "url": self._build_url(f"/info/m3u8/{meta['info_id']}/{encoded}.m3u8"),
            "header": {
                "Referer": self.host + self.lang_path + "/",
                "Origin": self.host,
                "User-Agent": self.headers["User-Agent"],
            },
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m unittest py/tests/test_PPnix.py -v`  
Expected: PASS for detail and player tests

- [ ] **Step 5: Commit**

```bash
git add py/PPnix.py py/tests/test_PPnix.py
git commit -m "feat: add PPnix detail and player parsing"
```

### Task 4: Run focused verification and repo-style cleanup

**Files:**
- Modify: `py/PPnix.py`
- Modify: `py/tests/test_PPnix.py`
- Test: `py/tests/test_PPnix.py`

- [ ] **Step 1: Run the focused PPnix test module**

Run: `uv run python -m unittest py/tests/test_PPnix.py -v`  
Expected: all PPnix tests pass

- [ ] **Step 2: Tighten static filter values and helper names if test-driven cleanup is needed**

```python
self.filters = {
    "1": [
        {
            "key": "class",
            "name": "类型",
            "init": "",
            "value": [{"n": "全部", "v": ""}, {"n": "动作", "v": "动作"}, {"n": "喜剧", "v": "喜剧"}, {"n": "剧情", "v": "剧情"}],
        },
        {
            "key": "by",
            "name": "排序",
            "init": "time",
            "value": [{"n": "按时间", "v": "time"}, {"n": "按人气", "v": "hits"}, {"n": "按评分", "v": "score"}],
        },
    ],
    "2": [
        {
            "key": "class",
            "name": "类型",
            "init": "",
            "value": [{"n": "全部", "v": ""}, {"n": "爱情", "v": "爱情"}, {"n": "古装", "v": "古装"}, {"n": "悬疑", "v": "悬疑"}],
        },
        {
            "key": "by",
            "name": "排序",
            "init": "time",
            "value": [{"n": "按时间", "v": "time"}, {"n": "按人气", "v": "hits"}, {"n": "按评分", "v": "score"}],
        },
    ],
}
```

- [ ] **Step 3: Re-run the focused PPnix test module**

Run: `uv run python -m unittest py/tests/test_PPnix.py -v`  
Expected: all PPnix tests still pass after cleanup

- [ ] **Step 4: Commit**

```bash
git add py/PPnix.py py/tests/test_PPnix.py
git commit -m "test: verify PPnix spider behavior"
```
