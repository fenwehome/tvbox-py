# QQ音乐专辑分类 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 QQ 音乐 spider 新增“专辑”固定分类，支持按地区分页浏览专辑列表，并复用现有 `album:*` 详情链路。

**Architecture:** 保持现有单文件 spider 模式，在 `py/QQ音乐.py` 中新增专辑分类列表归一化助手和 `categoryContent("album", ...)` 分支，不改动现有搜索、详情和播放器协议。测试集中放在 `py/tests/test_QQ音乐.py`，沿用 `unittest + patch` 风格，通过 mock 专辑列表 JSON 覆盖分类顺序、默认筛选、页码与地区透传、封面回退和容错降级。

**Tech Stack:** Python 3, `unittest`, `unittest.mock`, `importlib.machinery.SourceFileLoader`

---

## File Structure

- Modify: `py/QQ音乐.py`
  责任：调整固定分类顺序，新增专辑列表归一化助手，并在 `categoryContent()` 中实现 `album` 列表分支。
- Modify: `py/tests/test_QQ音乐.py`
  责任：新增专辑分类列表 fixtures 和分类浏览测试，不改动现有歌曲、歌手、歌单、专辑详情测试。
- Reference: `docs/superpowers/specs/2026-05-07-qqmusic-album-category-design.md`

### Task 1: Add Album Category Entry And Default List Mapping

**Files:**
- Modify: `py/tests/test_QQ音乐.py:471-661`
- Modify: `py/QQ音乐.py:22-26`
- Modify: `py/QQ音乐.py:184-211`
- Modify: `py/QQ音乐.py:360-388`
- Test: `py/tests/test_QQ音乐.py`

- [ ] **Step 1: Write the failing test**

Add a new fixture near the other category fixtures:

```python
ALBUM_CATEGORY_JSON = {
    "code": 0,
    "data": {
        "albums": [
            {
                "id": 89351731,
                "mid": "003QAXMO4T46al",
                "name": "余额不足",
                "release_time": "2026-04-17",
                "singers": [
                    {
                        "id": 2622827,
                        "mid": "0013etbl2nYw4j",
                        "name": "张语哝",
                    }
                ],
                "pic": "http://y.gtimg.cn/music/photo_new/T002R180x180M000003QAXMO4T46al_1.jpg",
                "photo": {
                    "pic_mid": "003QAXMO4T46al_1",
                },
            }
        ]
    },
}
```

Replace the existing home-content test and add a new album-category test:

```python
def test_home_content_returns_top_singer_album_and_playlist_classes(self):
    result = self.spider.homeContent(False)
    self.assertEqual(
        result["class"],
        [
            {"type_id": "top", "type_name": "排行榜"},
            {"type_id": "singer", "type_name": "歌手"},
            {"type_id": "album", "type_name": "专辑"},
            {"type_id": "playlist", "type_name": "歌单"},
        ],
    )
    self.assertEqual(result["list"], [])


@patch.object(Spider, "_get_json")
def test_category_content_maps_album_cards_with_default_area(self, mock_get_json):
    mock_get_json.return_value = ALBUM_CATEGORY_JSON

    result = self.spider.categoryContent("album", "1", False, {})

    self.assertEqual(result["page"], 1)
    self.assertEqual(result["total"], 1)
    self.assertEqual(
        result["list"],
        [
            {
                "vod_id": "album:003QAXMO4T46al",
                "vod_name": "余额不足",
                "vod_pic": "http://y.gtimg.cn/music/photo_new/T002R180x180M000003QAXMO4T46al_1.jpg",
                "vod_remarks": "张语哝  2026-04-17",
            }
        ],
    )
    called_url = mock_get_json.call_args[0][0]
    self.assertIn("/api/album?area=1&page=1", called_url)
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
    "test_home_content_returns_top_singer_album_and_playlist_classes",
    "test_category_content_maps_album_cards_with_default_area",
]
suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(name, case) for name in names)
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
PY
```

Expected: FAIL because `homeContent()` still returns only `top/singer/playlist`, and `categoryContent()` has no `album` branch.

- [ ] **Step 3: Write minimal implementation**

Update the fixed classes and add the minimal album list helper + category branch:

```python
self.classes = [
    {"type_id": "top", "type_name": "排行榜"},
    {"type_id": "singer", "type_name": "歌手"},
    {"type_id": "album", "type_name": "专辑"},
    {"type_id": "playlist", "type_name": "歌单"},
]
```

