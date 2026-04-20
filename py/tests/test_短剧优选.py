import unittest
import json
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest.mock import patch, MagicMock

ROOT = Path(__file__).resolve().parents[1]
MODULE = SourceFileLoader("duanjuyx_spider", str(ROOT / "短剧优选.py")).load_module()
Spider = MODULE.Spider


class TestDuanjuYouxuanSpider(unittest.TestCase):
    def setUp(self):
        Spider._instance = None
        self.spider = Spider()
        self.spider.init()

    def test_home_content_has_active_platforms(self):
        content = self.spider.homeContent(False)
        ids = [c["type_id"] for c in content["class"]]
        self.assertIn("七猫", ids)
        self.assertIn("星芽", ids)
        self.assertIn("西饭", ids)
        self.assertIn("七星", ids)
        self.assertIn("短剧网", ids)

    def test_home_content_has_filters(self):
        content = self.spider.homeContent(False)
        self.assertIn("七猫", content["filters"])
        self.assertIn("短剧网", content["filters"])
        qm_filter = content["filters"]["七猫"][0]
        self.assertEqual(qm_filter["key"], "area")
        self.assertTrue(len(qm_filter["value"]) > 50)

    def test_home_video_content_returns_empty(self):
        self.assertEqual(self.spider.homeVideoContent(), {"list": []})

    def test_player_tianquan(self):
        result = self.spider.playerContent("甜圈短剧", "vid123", {})
        self.assertEqual(result["parse"], 0)
        self.assertIn("video_id=vid123", result["url"])

    def test_player_xingya_passthrough(self):
        result = self.spider.playerContent("星芽短剧", "https://example.com/video.m3u8", {})
        self.assertEqual(result["url"], "https://example.com/video.m3u8")

    def test_player_weiguan_selects_super(self):
        play_setting = {"super": "s.mp4", "high": "h.mp4", "normal": "n.mp4"}
        result = self.spider.playerContent("围观短剧", json.dumps(play_setting), {})
        self.assertEqual(result["url"], "s.mp4")

    def test_player_weiguan_falls_back_to_high(self):
        play_setting = {"high": "h.mp4", "normal": "n.mp4"}
        result = self.spider.playerContent("围观短剧", json.dumps(play_setting), {})
        self.assertEqual(result["url"], "h.mp4")

    def test_player_weiguan_invalid_json(self):
        result = self.spider.playerContent("围观短剧", "not-json", {})
        self.assertEqual(result["url"], "not-json")

    def test_player_duanjuwang_passthrough(self):
        result = self.spider.playerContent("短剧网", "push://pan.quark.cn/abc", {})
        self.assertEqual(result["parse"], 0)
        self.assertEqual(result["url"], "push://pan.quark.cn/abc")

    @patch.object(Spider, "_get_text")
    def test_player_juwang_extracts_m3u8(self, mock_text):
        mock_text.return_value = 'var data = {"wwm3u8": "https:\\/\\/cdn.example.com\\/video.m3u8"};'
        result = self.spider.playerContent("剧王短剧", "https://djw1.com/play/123", {})
        self.assertEqual(result["url"], "https://cdn.example.com/video.m3u8")
        self.assertEqual(result["parse"], 0)

    @patch.object(Spider, "_get_json")
    def test_category_tianquan(self, mock_json):
        mock_json.return_value = {
            "data": [
                {"book_id": "b1", "title": "逆袭人生", "cover": "http://pic/1.jpg", "sub_title": "60集"},
                {"book_id": "b2", "title": "霸总归来", "cover": "http://pic/2.jpg", "sub_title": "80集"},
            ]
        }
        result = self.spider.categoryContent("甜圈", "1", False, {"area": "逆袭"})
        self.assertEqual(len(result["list"]), 2)
        self.assertEqual(result["list"][0]["vod_id"], "甜圈@b1")
        self.assertEqual(result["list"][0]["vod_name"], "逆袭人生")
        self.assertEqual(result["pagecount"], 2)

    @patch.object(Spider, "_post_json")
    def test_category_weiguan(self, mock_json):
        mock_json.return_value = {
            "data": [
                {"oneId": "wg1", "title": "都市情缘", "vertPoster": "http://pic/wg.jpg", "episodeCount": 50},
            ]
        }
        result = self.spider.categoryContent("围观", "1", False, {"area": "都市"})
        self.assertEqual(len(result["list"]), 1)
        self.assertEqual(result["list"][0]["vod_id"], "围观@wg1")

    @patch.object(Spider, "_get_text")
    def test_category_duanjuwang(self, mock_text):
        mock_text.return_value = """
        <li class="col-6">
          <h3 class="f-14"><a href="/detail/123.html">短剧名（60集完结）</a></h3>
          <img class="lazy" data-original="/cover.jpg" />
        </li>
        """
        result = self.spider.categoryContent("短剧网", "1", False, {"area": "1"})
        self.assertEqual(len(result["list"]), 1)
        self.assertEqual(result["list"][0]["vod_id"], "短剧网@https://sm3.cc/detail/123.html")
        self.assertEqual(result["list"][0]["vod_name"], "短剧名（60集完结）")
        self.assertEqual(result["list"][0]["vod_remarks"], "")
        self.assertEqual(result["pagecount"], 2)

    @patch.object(Spider, "_get_json")
    def test_category_empty_result(self, mock_json):
        mock_json.return_value = {"data": []}
        result = self.spider.categoryContent("甜圈", "2", False, {"area": "逆袭"})
        self.assertEqual(result["list"], [])
        self.assertEqual(result["pagecount"], 2)

    @patch.object(Spider, "_get_json")
    def test_detail_tianquan(self, mock_json):
        mock_json.return_value = {
            "book_name": "甜剧1号", "book_pic": "http://pic/t.jpg", "desc": "剧情简介",
            "duration": "60分钟", "author": "作者", "time": "2025-01-01",
            "data": [
                {"title": "第1集", "video_id": "v1"},
                {"title": "第2集", "video_id": "v2"},
            ],
        }
        result = self.spider.detailContent(["甜圈@b1"])
        vod = result["list"][0]
        self.assertEqual(vod["vod_name"], "甜剧1号")
        self.assertEqual(vod["vod_play_from"], "甜圈短剧")
        self.assertIn("第1集$v1", vod["vod_play_url"])
        self.assertIn("第2集$v2", vod["vod_play_url"])

    @patch.object(Spider, "_get_json")
    def test_detail_weiguan(self, mock_json):
        mock_json.return_value = {
            "data": [
                {"title": "逆袭", "playOrder": 1, "playSetting": {"super": "s1.mp4"}, "vertPoster": "p.jpg", "collectionCount": 100},
                {"title": "逆袭", "playOrder": 2, "playSetting": {"super": "s2.mp4"}, "vertPoster": "p.jpg", "collectionCount": 100},
            ]
        }
        result = self.spider.detailContent(["围观@wg1"])
        vod = result["list"][0]
        self.assertEqual(vod["vod_name"], "逆袭")
        self.assertEqual(vod["vod_remarks"], "共2集")
        self.assertIn("围观短剧", vod["vod_play_from"])

    @patch.object(Spider, "_get_text")
    def test_detail_juwang(self, mock_text):
        mock_text.return_value = """
        <html><body>
        <h1>剧王短剧名</h1>
        <img src="/poster.jpg" />
        <div class="info-detail">剧情简介</div>
        <div class="ep-list">
          <a href="/play/1-1.html">第1集</a>
          <a href="/play/1-2.html">第2集</a>
        </div>
        </body></html>
        """
        result = self.spider.detailContent(["剧王@/show/123"])
        vod = result["list"][0]
        self.assertEqual(vod["vod_name"], "剧王短剧名")
        self.assertEqual(vod["vod_content"], "剧情简介")
        self.assertEqual(vod["vod_play_from"], "剧王短剧")
        self.assertIn("第1集$/play/1-1.html", vod["vod_play_url"])

    @patch.object(Spider, "_get_text")
    def test_detail_duanjuwang(self, mock_text):
        mock_text.return_value = """
        <html><body>
        <h1>网盘短剧名</h1>
        <img class="lazy" data-original="/poster.jpg" />
        <div class="content">
          <a href="https://pan.quark.cn/s/abc123">夸克链接</a>
          <a href="https://pan.baidu.com/s/xyz789">百度链接</a>
        </div>
        </body></html>
        """
        result = self.spider.detailContent(["短剧网@https://sm3.cc/detail/123"])
        vod = result["list"][0]
        self.assertEqual(vod["vod_name"], "网盘短剧名")
        self.assertEqual(vod["vod_content"], "此为推送网盘规则")
        self.assertIn("quark", vod["vod_play_from"])
        self.assertIn("baidu", vod["vod_play_from"])
        self.assertIn("quark$https://pan.quark.cn/s/abc123", vod["vod_play_url"])

    @patch.object(Spider, "_get_text")
    def test_detail_duanjuwang_no_netdisk_links(self, mock_text):
        mock_text.return_value = """
        <html><body>
        <h1>无链接短剧</h1>
        <div class="content"><p>暂无链接</p></div>
        </body></html>
        """
        result = self.spider.detailContent(["短剧网@https://sm3.cc/detail/456"])
        vod = result["list"][0]
        self.assertEqual(vod["vod_name"], "无链接短剧")
        self.assertEqual(vod["vod_play_from"], "短剧网")
        self.assertEqual(vod["vod_play_url"], "")

    @patch.object(Spider, "_get_json")
    def test_detail_failure_returns_error_vod(self, mock_json):
        mock_json.side_effect = Exception("network error")
        result = self.spider.detailContent(["甜圈@missing"])
        vod = result["list"][0]
        self.assertIn("详情加载失败", vod["vod_name"])

    @patch.object(Spider, "_aggregate_search")
    def test_search_filters_by_keyword(self, mock_search):
        mock_search.return_value = [
            {"vod_id": "甜圈@1", "vod_name": "逆袭人生", "vod_pic": "", "vod_remarks": ""},
            {"vod_id": "七猫@2", "vod_name": "霸道总裁", "vod_pic": "", "vod_remarks": ""},
        ]
        result = self.spider.searchContent("逆袭", False, "1")
        self.assertEqual(len(result["list"]), 1)
        self.assertEqual(result["list"][0]["vod_name"], "逆袭人生")

    @patch.object(Spider, "_aggregate_search")
    def test_search_empty_keyword(self, mock_search):
        result = self.spider.searchContent("", False, "1")
        self.assertEqual(result["list"], [])
        mock_search.assert_not_called()

    def test_filter_defaults(self):
        self.assertEqual(self.spider.filter_defaults["七猫"]["area"], "0")
        self.assertEqual(self.spider.filter_defaults["围观"]["area"], "都市")
        self.assertEqual(self.spider.filter_defaults["短剧网"]["area"], "1")

    def test_identify_disk(self):
        self.assertEqual(self.spider._identify_disk("https://pan.quark.cn/s/abc"), "quark")
        self.assertEqual(self.spider._identify_disk("https://pan.baidu.com/s/xyz"), "baidu")
        self.assertEqual(self.spider._identify_disk("https://drive.uc.cn/s/123"), "uc")
        self.assertEqual(self.spider._identify_disk("https://example.com/video.mp4"), "")


if __name__ == "__main__":
    unittest.main()
