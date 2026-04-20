import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
MODULE = SourceFileLoader("rrdy_spider", str(ROOT / "人人电影.py")).load_module()
Spider = MODULE.Spider


class TestRenRenDianYingSpider(unittest.TestCase):
    def setUp(self):
        Spider._instance = None
        self.spider = Spider()
        self.spider.init()

    def test_home_content_exposes_reference_categories(self):
        content = self.spider.homeContent(False)
        self.assertEqual(
            [(item["type_id"], item["type_name"]) for item in content["class"]],
            [
                ("movie/list_2", "电影"),
                ("dianshiju/list_6", "电视剧"),
                ("dongman/list_13", "动漫"),
                ("zongyi/list_10", "老电影"),
            ],
        )

    def test_home_video_content_returns_empty_list(self):
        self.assertEqual(self.spider.homeVideoContent(), {"list": []})

    def test_build_url_and_pan_detection_helpers(self):
        self.assertEqual(self.spider._build_url("/movie/1.html"), "https://www.rrdynb.com/movie/1.html")
        self.assertEqual(
            self.spider._build_url("https://pan.baidu.com/s/demo"),
            "https://pan.baidu.com/s/demo",
        )
        self.assertTrue(self.spider._is_supported_pan_url("https://pan.baidu.com/s/demo"))
        self.assertTrue(self.spider._is_supported_pan_url("https://pan.quark.cn/s/demo"))
        self.assertFalse(self.spider._is_supported_pan_url("https://pan.xunlei.com/s/demo"))

    def test_clean_search_title_and_normalize_title(self):
        self.assertEqual(
            self.spider._clean_search_title("<font color='red'>剑来</font> 第二季"),
            "剑来 第二季",
        )
        self.assertEqual(self.spider._normalize_title("《繁花》"), "繁花")
        self.assertEqual(self.spider._normalize_title("「诛仙」特别篇"), "诛仙")
        self.assertEqual(self.spider._normalize_title("普通标题"), "普通标题")

    def test_parse_cards_extracts_expected_fields(self):
        html = """
        <ul id="movielist">
          <li>
            <div class="pure-img"><img class="pure-img" data-original="/poster.jpg" /></div>
            <div class="intro">
              <h2><a href="/movie/123.html" title="《示例电影》">《示例电影》</a></h2>
            </div>
            <div class="dou"><b>8.8</b></div>
          </li>
        </ul>
        """
        self.assertEqual(
            self.spider._parse_cards(html),
            [
                {
                    "vod_id": "/movie/123.html",
                    "vod_name": "示例电影",
                    "vod_pic": "https://www.rrdynb.com/poster.jpg",
                    "vod_remarks": "8.8",
                }
            ],
        )

    @patch.object(Spider, "_request_html")
    def test_category_content_builds_reference_url_and_page_payload(self, mock_request_html):
        mock_request_html.return_value = """
        <ul id="movielist">
          <li>
            <img class="pure-img" data-original="/cate.jpg" />
            <div class="intro"><h2><a href="/movie/456.html" title="分类影片">分类影片</a></h2></div>
            <div class="dou"><b>更新中</b></div>
          </li>
        </ul>
        """
        result = self.spider.categoryContent("movie/list_2", "3", False, {})
        self.assertEqual(
            mock_request_html.call_args.args[0],
            "https://www.rrdynb.com/movie/list_2_3.html",
        )
        self.assertEqual(result["page"], 3)
        self.assertEqual(result["limit"], 1)
        self.assertEqual(result["list"][0]["vod_name"], "分类影片")
        self.assertNotIn("pagecount", result)
