import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from urllib.parse import quote
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
MODULE = SourceFileLoader("shuangxing_spider", str(ROOT / "双星.py")).load_module()
Spider = MODULE.Spider


class FakeResponse:
    def __init__(self, status_code=200, text="", cookies=None):
        self.status_code = status_code
        self.text = text
        self.cookies = cookies or {}
        self.headers = {}
        self.url = ""


class TestShuangXingSpider(unittest.TestCase):
    def setUp(self):
        Spider._instance = None
        self.spider = Spider()

    def test_home_content_exposes_reference_categories(self):
        content = self.spider.homeContent(False)
        self.assertEqual(
            [(item["type_id"], item["type_name"]) for item in content["class"]],
            [
                ("ju", "国剧"),
                ("zy", "综艺"),
                ("mv", "电影"),
                ("rh", "日韩"),
                ("ym", "英美"),
                ("wj", "外剧"),
                ("dm", "动漫"),
            ],
        )

    def test_home_video_content_returns_empty_list(self):
        self.assertEqual(self.spider.homeVideoContent(), {"list": []})

    @patch.object(Spider, "fetch")
    def test_init_collects_cookie_pairs_and_headers_include_cookie(self, mock_fetch):
        mock_fetch.return_value = FakeResponse(cookies={"foo": "bar", "token": "xyz"})
        self.spider.init()
        self.assertEqual(self.spider.cookie, "foo=bar; token=xyz")
        self.assertEqual(self.spider._headers()["cookie"], "foo=bar; token=xyz")

    def test_headers_without_cookie_keep_base_headers_only(self):
        self.assertEqual(
            self.spider._headers(),
            {
                "User-Agent": Spider.UA,
                "Referer": Spider.BASE_URL,
            },
        )

    def test_detect_pan_type_returns_expected_keys(self):
        self.assertEqual(self.spider._detect_pan_type("https://pan.quark.cn/s/demo"), "quark")
        self.assertEqual(self.spider._detect_pan_type("https://www.alipan.com/s/demo"), "ali")
        self.assertEqual(self.spider._detect_pan_type("https://example.com/video"), "")

    @patch.object(Spider, "_get_html")
    def test_category_content_builds_reference_url_and_parses_cards(self, mock_get_html):
        mock_get_html.return_value = """
        <body>
          <div><div><main><div><ul>
            <li><div class="a"><a href="/post/alpha">示例国剧</a></div></li>
            <li><div class="a"><a href="/post/beta">示例综艺</a></div></li>
          </ul></div></main></div></div>
        </body>
        """
        result = self.spider.categoryContent("ju", "3", False, {})
        self.assertEqual(mock_get_html.call_args.args[0], "https://1.star2.cn/ju_3/")
        self.assertEqual(result["page"], 3)
        self.assertEqual(result["limit"], 15)
        self.assertEqual(result["total"], 32)
        self.assertEqual(
            result["list"],
            [
                {"vod_id": "/post/alpha", "vod_name": "示例国剧", "vod_pic": "", "vod_remarks": ""},
                {"vod_id": "/post/beta", "vod_name": "示例综艺", "vod_pic": "", "vod_remarks": ""},
            ],
        )

    @patch.object(Spider, "_get_html")
    def test_search_content_builds_reference_url_and_parses_results(self, mock_get_html):
        mock_get_html.return_value = """
        <body>
          <div><div><main><div><ul>
            <li><div class="a"><a href="/post/search">搜索结果</a></div></li>
          </ul></div></main></div></div>
        </body>
        """
        result = self.spider.searchContent("繁花", False, "2")
        self.assertEqual(
            mock_get_html.call_args.args[0],
            f"https://1.star2.cn/search/?keyword={quote('繁花')}&page=2",
        )
        self.assertEqual(result["page"], 2)
        self.assertEqual(
            result["list"],
            [{"vod_id": "/post/search", "vod_name": "搜索结果", "vod_pic": "", "vod_remarks": ""}],
        )

    def test_search_content_short_circuits_blank_keyword(self):
        self.assertEqual(self.spider.searchContent("", False, "1"), {"page": 1, "total": 0, "list": []})

    @patch.object(Spider, "_get_html")
    def test_detail_content_extracts_title_and_sorted_deduplicated_pan_lines(self, mock_get_html):
        mock_get_html.return_value = """
        <body>
          <div>
            <div class="s20erx erx-m-bot erx-content">
              <main><article><h1>双星示例</h1></article></main>
            </div>
          </div>
          <div id="maximg">
            <div class="dlipp-cont-wp"><div><div class="dlipp-cont-bd">
              <a href="https://pan.baidu.com/s/b-demo"></a>
              <a href="https://pan.quark.cn/s/q-demo"></a>
              <a href="https://pan.baidu.com/s/b-demo"></a>
              <a href="https://example.com/ignored"></a>
            </div></div></div>
          </div>
        </body>
        """
        result = self.spider.detailContent(["/post/demo"])
        self.assertEqual(mock_get_html.call_args.args[0], "https://1.star2.cn/post/demo")
        self.assertEqual(
            result,
            {
                "list": [
                    {
                        "vod_id": "/post/demo",
                        "vod_name": "双星示例",
                        "vod_pic": "",
                        "vod_remarks": "",
                        "vod_content": "",
                        "vod_director": "",
                        "vod_actor": "",
                        "vod_play_from": "quark$$$baidu",
                        "vod_play_url": "夸克资源$https://pan.quark.cn/s/q-demo$$$百度资源$https://pan.baidu.com/s/b-demo",
                    }
                ]
            },
        )

    @patch.object(Spider, "_get_html")
    def test_detail_content_returns_empty_list_for_blank_html(self, mock_get_html):
        mock_get_html.return_value = ""
        self.assertEqual(self.spider.detailContent(["/post/missing"]), {"list": []})

    def test_player_content_passthroughs_supported_pan_links(self):
        self.assertEqual(
            self.spider.playerContent("quark", "https://pan.quark.cn/s/demo", {}),
            {"parse": 0, "playUrl": "", "url": "https://pan.quark.cn/s/demo"},
        )

    def test_player_content_rejects_unknown_links(self):
        self.assertEqual(
            self.spider.playerContent("site", "https://example.com/video", {}),
            {"parse": 0, "playUrl": "", "url": ""},
        )


if __name__ == "__main__":
    unittest.main()
