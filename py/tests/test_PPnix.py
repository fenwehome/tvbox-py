import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
MODULE = SourceFileLoader("ppnix_spider", str(ROOT / "PPnix.py")).load_module()
Spider = MODULE.Spider


class TestPPnixSpider(unittest.TestCase):
    def setUp(self):
        Spider._instance = None
        self.spider = Spider()
        self.spider.init()

    def test_home_content_exposes_expected_categories_and_filter_keys(self):
        content = self.spider.homeContent(False)
        self.assertEqual([item["type_id"] for item in content["class"]], ["1", "2"])
        self.assertEqual([item["key"] for item in content["filters"]["1"]], ["class", "by"])
        self.assertEqual([item["key"] for item in content["filters"]["2"]], ["class", "by"])

    def test_build_category_url_maps_first_page_and_sort_values(self):
        self.assertEqual(
            self.spider._build_category_url("1", "1", {}),
            "https://www.ppnix.com/cn/movie/----newstime.html",
        )
        self.assertEqual(
            self.spider._build_category_url("2", "3", {"class": "爱情", "by": "hits"}),
            "https://www.ppnix.com/cn/tv/爱情---2-onclick.html",
        )

    def test_build_search_url_uses_ppnix_pattern(self):
        self.assertEqual(
            self.spider._build_search_url("繁花", "1"),
            "https://www.ppnix.com/cn/search/%E7%B9%81%E8%8A%B1--.html",
        )
        self.assertEqual(
            self.spider._build_search_url("繁花", "2"),
            "https://www.ppnix.com/cn/search/%E7%B9%81%E8%8A%B1--.html-page-2",
        )

    def test_parse_cards_extracts_short_vod_id_title_cover_and_remarks(self):
        html = """
        <ul>
          <li>
            <a class="thumbnail" href="/cn/movie/123.html">
              <img class="thumb" src="/poster.jpg" alt="示例影片" />
            </a>
            <footer><span class="rate">HD</span></footer>
          </li>
        </ul>
        """
        self.assertEqual(
            self.spider._parse_cards(html),
            [
                {
                    "vod_id": "movie/123.html",
                    "vod_name": "示例影片",
                    "vod_pic": "https://www.ppnix.com/poster.jpg",
                    "vod_remarks": "HD",
                }
            ],
        )

    @patch.object(Spider, "_request_html")
    def test_home_video_content_merges_movie_and_tv_cards(self, mock_request_html):
        mock_request_html.return_value = """
        <div class="lists-content">
          <ul>
            <li><a class="thumbnail" href="/cn/movie/101.html"><img class="thumb" src="/m.jpg" alt="电影一" /></a><footer><span class="rate">HD</span></footer></li>
          </ul>
        </div>
        <div class="lists-content">
          <ul>
            <li><a class="thumbnail" href="/cn/tv/201.html"><img class="thumb" src="/t.jpg" alt="剧集一" /></a><footer><span class="rate">更新中</span></footer></li>
          </ul>
        </div>
        """
        result = self.spider.homeVideoContent()
        self.assertEqual([item["vod_id"] for item in result["list"]], ["movie/101.html", "tv/201.html"])

    @patch.object(Spider, "_request_html")
    def test_category_content_uses_expected_listing_url(self, mock_request_html):
        mock_request_html.return_value = """
        <div class="lists-content"><ul>
          <li><a class="thumbnail" href="/cn/movie/301.html"><img class="thumb" src="/c.jpg" alt="分类影片" /></a><footer><span class="rate">HD</span></footer></li>
        </ul></div>
        """
        result = self.spider.categoryContent("1", "2", False, {"class": "动作", "by": "score"})
        self.assertEqual(
            mock_request_html.call_args.args[0],
            "https://www.ppnix.com/cn/movie/动作---1-rating.html",
        )
        self.assertEqual(result["page"], 2)
        self.assertEqual(result["list"][0]["vod_id"], "movie/301.html")
        self.assertNotIn("pagecount", result)

    @patch.object(Spider, "_request_html")
    def test_search_content_parses_only_movie_and_tv_ids(self, mock_request_html):
        mock_request_html.return_value = """
        <div class="lists-content"><ul>
          <li><a class="thumbnail" href="/cn/movie/401.html"><img class="thumb" src="/s1.jpg" alt="搜索电影" /></a></li>
          <li><a class="thumbnail" href="/cn/topic/ignore.html"><img class="thumb" src="/s2.jpg" alt="忽略条目" /></a></li>
        </ul></div>
        """
        result = self.spider.searchContent("搜索词", False, "1")
        self.assertEqual(
            mock_request_html.call_args.args[0],
            "https://www.ppnix.com/cn/search/%E6%90%9C%E7%B4%A2%E8%AF%8D--.html",
        )
        self.assertEqual([item["vod_id"] for item in result["list"]], ["movie/401.html"])
        self.assertNotIn("pagecount", result)

    def test_extract_m3u8_items_reads_infoid_and_episode_names(self):
        html = """
        <script>
        var infoid = 7788;
        var m3u8 = ["第1集", "第2集"];
        </script>
        """
        self.assertEqual(
            self.spider._extract_m3u8_items(html),
            {"info_id": "7788", "items": ["第1集", "第2集"]},
        )

    @patch.object(Spider, "_request_html")
    def test_detail_content_builds_ppnix_play_group(self, mock_request_html):
        mock_request_html.return_value = """
        <h1 class="product-title">示例剧 (2025)</h1>
        <header class="product-header"><img class="thumb" src="/poster.jpg" /></header>
        <div class="product-excerpt">导演：<span>导演甲</span></div>
        <div class="product-excerpt">主演：<span>演员甲 / 演员乙</span></div>
        <div class="product-excerpt">简介：一段剧情简介</div>
        <script>
        var infoid = 8899;
        var m3u8 = ["第1集", "第2集"];
        </script>
        """
        result = self.spider.detailContent(["tv/8899.html"])
        vod = result["list"][0]
        self.assertEqual(vod["vod_id"], "tv/8899.html")
        self.assertEqual(vod["vod_name"], "示例剧")
        self.assertEqual(vod["vod_pic"], "https://www.ppnix.com/poster.jpg")
        self.assertEqual(vod["vod_year"], "2025")
        self.assertEqual(vod["vod_director"], "导演甲")
        self.assertEqual(vod["vod_actor"], "演员甲,演员乙")
        self.assertEqual(vod["vod_content"], "一段剧情简介")
        self.assertEqual(vod["vod_play_from"], "PPnix")
        self.assertEqual(
            vod["vod_play_url"],
            "第1集$8899|%E7%AC%AC1%E9%9B%86#第2集$8899|%E7%AC%AC2%E9%9B%86",
        )

    def test_player_content_returns_direct_m3u8_url(self):
        result = self.spider.playerContent("PPnix", "8899|%E7%AC%AC1%E9%9B%86", {})
        self.assertEqual(result["parse"], 0)
        self.assertEqual(result["jx"], 0)
        self.assertEqual(result["url"], "https://www.ppnix.com/info/m3u8/8899/%E7%AC%AC1%E9%9B%86.m3u8")
        self.assertEqual(result["header"]["Origin"], "https://www.ppnix.com")

    def test_player_content_falls_back_when_play_id_is_invalid(self):
        result = self.spider.playerContent("PPnix", "broken", {})
        self.assertEqual(result["parse"], 1)
        self.assertEqual(result["jx"], 1)
        self.assertEqual(result["url"], "broken")


if __name__ == "__main__":
    unittest.main()
