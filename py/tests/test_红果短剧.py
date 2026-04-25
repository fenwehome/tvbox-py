import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest.mock import MagicMock, patch


ROOT = Path(__file__).resolve().parents[1]
MODULE = SourceFileLoader("hongguo_spider", str(ROOT / "红果短剧.py")).load_module()
Spider = MODULE.Spider


class TestHongGuoDuanJuSpider(unittest.TestCase):
    def setUp(self):
        Spider._instance = None
        self.spider = Spider()
        self.spider.init()

    def test_home_content_exposes_categories(self):
        content = self.spider.homeContent(False)
        ids = [item["type_id"] for item in content["class"]]
        self.assertEqual(content["class"][0]["type_id"], "逆袭")
        self.assertIn("现代言情", ids)
        self.assertNotIn("热播", ids)
        self.assertIn("分类", content["filters"])

    @patch.object(Spider, "_get_json")
    def test_home_video_content_uses_hot_category(self, mock_json):
        mock_json.return_value = {
            "data": [
                {"id": 1, "title": "【热播】逆袭人生", "cover": "http://img/1.jpg", "totalChapterNum": 88}
            ]
        }
        result = self.spider.homeVideoContent()
        self.assertEqual(result["list"][0]["vod_id"], "1")
        self.assertEqual(result["list"][0]["vod_name"], "逆袭人生")
        self.assertEqual(result["list"][0]["vod_remarks"], "更新至88集")
        self.assertIn("name=%E7%83%AD%E6%92%AD", mock_json.call_args.args[0])

    @patch.object(Spider, "_get_json")
    def test_category_content_builds_query_and_maps_items(self, mock_json):
        mock_json.return_value = {
            "data": [
                {"book_id": "b2", "title": "新剧回归", "cover": "http://img/2.jpg", "sub_title": "36集"}
            ]
        }
        result = self.spider.categoryContent("穿越", "3", False, {})
        self.assertEqual(result["page"], 3)
        self.assertEqual(result["list"][0]["vod_id"], "b2")
        self.assertEqual(result["list"][0]["vod_remarks"], "36集")
        self.assertNotIn("pagecount", result)
        self.assertIn("/api/duanju/api.php?", mock_json.call_args.args[0])
        self.assertIn("classname=%E7%A9%BF%E8%B6%8A", mock_json.call_args.args[0])
        self.assertIn("offset=40", mock_json.call_args.args[0])
        self.assertIn("showRawParams=false", mock_json.call_args.args[0])

    @patch.object(Spider, "_get_json")
    def test_search_content_uses_keyword_query(self, mock_json):
        mock_json.return_value = {
            "data": [
                {"id": 3, "title": "霸总归来", "cover": "", "totalChapterNum": 12}
            ]
        }
        result = self.spider.searchContent("霸总", False, "1")
        self.assertEqual(result["list"][0]["vod_name"], "霸总归来")
        self.assertIn("name=%E9%9C%B8%E6%80%BB&page=1", mock_json.call_args.args[0])

    @patch.object(Spider, "_get_json")
    def test_search_content_returns_empty_for_blank_keyword(self, mock_json):
        result = self.spider.searchContent("", False, "1")
        self.assertEqual(result["list"], [])
        mock_json.assert_not_called()

    @patch.object(Spider, "fetch")
    def test_category_content_returns_empty_for_invalid_json_response(self, mock_fetch):
        mock_fetch.return_value = MagicMock(status_code=200, text="<html>blocked</html>")
        result = self.spider.categoryContent("新剧", "1", False, {})
        self.assertEqual(result, {"page": 1, "limit": 0, "total": 0, "list": []})

    def test_clean_title_removes_hot_and_new_tags(self):
        self.assertEqual(self.spider._clean_title("【热播】新剧名"), "新剧名")
        self.assertEqual(self.spider._clean_title("[新剧热播] 第二部"), "第二部")

    @patch.object(Spider, "_get_json")
    def test_detail_content_builds_single_playlist(self, mock_json):
        mock_json.return_value = {
            "book_id": "100",
            "book_name": "总裁有疾闪婚来袭",
            "author": "树下的椰子",
            "category_names": ["都市爱情", "闪婚", "总裁"],
            "desc": "一段剧情简介",
            "duration": "1小时43分钟",
            "book_pic": "http://img/d.jpg",
            "time": "2026-04-25 09:32:02",
            "total": "2",
            "data": [
                {"title": "第1集", "video_id": "v1", "volume_name": ""},
                {"title": "第2集", "video_id": "v2", "volume_name": ""},
            ]
        }
        result = self.spider.detailContent(["100"])
        vod = result["list"][0]
        self.assertEqual(vod["vod_id"], "100")
        self.assertEqual(vod["vod_name"], "总裁有疾闪婚来袭")
        self.assertEqual(vod["vod_pic"], "http://img/d.jpg")
        self.assertEqual(vod["vod_remarks"], "1小时43分钟")
        self.assertEqual(vod["vod_actor"], "树下的椰子")
        self.assertEqual(vod["vod_area"], "都市爱情,闪婚,总裁")
        self.assertEqual(vod["vod_content"], "一段剧情简介")
        self.assertEqual(vod["vod_play_from"], "红果短剧")
        self.assertIn("第1集$v1", vod["vod_play_url"])
        self.assertIn("第2集$v2", vod["vod_play_url"])
        self.assertEqual(
            mock_json.call_args.args[0],
            "https://api-v2.cenguigui.cn/api/duanju/api.php?book_id=100",
        )

    @patch.object(Spider, "_get_json")
    def test_detail_content_returns_empty_when_id_missing(self, mock_json):
        result = self.spider.detailContent([""])
        self.assertEqual(result, {"list": []})
        mock_json.assert_not_called()

    def test_sort_qualities_prefers_1080p_then_sc_then_sd(self):
        ordered = self.spider._sort_qualities(
            [
                {"quality": "sd", "download_url": "sd.mp4"},
                {"quality": "1080p", "download_url": "1080.mp4"},
                {"quality": "sc", "download_url": "sc.mp4"},
            ]
        )
        self.assertEqual([item["quality"] for item in ordered], ["1080p", "sc", "sd"])

    @patch.object(Spider, "_get_json")
    def test_player_content_returns_best_quality_direct_url(self, mock_json):
        mock_json.return_value = {"url": "http://video/play.mp4"}
        result = self.spider.playerContent("红果短剧", "v1", {})
        self.assertEqual(result["parse"], 0)
        self.assertEqual(result["url"], "http://video/play.mp4")
        self.assertEqual(
            mock_json.call_args.args[0],
            "https://api-v2.cenguigui.cn/api/duanju/api.php?video_id=v1",
        )

    @patch.object(Spider, "_get_json")
    def test_player_content_returns_empty_url_on_error(self, mock_json):
        mock_json.side_effect = Exception("boom")
        result = self.spider.playerContent("红果短剧", "v2", {})
        self.assertEqual(result["parse"], 0)
        self.assertEqual(result["url"], "")


if __name__ == "__main__":
    unittest.main()