```python
def _album_category_area(self, extend):
    if not isinstance(extend, dict):
        return "1"
    area = str(extend.get("area", "1") or "1").strip()
    return area if area in {"1", "2", "3", "4", "5"} else "1"


def _album_category_cover(self, album):
    return album.get("pic", "") or album.get("cover", "") or ""


def _album_category_card(self, album):
    album_mid = str(album.get("mid", "")).strip()
    album_name = str(album.get("name", "")).strip()
    if not album_mid or not album_name:
        return None
    singer_name = self._join_named_items(album.get("singers", []))
    release_time = album.get("release_time", "") or ""
    if singer_name and release_time:
        remarks = "%s  %s" % (singer_name, release_time)
    else:
        remarks = singer_name or release_time or ""
    return {
        "vod_id": "album:%s" % album_mid,
        "vod_name": album_name,
        "vod_pic": self._album_category_cover(album),
        "vod_remarks": remarks,
    }
```

```python
if tid == "album":
    page = str(pg or "1")
    area = self._album_category_area(extend)
    data = self._get_json(self._api_url("/api/album", area=area, page=page))
    items = []
    for item in data.get("data", {}).get("albums", []):
        card = self._album_category_card(item)
        if not card:
            continue
        items.append(card)
    return {"page": int(page), "limit": len(items), "total": len(items), "list": items}
```

- [ ] **Step 4: Run test to verify it passes**

Run the same command from Step 2.

Expected: PASS for both tests.

- [ ] **Step 5: Commit**

```bash
git add py/QQ音乐.py py/tests/test_QQ音乐.py
git commit -m "feat: add qqmusic album category entry"
```

### Task 2: Support Area Override And Pic-Mid Cover Fallback

**Files:**
- Modify: `py/tests/test_QQ音乐.py:471-661`
- Modify: `py/QQ音乐.py:246-350`
- Modify: `py/QQ音乐.py:360-388`
- Test: `py/tests/test_QQ音乐.py`

- [ ] **Step 1: Write the failing test**

Add a second fixture with no direct `pic`, multiple singers, and a `photo.pic_mid` fallback:

```python
ALBUM_CATEGORY_FALLBACK_JSON = {
    "code": 0,
    "data": {
        "albums": [
            {
                "id": 90000001,
                "mid": "001AlbumTwo",
                "name": "双人专辑",
                "release_time": "2026-01-01",
                "singers": [
                    {"id": 1, "mid": "001SingerA", "name": "歌手甲"},
                    {"id": 2, "mid": "001SingerB", "name": "歌手乙"},
                ],
                "pic": "",
                "photo": {
                    "pic_mid": "001AlbumTwo_1",
                },
            }
        ]
    },
}
```

Add these tests:

```python
@patch.object(Spider, "_get_json")
def test_category_content_album_uses_requested_page_and_area(self, mock_get_json):
    mock_get_json.return_value = ALBUM_CATEGORY_FALLBACK_JSON

    result = self.spider.categoryContent("album", "2", False, {"area": "3"})

    self.assertEqual(result["page"], 2)
    self.assertEqual(
        result["list"],
        [
            {
                "vod_id": "album:001AlbumTwo",
                "vod_name": "双人专辑",
                "vod_pic": "http://y.gtimg.cn/music/photo_new/T002R300x300M000001AlbumTwo_1.jpg",
                "vod_remarks": "歌手甲/歌手乙  2026-01-01",
            }
        ],
    )
    called_url = mock_get_json.call_args[0][0]
    self.assertIn("/api/album?area=3&page=2", called_url)
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
    "test_category_content_album_uses_requested_page_and_area",
]
suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(name, case) for name in names)
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
PY
```

Expected: FAIL because the current implementation ignores `photo.pic_mid` and therefore returns an empty `vod_pic`.

- [ ] **Step 3: Write minimal implementation**

Upgrade the album cover helper to fall back to `photo.pic_mid`:

```python
def _album_category_cover(self, album):
    direct = album.get("pic", "") or album.get("cover", "") or ""
    if direct:
        return direct
    photo = album.get("photo", {}) if isinstance(album.get("photo", {}), dict) else {}
    pic_mid = str(photo.get("pic_mid", "")).strip()
    if pic_mid:
        return "http://y.gtimg.cn/music/photo_new/T002R300x300M000%s.jpg" % pic_mid
    return ""
```

Keep `self._join_named_items(album.get("singers", []))` for multiple-singer remarks so the test output becomes `歌手甲/歌手乙  2026-01-01`.

- [ ] **Step 4: Run test to verify it passes**

