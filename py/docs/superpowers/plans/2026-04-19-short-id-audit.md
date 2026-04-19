# Spider 短路径 ID 审计修正 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 审计现有 Spider 的 `vod_id` 与播放 id 返回形式，并修复仍然暴露完整站内 URL 的实现，统一改为各站原始路径压缩后的短 id。

**Architecture:** 先基于现有测试和代码结构确认哪些 Spider 实际违规，再只对违规文件做最小可逆改动。每个违规 Spider 都增加短路径回归测试，并在 Spider 内部增加 `encode/decode` helper 或复用现有 helper 来完成“对外短 id、对内完整 URL”的分层。

**Tech Stack:** Python 3、`base.spider.Spider`、unittest、`unittest.mock`、lxml/XPath、regex

---

## File Structure

- Modify: `低端影视.py`
  - 将 `vod_id` 从完整 URL 压缩为站内原始路径，并在详情解析中恢复
- Modify: `滴答影视.py`
  - 将 `vod_id` 从完整 URL 压缩为站内原始路径，并在详情解析中恢复
- Modify: `tests/test_低端影视.py`
  - 覆盖 `vod_id` 短路径输出和短路径详情请求
- Modify: `tests/test_滴答影视.py`
  - 覆盖 `vod_id` 短路径输出和短路径详情请求
- Reference only: `libvio.py`, `剧迷.py`, `橘子TV.py`, `youknow.py`, `乌云影视.py`, `剧圈圈.py`
  - 只做确认，不修改

### Task 1: Audit Existing Spider Behavior And Lock Failing Tests For 低端影视

**Files:**
- Modify: `tests/test_低端影视.py`
- Reference: `低端影视.py`

- [ ] **Step 1: Write the failing tests for short detail ids in list/search/detail flows**

```python
    def test_parse_cards_returns_compact_site_path_ids(self):
        html = """
        <article>
          <a href="https://ddys.io/movie/demo/">
            <img src="https://ddys.io/demo.jpg" />
            <h2>示例影片</h2>
          </a>
        </article>
        """
        items = self.spider._parse_cards(html)
        self.assertEqual(items[0]["vod_id"], "movie/demo")

    @patch.object(Spider, "_request_html")
    def test_detail_content_decodes_compact_site_path_id(self, mock_request_html):
        mock_request_html.return_value = "<html><h1>示例影片</h1></html>"
        self.spider.detailContent(["movie/demo"])
        self.assertEqual(mock_request_html.call_args.args[0], "https://ddys.io/movie/demo/")

    @patch.object(Spider, "_request_html")
    def test_search_content_returns_compact_site_path_ids(self, mock_request_html):
        mock_request_html.return_value = """
        <article>
          <a href="https://ddys.io/movie/search-demo/">
            <img src="https://ddys.io/search.jpg" />
            <h2>搜索影片</h2>
          </a>
        </article>
        """
        result = self.spider.searchContent("搜索影片", False, "1")
        self.assertEqual(result["list"][0]["vod_id"], "movie/search-demo")
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run: `python -m unittest tests.test_低端影视.TestDDYSSpider.test_parse_cards_returns_compact_site_path_ids tests.test_低端影视.TestDDYSSpider.test_detail_content_decodes_compact_site_path_id tests.test_低端影视.TestDDYSSpider.test_search_content_returns_compact_site_path_ids -v`

Expected: `FAIL` because `低端影视.py` currently returns full detail URLs and reads detail ids as URLs.

- [ ] **Step 3: Implement the minimal path-based id encode/decode logic in 低端影视.py**

```python
    def _extract_site_path_id(self, href):
        full = self._build_url(href)
        matched = re.search(r"https?://[^/]+/(movie/[^?#]+?)/?$", full)
        return matched.group(1).rstrip("/") if matched else ""

    def _build_detail_request_url(self, vod_id):
        value = self._stringify(vod_id).strip().strip("/")
        return self._build_url(value + "/") if value else ""

    def _parse_cards(self, html):
        ...
            vod_id = self._extract_site_path_id(href)
        ...

    def detailContent(self, ids):
        ...
            vod_id = self._stringify(raw_id).strip().strip("/")
            request_url = self._build_detail_request_url(vod_id)
            if not request_url:
                continue
            vod = self._parse_detail_page(self._request_html(request_url), vod_id)
        ...
```

- [ ] **Step 4: Run the targeted tests to verify they pass**

Run: `python -m unittest tests.test_低端影视.TestDDYSSpider.test_parse_cards_returns_compact_site_path_ids tests.test_低端影视.TestDDYSSpider.test_detail_content_decodes_compact_site_path_id tests.test_低端影视.TestDDYSSpider.test_search_content_returns_compact_site_path_ids -v`

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add 低端影视.py tests/test_低端影视.py
git commit -m "fix: compress ddys detail ids"
```

