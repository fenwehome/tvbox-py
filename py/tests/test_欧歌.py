import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE = SourceFileLoader("ouge_spider", str(ROOT / "欧歌.py")).load_module()
Spider = MODULE.Spider


class TestOuGeSpider(unittest.TestCase):
    def setUp(self):
        Spider._instance = None
        self.spider = Spider()
        self.spider.init()

    def test_home_content_exposes_reference_categories(self):
        content = self.spider.homeContent(False)
        self.assertEqual(
            [(item["type_id"], item["type_name"]) for item in content["class"]],
            [
                ("1", "欧歌电影"),
                ("2", "欧哥剧集"),
                ("3", "欧歌动漫"),
                ("4", "欧歌综艺"),
                ("5", "欧歌短剧"),
                ("21", "欧歌综合"),
            ],
        )

    def test_home_video_content_returns_empty_list(self):
        self.assertEqual(self.spider.homeVideoContent(), {"list": []})

    def test_build_url_joins_relative_paths_against_host(self):
        self.assertEqual(
            self.spider._build_url("/index.php/vod/detail/id/1.html"),
            "https://woog.nxog.eu.org/index.php/vod/detail/id/1.html",
        )
        self.assertEqual(
            self.spider._build_url("https://cdn.example.com/poster.jpg"),
            "https://cdn.example.com/poster.jpg",
        )

    def test_detect_pan_type_returns_expected_type_and_label(self):
        self.assertEqual(
            self.spider._detect_pan_type("https://pan.baidu.com/s/demo"),
            ("baidu", "百度资源"),
        )
        self.assertEqual(
            self.spider._detect_pan_type("https://pan.quark.cn/s/demo"),
            ("quark", "夸克资源"),
        )
        self.assertEqual(
            self.spider._detect_pan_type("https://example.com/video"),
            ("", ""),
        )


if __name__ == "__main__":
    unittest.main()
