import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE = SourceFileLoader("czzy_spider", str(ROOT / "厂长资源.py")).load_module()
Spider = MODULE.Spider


class TestCZZYSpider(unittest.TestCase):
    def setUp(self):
        self.spider = Spider()
        self.spider.init()

    def test_home_content_exposes_expected_categories(self):
        content = self.spider.homeContent(False)
        class_ids = [item["type_id"] for item in content["class"]]
        self.assertEqual(class_ids[:3], ["movie", "tv", "anime"])
        self.assertIn("cn_drama", class_ids)

    def test_parse_media_cards_extracts_basic_fields(self):
        html = """
        <ul class="mi_ne_kd">
          <li>
            <a href="/movie/abc.html" title="链接标题">
              <img data-original="https://img.example/cover.jpg" alt="测试影片" />
            </a>
            <span class="jidi">更新至10集</span>
          </li>
        </ul>
        """
        cards = self.spider._parse_media_cards(html, "https://www.cz01.org")
        self.assertEqual(
            cards,
            [
                {
                    "vod_id": "/movie/abc.html",
                    "vod_name": "测试影片",
                    "vod_pic": "https://img.example/cover.jpg",
                    "vod_remarks": "更新至10集",
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
