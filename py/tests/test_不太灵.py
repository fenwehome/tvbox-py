import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
MODULE = SourceFileLoader("butailing_spider", str(ROOT / "不太灵.py")).load_module()
Spider = MODULE.Spider


class FakeResponse:
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code
        self.encoding = "utf-8"


class TestBuTaiLingSpider(unittest.TestCase):
    def setUp(self):
        Spider._instance = None
        self.spider = Spider()
        self.spider.init()

    def test_home_content_returns_fixed_categories_and_filters(self):
        with patch.object(
            Spider,
            "_request_api",
            return_value={"t1": [{"title": "动作"}], "t2": [{"title": "中国"}], "t3": [], "t4": [], "t5": []},
        ):
            content = self.spider.homeContent(False)

        self.assertEqual(
            [item["type_id"] for item in content["class"]],
            ["1", "2", "3", "4", "5"],
        )
        self.assertIn("1", content["filters"])
        self.assertIn("2", content["filters"])
        self.assertEqual(content["filters"]["1"][0]["key"], "sc")

    @patch.object(Spider, "_request_api")
    def test_home_video_content_requests_recent_hot_list(self, mock_request_api):
        mock_request_api.return_value = [
            {"doub_id": 11, "title": "示例电影", "image": "https://img.test/poster.jpg", "ejs": "HD"}
        ]
        content = self.spider.homeVideoContent()
        self.assertEqual(mock_request_api.call_args.args[0], "getVideoList")
        self.assertEqual(mock_request_api.call_args.args[1]["sc"], "3")
        self.assertEqual(content["list"][0]["vod_id"], "11")
        self.assertEqual(content["list"][0]["vod_remarks"], "HD")

    def test_build_api_url_appends_credentials(self):
        url = self.spider._build_api_url("getVideoList", {"page": 2, "limit": 24})
        self.assertIn("getVideoList", url)
        self.assertIn("app_id=83768d9ad4", url)
        self.assertIn("identity=23734adac0301bccdcb107c4aa21f96c", url)
        self.assertIn("page=2", url)

    @patch("requests.get")
    def test_request_api_parses_json_and_callback_payload(self, mock_get):
        mock_get.return_value = FakeResponse('callback({"success":true,"code":200,"data":{"data":[{"doub_id": 1}]}})')
        result = self.spider._request_api("getVideoList", {"page": 1})
        self.assertEqual(result, [{"doub_id": 1}])


if __name__ == "__main__":
    unittest.main()
