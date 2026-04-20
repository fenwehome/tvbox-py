import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE = SourceFileLoader("letu_spider", str(ROOT / "乐兔.py")).load_module()
Spider = MODULE.Spider


class TestLeTuSpider(unittest.TestCase):
    def setUp(self):
        Spider._instance = None
        self.spider = Spider()
        self.spider.init()

    def test_home_content_exposes_expected_categories(self):
        content = self.spider.homeContent(False)
        self.assertEqual(
            [item["type_id"] for item in content["class"]],
            ["1", "2", "3", "4", "5"],
        )

    def test_home_video_content_returns_empty_list(self):
        self.assertEqual(self.spider.homeVideoContent(), {"list": []})

    def test_encode_and_decode_detail_and_play_ids(self):
        self.assertEqual(self.spider._encode_vod_id("/detail/demo.html"), "detail/demo")
        self.assertEqual(self.spider._decode_vod_id("detail/demo"), "https://www.letu.me/detail/demo.html")
        self.assertEqual(self.spider._encode_play_id("/play/123-1-1.html"), "play/123-1-1")
        self.assertEqual(self.spider._decode_play_id("play/123-1-1"), "https://www.letu.me/play/123-1-1.html")


if __name__ == "__main__":
    unittest.main()
