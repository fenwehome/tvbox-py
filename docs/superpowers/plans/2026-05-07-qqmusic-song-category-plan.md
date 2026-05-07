# QQ音乐歌曲分类 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 QQ 音乐 spider 新增“歌曲”固定分类和 `type` 筛选，支持按地区分页浏览新歌首发列表，并复用现有 `song:*` 详情链路。

**Architecture:** 保持现有单文件 spider 模式，在 `py/QQ音乐.py` 中扩展固定分类顺序、首页筛选输出和 `categoryContent("song", ...)` 列表分支，不改动现有单曲详情和播放器协议。测试集中放在 `py/tests/test_QQ音乐.py`，沿用 `unittest + patch` 风格，通过 mock `/api/song` 返回覆盖分类顺序、筛选结构、默认类型、页码透传、封面拼装、备注映射和容错降级。

**Tech Stack:** Python 3, `unittest`, `unittest.mock`, `importlib.machinery.SourceFileLoader`

---

## File Structure

- Modify: `py/QQ音乐.py`
  责任：调整固定分类顺序，新增 `song` 筛选配置、歌曲列表归一化助手和 `categoryContent("song", ...)` 分支。
- Modify: `py/tests/test_QQ音乐.py`
  责任：新增歌曲分类 fixtures 和列表测试，不改动现有歌曲详情、歌手、专辑、歌单测试语义。
- Reference: `docs/superpowers/specs/2026-05-07-qqmusic-song-category-design.md`

### Task 1: Add Song Category Entry And Home Filters

**Files:**
- Modify: `py/tests/test_QQ音乐.py:500-560`
- Modify: `py/QQ音乐.py:22-38`
- Modify: `py/QQ音乐.py:60-61`
- Test: `py/tests/test_QQ音乐.py`

- [ ] **Step 1: Write the failing test**

Replace the existing home-content test body with:

```python
def test_home_content_returns_song_top_singer_album_and_playlist_classes(self):
    result = self.spider.homeContent(False)
    self.assertEqual(
        result["class"],
        [
            {"type_id": "song", "type_name": "歌曲"},
            {"type_id": "top", "type_name": "排行榜"},
            {"type_id": "singer", "type_name": "歌手"},
            {"type_id": "album", "type_name": "专辑"},
            {"type_id": "playlist", "type_name": "歌单"},
        ],
    )
    self.assertEqual(
        result["filters"],
        {
            "song": [
                {
                    "key": "type",
                    "name": "地区",
                    "init": "5",
                    "value": [
                        {"n": "最新", "v": "5"},
                        {"n": "内地", "v": "1"},
                        {"n": "港台", "v": "6"},
                        {"n": "欧美", "v": "2"},
                        {"n": "韩国", "v": "4"},
                        {"n": "日本", "v": "3"},
                    ],
                }
            ],
            "album": [
                {
                    "key": "area",
                    "name": "地区",
                    "init": "1",
                    "value": [
                        {"n": "内地", "v": "1"},
                        {"n": "港台", "v": "2"},
                        {"n": "欧美", "v": "3"},
                        {"n": "韩国", "v": "4"},
                        {"n": "日本", "v": "5"},
                    ],
                }
            ],
        },
    )
    self.assertEqual(result["list"], [])
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python - <<'PY'
import sys, types, unittest
from importlib.machinery import SourceFileLoader

requests = types.ModuleType("requests")
requests.get = lambda *args, **kwargs: None
requests.post = lambda *args, **kwargs: None
sys.modules["requests"] = requests

module = SourceFileLoader("test_qqmusic", "py/tests/test_QQ音乐.py").load_module()
case = module.TestQQMusicSpider
suite = unittest.TestSuite([
    unittest.defaultTestLoader.loadTestsFromName(
        "test_home_content_returns_song_top_singer_album_and_playlist_classes",
        case,
    )
])
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
PY
```

Expected: FAIL because `homeContent()` still starts with `top`, and `filters` does not yet include `song`.

- [ ] **Step 3: Write minimal implementation**

Update the fixed classes and filters in `Spider.__init__`:

