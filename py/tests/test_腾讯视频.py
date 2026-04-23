import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
MODULE = SourceFileLoader("tengxun_spider", str(ROOT / "腾讯视频.py")).load_module()
Spider = MODULE.Spider


HOME_HTML = """
<div class="list_item">
  <a data-float="/x/cover/mzc00200abc1111.html"><img alt="海底小纵队" src="https://img.test/a.jpg"></a>
  <a>更新至10集</a>
</div>
<div class="list_item">
  <a data-float="/x/cover/mzc00200abc2222.html"><img alt="熊出没" src="https://img.test/b.jpg"></a>
  <a>全52集</a>
</div>
"""


class TestTencentSpider(unittest.TestCase):
    def setUp(self):
        Spider._instance = None
        self.spider = Spider()
        self.spider.init()

    def test_parse_list_items_extracts_cards(self):
        cards = self.spider._parse_list_items(HOME_HTML, with_channel=False)
        self.assertEqual(
            cards,
            [
                {
                    "vod_id": "/x/cover/mzc00200abc1111.html",
                    "vod_name": "海底小纵队",
                    "vod_pic": "https://img.test/a.jpg",
                    "vod_remarks": "更新至10集",
                },
                {
                    "vod_id": "/x/cover/mzc00200abc2222.html",
                    "vod_name": "熊出没",
                    "vod_pic": "https://img.test/b.jpg",
                    "vod_remarks": "全52集",
                },
            ],
        )

    @patch.object(Spider, "fetch")
    def test_home_content_returns_fixed_classes_and_top_20_cards(self, mock_fetch):
        mock_fetch.return_value = SimpleNamespace(text=HOME_HTML)
        result = self.spider.homeContent(False)
        self.assertEqual(
            [item["type_id"] for item in result["class"]],
            ["choice", "movie", "tv", "variety", "cartoon", "child", "doco"],
        )
        self.assertEqual(result["list"][0]["vod_name"], "海底小纵队")
        self.assertNotIn("filters", result)

    def test_player_content_passthroughs_raw_url(self):
        result = self.spider.playerContent("腾讯视频", "https://v.qq.com/x/cover/demo.html", {})
        self.assertEqual(
            result,
            {
                "parse": 1,
                "jx": 1,
                "url": "https://v.qq.com/x/cover/demo.html",
                "header": {"User-Agent": "PC_UA"},
            },
        )


if __name__ == "__main__":
    unittest.main()
