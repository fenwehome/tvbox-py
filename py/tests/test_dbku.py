import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE = SourceFileLoader("dbku_spider", str(ROOT / "独播库.py")).load_module()
Spider = MODULE.Spider


class TestDBKUSpider(unittest.TestCase):
    def setUp(self):
        self.spider = Spider()
        self.spider.init()

    def test_home_content_exposes_expected_categories(self):
        content = self.spider.homeContent(False)
        class_ids = [item["type_id"] for item in content["class"]]
        self.assertEqual(class_ids, ["index", "movie", "variety", "anime", "hk", "luju"])

    def test_parse_list_cards_extracts_detail_url_title_cover_and_description(self):
        html = """
        <div class="myui-vodlist__box">
          <a class="thumb" href="/voddetail/123.html" title="示例影片" data-original="https://img.example/dbku.jpg"></a>
          <span class="pic-text">更新至10集</span>
        </div>
        """
        cards = self.spider._parse_list_cards(html)
        self.assertEqual(
            cards,
            [
                {
                    "vod_id": "https://www.dbku.tv/voddetail/123.html",
                    "vod_name": "示例影片",
                    "vod_pic": "https://img.example/dbku.jpg",
                    "vod_remarks": "更新至10集",
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
