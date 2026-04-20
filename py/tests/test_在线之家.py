import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE = SourceFileLoader("zxzj_spider", str(ROOT / "在线之家.py")).load_module()
Spider = MODULE.Spider


class TestZXZJSpider(unittest.TestCase):
    def setUp(self):
        Spider._instance = None
        self.spider = Spider()
        self.spider.init()

    def test_home_content_exposes_expected_classes_and_filter_keys(self):
        content = self.spider.homeContent(False)
        self.assertEqual(
            [item["type_id"] for item in content["class"]],
            ["1", "2", "3", "4", "5", "6"],
        )
        self.assertEqual(
            [item["key"] for item in content["filters"]["1"]],
            ["class", "area", "year", "by"],
        )

    def test_home_video_content_returns_empty_list(self):
        self.assertEqual(self.spider.homeVideoContent(), {"list": []})

    def test_build_category_url_applies_default_and_selected_filters(self):
        url = self.spider._build_category_url("1", "2", {"area": "欧美", "by": "hits", "year": "2025"})
        self.assertEqual(url, "https://www.zxzjhd.com/vodshow/1-欧美-hits------2---2025.html")

    def test_build_category_url_for_first_page_keeps_page_1_segment(self):
        url = self.spider._build_category_url("2", "1", {})
        self.assertEqual(url, "https://www.zxzjhd.com/vodshow/2--------1---.html")


if __name__ == "__main__":
    unittest.main()