```python
self.classes = [
    {"type_id": "song", "type_name": "歌曲"},
    {"type_id": "top", "type_name": "排行榜"},
    {"type_id": "singer", "type_name": "歌手"},
    {"type_id": "album", "type_name": "专辑"},
    {"type_id": "playlist", "type_name": "歌单"},
]
self.filters = {
    "song": [
        {
            "key": "type",
            "name": "地区",
            "init": "5",
            "value": [
                {"n": "最新", "v": "5"},
                {"n": "内地", "v": "1"},
                {"n": "港台", "v": "6"},
                {"n": "欧美", "v": "2"},
                {"n": "韩国", "v": "4"},
                {"n": "日本", "v": "3"},
            ],
        }
    ],
    "album": [
        {
            "key": "area",
            "name": "地区",
            "init": "1",
            "value": [
                {"n": "内地", "v": "1"},
                {"n": "港台", "v": "2"},
                {"n": "欧美", "v": "3"},
                {"n": "韩国", "v": "4"},
                {"n": "日本", "v": "5"},
            ],
        }
    ],
}
```

Keep:

```python
def homeContent(self, filter):
    return {"class": list(self.classes), "filters": self.filters, "list": []}
```

- [ ] **Step 4: Run test to verify it passes**

Run the same command from Step 2.

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -f py/QQ音乐.py py/tests/test_QQ音乐.py
git commit -m "feat: add qqmusic song category filters"
```

### Task 2: Add Song Category List Mapping

**Files:**
- Modify: `py/tests/test_QQ音乐.py:430-760`
- Modify: `py/QQ音乐.py:60-180`
- Modify: `py/QQ音乐.py:360-440`
- Test: `py/tests/test_QQ音乐.py`

- [ ] **Step 1: Write the failing test**

Add a fixture near the category fixtures:

```python
SONG_CATEGORY_JSON = {
    "code": 0,
    "data": {
        "lan": "最新",
        "songlist": [
            {
                "mid": "001BSw5S2HYiTG",
                "name": "パッパパラダイス",
                "title": "パッパパラダイス (PAPPAPARADISE)",
                "time_public": "2026-05-06",
                "singer": [
                    {
                        "id": 5087,
                        "mid": "002JptyK0sIn6P",
                        "name": "宇多田光",
                    }
                ],
            },
            {
                "mid": "002songTwo",
                "name": "测试歌",
                "title": "",
                "time_public": "",
                "singer": [
                    {
                        "id": 1,
                        "mid": "001SingerA",
                        "name": "歌手甲",
                    },
                    {
                        "id": 2,
                        "mid": "001SingerB",
                        "name": "歌手乙",
                    },
                ],
            },
        ],
    },
}
```

Add these tests:

```python
@patch.object(Spider, "_get_json")
def test_category_content_maps_song_cards_with_default_type(self, mock_get_json):
    mock_get_json.return_value = SONG_CATEGORY_JSON

    result = self.spider.categoryContent("song", "1", False, {})

    self.assertEqual(result["page"], 1)
    self.assertEqual(result["total"], 2)
    self.assertEqual(
        result["list"],
        [
            {
                "vod_id": "song:001BSw5S2HYiTG",
                "vod_name": "パッパパラダイス (PAPPAPARADISE)",
                "vod_pic": "https://music.har01d.cn/api/song/cover/content?mid=001BSw5S2HYiTG&size=300",
                "vod_remarks": "宇多田光  2026-05-06",
            },
            {
                "vod_id": "song:002songTwo",
                "vod_name": "测试歌",
                "vod_pic": "https://music.har01d.cn/api/song/cover/content?mid=002songTwo&size=300",
                "vod_remarks": "歌手甲/歌手乙",
            },
        ],
    )
    called_url = mock_get_json.call_args[0][0]
    self.assertIn("/api/song?type=5&page=1", called_url)


@patch.object(Spider, "_get_json")
def test_category_content_song_uses_requested_page_and_type(self, mock_get_json):
    mock_get_json.return_value = SONG_CATEGORY_JSON

    self.spider.categoryContent("song", "2", False, {"type": "3"})

    called_url = mock_get_json.call_args[0][0]
    self.assertIn("/api/song?type=3&page=2", called_url)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python - <<'PY'