### Task 2: Lock Failing Tests And Fix 短路径 IDs In 滴答影视

**Files:**
- Modify: `tests/test_滴答影视.py`
- Modify: `滴答影视.py`

- [ ] **Step 1: Write the failing tests for short detail ids in list/search/detail flows**

```python
    def test_parse_cards_returns_compact_site_path_ids(self):
        html = """
        <div class="myui-vodlist__box">
          <div class="title"><a href="/detail/888.html" title="示例影片"></a></div>
          <a class="lazyload" data-original="/cover.jpg"></a>
        </div>
        """
        cards = self.spider._parse_cards(html)
        self.assertEqual(cards[0]["vod_id"], "detail/888")

    @patch.object(Spider, "_request_html")
    def test_detail_content_decodes_compact_site_path_id(self, mock_request_html):
        mock_request_html.return_value = '<div class="myui-content__detail"><h1 class="title">详情标题</h1></div>'
        self.spider.detailContent(["detail/111"])
        self.assertEqual(mock_request_html.call_args.args[0], "https://www.didahd.pro/detail/111.html")

    @patch.object(Spider, "_request_html")
    def test_search_content_returns_compact_site_path_ids(self, mock_request_html):
        mock_request_html.return_value = """
        <div class="myui-vodlist__box">
          <div class="title"><a href="/detail/321.html" title="搜索影片"></a></div>
          <a class="lazyload" data-original="/search.jpg"></a>
        </div>
        """
        result = self.spider.searchContent("搜索影片", False, "1")
        self.assertEqual(result["list"][0]["vod_id"], "detail/321")
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run: `python -m unittest tests.test_滴答影视.TestDidaSpider.test_parse_cards_returns_compact_site_path_ids tests.test_滴答影视.TestDidaSpider.test_detail_content_decodes_compact_site_path_id tests.test_滴答影视.TestDidaSpider.test_search_content_returns_compact_site_path_ids -v`

Expected: `FAIL` because `滴答影视.py` currently returns full detail URLs and reads detail ids as URLs.

- [ ] **Step 3: Implement the minimal path-based id encode/decode logic in 滴答影视.py**

```python
    def _extract_site_path_id(self, href):
        matched = re.search(r"/(detail/[^/?#]+)\.html", self._build_url(href))
        return matched.group(1) if matched else ""

    def _build_detail_request_url(self, vod_id):
        value = self._stringify(vod_id).strip().strip("/")
        return self._build_url(f"/{value}.html") if value else ""

    def _parse_cards(self, html):
        ...
            vod_id = self._extract_site_path_id(href)
        ...

    def detailContent(self, ids):
        ...
            vod_id = self._stringify(raw).strip().strip("/")
            if not vod_id:
                continue
            result["list"].append(self._parse_detail_page(self._request_html(self._build_detail_request_url(vod_id)), vod_id))
```

- [ ] **Step 4: Run the targeted tests to verify they pass**

Run: `python -m unittest tests.test_滴答影视.TestDidaSpider.test_parse_cards_returns_compact_site_path_ids tests.test_滴答影视.TestDidaSpider.test_detail_content_decodes_compact_site_path_id tests.test_滴答影视.TestDidaSpider.test_search_content_returns_compact_site_path_ids -v`

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add 滴答影视.py tests/test_滴答影视.py
git commit -m "fix: compress dida detail ids"
```

### Task 3: Verify No Regression In Already-Compliant Spiders

**Files:**
- Reference only: `libvio.py`
- Reference only: `剧迷.py`
- Reference only: `youknow.py`
- Reference only: `橘子TV.py`
- Reference only: `乌云影视.py`
- Reference only: `剧圈圈.py`

- [ ] **Step 1: Re-run focused test suites for the modified spiders**

Run: `python -m unittest tests.test_低端影视 tests.test_滴答影视 -v`

Expected: all tests in the two modified files pass.

- [ ] **Step 2: Re-run sanity checks for already-compliant spiders without modifying them**

Run: `python -m unittest tests.test_libvio tests.test_youknow tests.test_剧迷 -v`

Expected: their existing compact-id-related behavior remains green. If unrelated known failures appear, note them and do not change those spiders in this task.

- [ ] **Step 3: Review the final diff to ensure only actual offenders changed**

Run: `git diff -- 低端影视.py 滴答影视.py tests/test_低端影视.py tests/test_滴答影视.py`

Expected: diff only touches the two offending spiders and their tests.

- [ ] **Step 4: Re-run the modified-spider tests one final time**

Run: `python -m unittest tests.test_低端影视 tests.test_滴答影视 -v`

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add 低端影视.py 滴答影视.py tests/test_低端影视.py tests/test_滴答影视.py
git commit -m "fix: normalize short ids for audited spiders"
```
