import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest.mock import patch


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

    def test_fix_json_wrapped_html_unwraps_html_string(self):
        wrapped = "\"<html><body>ok</body></html>\""
        self.assertEqual(self.spider._fix_json_wrapped_html(wrapped), "<html><body>ok</body></html>")

    def test_parse_cards_extracts_short_vod_id_title_cover_and_remarks(self):
        html = """
        <ul class="stui-vodlist clearfix">
          <li>
            <a href="/voddetail/12345.html" title="示例影片" data-original="/cover.jpg"></a>
            <span class="pic-text">更新至10集</span>
          </li>
        </ul>
        """
        cards = self.spider._parse_cards(html)
        self.assertEqual(
            cards,
            [
                {
                    "vod_id": "voddetail/12345.html",
                    "vod_name": "示例影片",
                    "vod_pic": "https://www.zxzjhd.com/cover.jpg",
                    "vod_remarks": "更新至10集",
                }
            ],
        )

    @patch.object(Spider, "_request_html")
    def test_category_content_uses_built_url_and_returns_page_result(self, mock_request_html):
        mock_request_html.return_value = """
        <ul class="stui-vodlist clearfix">
          <li>
            <a href="/voddetail/23456.html" title="分类影片" data-original="/cate.jpg"></a>
            <span class="pic-text">HD</span>
          </li>
        </ul>
        """
        result = self.spider.categoryContent("1", "2", False, {"area": "欧美"})
        self.assertEqual(mock_request_html.call_args.args[0], "https://www.zxzjhd.com/vodshow/1-欧美-------2---.html")
        self.assertEqual(result["page"], 2)
        self.assertEqual(result["limit"], 24)
        self.assertEqual(result["list"][0]["vod_id"], "voddetail/23456.html")
        self.assertNotIn("pagecount", result)

    @patch.object(Spider, "_request_html")
    def test_search_content_parses_search_cards(self, mock_request_html):
        mock_request_html.return_value = """
        <ul class="stui-vodlist clearfix">
          <li>
            <a href="/voddetail/34567.html" title="搜索命中" data-original="/search.jpg"></a>
            <span class="pic-text">抢先版</span>
          </li>
        </ul>
        """
        result = self.spider.searchContent("繁花", False, "1")
        self.assertEqual(
            mock_request_html.call_args.args[0],
            "https://www.zxzjhd.com/vodsearch/%E7%B9%81%E8%8A%B1-------------.html",
        )
        self.assertEqual(result["list"][0]["vod_name"], "搜索命中")
        self.assertNotIn("pagecount", result)


if __name__ == "__main__":
    unittest.main()