import sys, types, unittest
from importlib.machinery import SourceFileLoader

requests = types.ModuleType("requests")
requests.get = lambda *args, **kwargs: None
requests.post = lambda *args, **kwargs: None
sys.modules["requests"] = requests

module = SourceFileLoader("test_qqmusic", "py/tests/test_QQ音乐.py").load_module()
case = module.TestQQMusicSpider
names = [
    "test_category_content_maps_song_cards_with_default_type",
    "test_category_content_song_uses_requested_page_and_type",
]
suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(name, case) for name in names)
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
PY
```

Expected: FAIL because there is no `song` category branch yet.

- [ ] **Step 3: Write minimal implementation**

Add helpers:

```python
def _song_category_type(self, extend):
    if not isinstance(extend, dict):
        return "5"
    category_type = str(extend.get("type", "5") or "5").strip()
    return category_type if category_type in {"5", "1", "6", "2", "4", "3"} else "5"


def _song_category_cover(self, mid):
    token = str(mid or "").strip()
    if not token:
        return ""
    return "%s/api/song/cover/content?mid=%s&size=300" % (self.base_url, token)


def _song_category_card(self, song):
    mid = str(song.get("mid", "")).strip()
    title = self._song_title(song)
    if not mid or not title:
        return None
    singer_name = self._join_singers(song.get("singer", []))
    publish_date = song.get("time_public", "") or ""
    if singer_name and publish_date:
        remarks = "%s  %s" % (singer_name, publish_date)
    else:
        remarks = singer_name or publish_date or ""
    return {
        "vod_id": "song:%s" % mid,
        "vod_name": title,
        "vod_pic": self._song_category_cover(mid),
        "vod_remarks": remarks,
    }
```

Add the category branch before `top`:

```python
if tid == "song":
    page = str(pg or "1")
    category_type = self._song_category_type(extend)
    data = self._get_json(self._api_url("/api/song", type=category_type, page=page))
    items = []
    for item in data.get("data", {}).get("songlist", []):
        card = self._song_category_card(item)
        if not card:
            continue
        items.append(card)
    return {"page": int(page), "limit": len(items), "total": len(items), "list": items}
```

- [ ] **Step 4: Run test to verify it passes**

Run the same command from Step 2.

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -f py/QQ音乐.py py/tests/test_QQ音乐.py
git commit -m "feat: add qqmusic song category listing"
```

### Task 3: Harden Song Category Fallbacks And Run Full Verification

**Files:**
- Modify: `py/tests/test_QQ音乐.py:620-820`
- Modify: `py/QQ音乐.py:60-180`
- Modify: `py/QQ音乐.py:360-440`
- Test: `py/tests/test_QQ音乐.py`

- [ ] **Step 1: Write the failing test**

Add these tests:

```python
@patch.object(Spider, "_get_json")
def test_category_content_song_invalid_type_falls_back_to_5(self, mock_get_json):
    mock_get_json.return_value = {"code": 0, "data": {"songlist": []}}

    self.spider.categoryContent("song", "1", False, {"type": "99"})

    called_url = mock_get_json.call_args[0][0]
    self.assertIn("/api/song?type=5&page=1", called_url)


@patch.object(Spider, "_get_json")
def test_category_content_song_skips_items_without_mid_or_title(self, mock_get_json):
    mock_get_json.return_value = {
        "code": 0,
        "data": {
            "songlist": [
                {"mid": "", "title": "坏歌", "name": "坏歌", "time_public": "2026-05-06", "singer": [{"name": "歌手"}]},
                {"mid": "001bad", "title": "", "name": "", "time_public": "2026-05-06", "singer": [{"name": "歌手"}]},
                {"mid": "001ok", "title": "", "name": "正常歌", "time_public": "", "singer": []},
            ]
        },
    }

    result = self.spider.categoryContent("song", "1", False, {})

    self.assertEqual(
        result["list"],
        [
            {
                "vod_id": "song:001ok",
                "vod_name": "正常歌",
                "vod_pic": "https://music.har01d.cn/api/song/cover/content?mid=001ok&size=300",
                "vod_remarks": "",
            }
        ],
    )


@patch.object(Spider, "_get_json")
def test_category_content_song_returns_empty_for_request_failure(self, mock_get_json):
    mock_get_json.return_value = {}

    self.assertEqual(
        self.spider.categoryContent("song", "1", False, {}),
        {"page": 1, "limit": 0, "total": 0, "list": []},
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python - <<'PY'
import sys, types, unittest
from importlib.machinery import SourceFileLoader

requests = types.ModuleType("requests")
requests.get = lambda *args, **kwargs: None
requests.post = lambda *args, **kwargs: None
sys.modules["requests"] = requests

module = SourceFileLoader("test_qqmusic", "py/tests/test_QQ音乐.py").load_module()
case = module.TestQQMusicSpider
names = [
    "test_category_content_song_invalid_type_falls_back_to_5",
    "test_category_content_song_skips_items_without_mid_or_title",
    "test_category_content_song_returns_empty_for_request_failure",
]
suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(name, case) for name in names)
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
PY
```