Run the same command from Step 2.

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add py/QQ音乐.py py/tests/test_QQ音乐.py
git commit -m "feat: add qqmusic album area and cover fallback"
```

### Task 3: Harden Album Category Fallbacks And Run Full Verification

**Files:**
- Modify: `py/tests/test_QQ音乐.py:471-661`
- Modify: `py/QQ音乐.py:246-350`
- Modify: `py/QQ音乐.py:360-388`
- Test: `py/tests/test_QQ音乐.py`

- [ ] **Step 1: Write the failing test**

Add these tests:

```python
@patch.object(Spider, "_get_json")
def test_category_content_album_invalid_area_falls_back_to_1(self, mock_get_json):
    mock_get_json.return_value = {"code": 0, "data": {"albums": []}}

    self.spider.categoryContent("album", "1", False, {"area": "99"})

    called_url = mock_get_json.call_args[0][0]
    self.assertIn("/api/album?area=1&page=1", called_url)


@patch.object(Spider, "_get_json")
def test_category_content_album_skips_items_without_mid_or_name(self, mock_get_json):
    mock_get_json.return_value = {
        "code": 0,
        "data": {
            "albums": [
                {"mid": "", "name": "坏专辑", "release_time": "2026-04-17", "singers": [{"name": "歌手"}], "photo": {}},
                {"mid": "001bad", "name": "", "release_time": "2026-04-17", "singers": [{"name": "歌手"}], "photo": {}},
                {"mid": "001ok", "name": "正常专辑", "release_time": "", "singers": [], "photo": {}},
            ]
        },
    }

    result = self.spider.categoryContent("album", "1", False, {})

    self.assertEqual(
        result["list"],
        [
            {
                "vod_id": "album:001ok",
                "vod_name": "正常专辑",
                "vod_pic": "",
                "vod_remarks": "",
            }
        ],
    )


@patch.object(Spider, "_get_json")
def test_category_content_album_returns_empty_for_request_failure(self, mock_get_json):
    mock_get_json.return_value = {}

    self.assertEqual(
        self.spider.categoryContent("album", "1", False, {}),
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
    "test_category_content_album_invalid_area_falls_back_to_1",
    "test_category_content_album_skips_items_without_mid_or_name",
    "test_category_content_album_returns_empty_for_request_failure",
]
suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(name, case) for name in names)
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
PY
```

Expected: FAIL if any invalid items are still emitted or if the request-failure branch does not preserve the empty-result shape.

- [ ] **Step 3: Write minimal implementation**

Make sure the helper and branch keep these guards:

```python
def _album_category_area(self, extend):
    if not isinstance(extend, dict):
        return "1"
    area = str(extend.get("area", "1") or "1").strip()
    return area if area in {"1", "2", "3", "4", "5"} else "1"
```

```python
def _album_category_card(self, album):
    album_mid = str(album.get("mid", "")).strip()
    album_name = str(album.get("name", "")).strip()
    if not album_mid or not album_name:
        return None
    singer_name = self._join_named_items(album.get("singers", []))
    release_time = album.get("release_time", "") or ""
    if singer_name and release_time:
        remarks = "%s  %s" % (singer_name, release_time)
    else:
        remarks = singer_name or release_time or ""
    return {
        "vod_id": "album:%s" % album_mid,
        "vod_name": album_name,
        "vod_pic": self._album_category_cover(album),
        "vod_remarks": remarks,
    }
```

```python
if tid == "album":
    page = str(pg or "1")
    area = self._album_category_area(extend)
    data = self._get_json(self._api_url("/api/album", area=area, page=page))
    items = []
    for item in data.get("data", {}).get("albums", []):
        card = self._album_category_card(item)
        if not card:
            continue
        items.append(card)
    return {"page": int(page), "limit": len(items), "total": len(items), "list": items}
```

- [ ] **Step 4: Run full verification**

Run the focused regression suite:

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
git add py/QQ音乐.py py/tests/test_QQ音乐.py
git commit -m "feat: add qqmusic album category browsing"
```

## Self-Review

- Spec coverage:
  - 固定分类顺序更新：Task 1
  - `album` 分类入口：Task 1
  - `area` 默认值与透传：Task 1, Task 2
  - `photo.pic_mid` 封面回退：Task 2
  - 非法 `area` 回退：Task 3
  - 坏数据跳过和请求失败空列表：Task 3
- Placeholder scan:
  - 无 `TODO`、`TBD` 或 “similar to above” 占位描述
- Type consistency:
  - 统一使用 `album:<mid>`、`extend["area"]`、`release_time`、`photo.pic_mid`