Expected: FAIL if invalid `type`, bad-song skipping, or request-failure shape is not handled correctly.

- [ ] **Step 3: Write minimal implementation**

Keep the guards in the helpers and list branch:

```python
def _song_category_type(self, extend):
    if not isinstance(extend, dict):
        return "5"
    category_type = str(extend.get("type", "5") or "5").strip()
    return category_type if category_type in {"5", "1", "6", "2", "4", "3"} else "5"
```

```python
def _song_category_card(self, song):
    mid = str(song.get("mid", "")).strip()
    title = self._song_title(song)
    if not mid or not title:
        return None
    singer_name = self._join_singers(song.get("singer", []))
    publish_date = song.get("time_public", "") or ""
    if singer_name and publish_date:
        remarks = "%s  %s" % (singer_name, publish_date)
    else:
        remarks = singer_name or publish_date or ""
    return {
        "vod_id": "song:%s" % mid,
        "vod_name": title,
        "vod_pic": self._song_category_cover(mid),
        "vod_remarks": remarks,
    }
```

```python
if tid == "song":
    page = str(pg or "1")
    category_type = self._song_category_type(extend)
    data = self._get_json(self._api_url("/api/song", type=category_type, page=page))
    items = []
    for item in data.get("data", {}).get("songlist", []):
        card = self._song_category_card(item)
        if not card:
            continue
        items.append(card)
    return {"page": int(page), "limit": len(items), "total": len(items), "list": items}
```

- [ ] **Step 4: Run full verification**

Run the full QQ 音乐 suite:

```bash
python - <<'PY'
import sys, types, unittest
from importlib.machinery import SourceFileLoader

requests = types.ModuleType("requests")
requests.get = lambda *args, **kwargs: None
requests.post = lambda *args, **kwargs: None
sys.modules["requests"] = requests

module = SourceFileLoader("test_qqmusic", "py/tests/test_QQ音乐.py").load_module()
suite = unittest.defaultTestLoader.loadTestsFromModule(module)
result = unittest.TextTestRunner(verbosity=1).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
PY
```

Expected: `OK`

Then run syntax verification:

```bash
python -m py_compile py/QQ音乐.py py/tests/test_QQ音乐.py
```

Expected: no output

- [ ] **Step 5: Commit**

```bash
git add -f py/QQ音乐.py py/tests/test_QQ音乐.py
git commit -m "feat: add qqmusic song category browsing"
```

## Self-Review

- Spec coverage:
  - 固定分类顺序更新：Task 1
  - `filters["song"]` 输出：Task 1
  - `/api/song?type=<type>&page=<pg>` 列表：Task 2
  - 封面拼装、备注映射：Task 2
  - 非法 `type`、坏数据和请求失败：Task 3
- Placeholder scan:
  - 无 `TODO`、`TBD` 或 “similar to above” 占位描述
- Type consistency:
  - 统一使用 `song` 分类、`type` 筛选键、`song:<mid>` 详情入口和 `time_public` 发行日期字段
