import base64
import json
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad


ROOT = Path(__file__).resolve().parents[1]
MODULE = SourceFileLoader("rrmj_spider", str(ROOT / "人人视频.py")).load_module()
Spider = MODULE.Spider


def encrypt_ecb_payload(payload):
    cipher = AES.new(MODULE.AES_KEY.encode("utf-8"), AES.MODE_ECB)
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    return base64.b64encode(cipher.encrypt(pad(body, AES.block_size))).decode("utf-8")


def encrypt_cbc_payload(value, new_sign):
    key = new_sign[4:20].encode("utf-8")
    cipher = AES.new(key, AES.MODE_CBC, MODULE.AES_IV.encode("utf-8"))
    return base64.b64encode(cipher.encrypt(pad(value.encode("utf-8"), AES.block_size))).decode("utf-8")


class TestRenRenShiPinSpider(unittest.TestCase):
    def setUp(self):
        Spider._instance = None
        self.spider = Spider()
        self.spider.init()

    def test_module_uses_pycryptodome_and_hmac(self):
        source = (ROOT / "人人视频.py").read_text(encoding="utf-8")
        self.assertIn("from Crypto.Cipher import AES", source)
        self.assertIn("from Crypto.Util.Padding import pad, unpad", source)
        self.assertIn("import hmac", source)

    def test_home_video_content_returns_empty_list(self):
        self.assertEqual(self.spider.homeVideoContent(), {"list": []})

    @patch("rrmj_spider.time.time", return_value=1713523200.123)
    def test_create_headers_signs_sorted_params(self, mock_time):
        headers = self.spider._create_headers(
            "/m-station/drama/drama_filter_search",
            {
                "sort": "hot",
                "dramaType": "TV",
                "year": "",
            },
            method="POST",
        )
        self.assertEqual(headers["t"], "1713523200123")
        self.assertEqual(headers["aliId"], MODULE.KY_ID)
        self.assertEqual(
            headers["x-ca-sign"],
            "wmstQtQaO9LiPx+xbWpi7LncPdyFnf6eVrVTNgoDDBU=",
        )

    @patch.object(Spider, "fetch")
    def test_request_api_decrypts_ecb_response(self, mock_fetch):
        mock_fetch.return_value = SimpleNamespace(
            status_code=200,
            text=encrypt_ecb_payload({"code": "0000", "data": {"ok": True}}),
        )
        result = self.spider._request_api("/m-station/drama/get_drama_filter")
        self.assertEqual(result, {"code": "0000", "data": {"ok": True}})
        self.assertEqual(
            mock_fetch.call_args.args[0],
            "https://api.rrmj.plus/m-station/drama/get_drama_filter",
        )

    @patch.object(Spider, "_request_api")
    def test_home_content_maps_expected_classes_and_filters(self, mock_request_api):
        mock_request_api.return_value = {
            "code": "0000",
            "data": [
                {
                    "filterType": "sort",
                    "dramaFilterItemList": [
                        {"displayName": "最热", "value": "hot"},
                        {"displayName": "最新", "value": "new"},
                    ],
                },
                {
                    "filterType": "dramaType",
                    "dramaFilterItemList": [
                        {"displayName": "全部", "value": ""},
                        {"displayName": "电视剧", "value": "TV"},
                        {"displayName": "电影", "value": "MOVIE"},
                        {"displayName": "综艺", "value": "VARIETY"},
                        {"displayName": "纪录片", "value": "DOCUMENTARY"},
                        {"displayName": "动漫", "value": "COMIC"},
                    ],
                },
                {
                    "filterType": "area",
                    "dramaFilterItemList": [
                        {"displayName": "全部", "value": ""},
                        {"displayName": "内地", "value": "中国大陆"},
                    ],
                },
                {
                    "filterType": "plotType",
                    "dramaFilterItemList": [
                        {"displayName": "全部", "value": ""},
                        {"displayName": "悬疑", "value": "悬疑"},
                    ],
                },
                {
                    "filterType": "year",
                    "dramaFilterItemList": [
                        {"displayName": "全部", "value": ""},
                        {"displayName": "2026", "value": "2026"},
                    ],
                },
            ],
        }
        result = self.spider.homeContent(False)
        self.assertEqual(
            result["class"],
            [
                {"type_id": "TV", "type_name": "剧集"},
                {"type_id": "MOVIE", "type_name": "电影"},
                {"type_id": "VARIETY", "type_name": "综艺"},
                {"type_id": "COMIC", "type_name": "动漫"},
            ],
        )
        self.assertEqual([item["key"] for item in result["filters"]["TV"]], ["area", "class", "year", "by"])
        self.assertEqual(result["filters"]["TV"][0]["value"][1], {"n": "内地", "v": "中国大陆"})
        self.assertEqual(result["filters"]["TV"][1]["value"][1], {"n": "悬疑", "v": "悬疑"})
        self.assertEqual(result["filters"]["TV"][3]["value"][1], {"n": "最新", "v": "new"})

    @patch.object(Spider, "_request_api")
    def test_category_content_posts_expected_payload_and_omits_pagecount(self, mock_request_api):
        mock_request_api.return_value = {
            "code": "0000",
            "data": [
                {
                    "dramaId": 56433,
                    "title": "神与律师事务所",
                    "coverUrl": "https://img.example/poster.jpg",
                    "year": "2026",
                    "subtitle": "柳演锡x李絮x金景南",
                }
            ],
        }
        result = self.spider.categoryContent(
            "TV",
            "2",
            False,
            {"area": "韩国", "year": "2026", "class": "悬疑", "by": "new"},
        )
        self.assertEqual(
            mock_request_api.call_args.args,
            (
                "/m-station/drama/drama_filter_search",
                {
                    "area": "韩国",
                    "sort": "new",
                    "year": "2026",
                    "dramaType": "TV",
                    "plotType": "悬疑",
                    "contentLabel": "",
                    "page": 2,
                    "rows": 30,
                },
            ),
        )
        self.assertEqual(result["page"], 2)
        self.assertEqual(result["list"][0]["vod_id"], "56433")
        self.assertEqual(result["list"][0]["vod_remarks"], "2026 柳演锡x李絮x金景南")
        self.assertNotIn("pagecount", result)

    @patch.object(Spider, "_request_api")
    def test_detail_content_maps_metadata_and_episode_ids(self, mock_request_api):
        mock_request_api.return_value = {
            "code": "0000",
            "data": {
                "dramaInfo": {
                    "dramaId": 56433,
                    "title": "神与律师事务所",
                    "cover": "https://img.example/detail.jpg",
                    "description": "一段剧情简介",
                    "year": 2026,
                    "area": "韩国",
                    "plotType": "剧情/悬疑",
                    "subtitle": "柳演锡x李絮x金景南",
                    "playStatus": "更新至12集",
                },
                "episodeList": [
                    {"id": 380772, "episodeNo": 1, "title": ""},
                    {"id": 380810, "episodeNo": 2, "title": "特别篇"},
                ],
            },
        }
        result = self.spider.detailContent(["56433"])
        vod = result["list"][0]
        self.assertEqual(vod["vod_id"], "56433")
        self.assertEqual(vod["vod_name"], "神与律师事务所")
        self.assertEqual(vod["vod_pic"], "https://img.example/detail.jpg")
        self.assertEqual(vod["vod_content"], "一段剧情简介")
        self.assertEqual(vod["vod_year"], "2026")
        self.assertEqual(vod["vod_area"], "韩国")
        self.assertEqual(vod["type_name"], "剧情/悬疑")
        self.assertEqual(vod["vod_actor"], "柳演锡x李絮x金景南")
        self.assertEqual(vod["vod_play_from"], "人人专线")
        self.assertEqual(vod["vod_play_url"], "第1集$56433@380772#特别篇$56433@380810")

    @patch.object(Spider, "fetch")
    @patch.object(Spider, "_request_api")
    def test_player_content_decrypts_play_url_and_uses_redirect_location(self, mock_request_api, mock_fetch):
        new_sign = "ngXN+eiB3og7T+Zf3iojv6zn6GFDjCi+9COuBBGHO6Y="
        encrypted_url = encrypt_cbc_payload("https://video.example/decrypted.mp4", new_sign)
        mock_request_api.return_value = {
            "code": "0000",
            "data": {
                "m3u8": {"url": encrypted_url},
                "newSign": new_sign,
            },
        }
        mock_fetch.return_value = SimpleNamespace(status_code=302, headers={"location": "https://video.example/final.mp4"})
        result = self.spider.playerContent("人人专线", "56433@380772", {})
        self.assertEqual(result["parse"], 0)
        self.assertEqual(result["jx"], 0)
        self.assertEqual(result["url"], "https://video.example/final.mp4")
        self.assertEqual(result["header"]["Referer"], MODULE.HOST)

    @patch.object(Spider, "_request_api")
    def test_search_content_prefers_precise_results_and_omits_pagecount(self, mock_request_api):
        mock_request_api.return_value = {
            "code": "0000",
            "data": {
                "seasonList": [
                    {
                        "id": "56433",
                        "title": "神与律师事务所",
                        "cover": "https://img.example/cover.jpg",
                        "year": "2026",
                        "classify": "电视剧",
                    }
                ],
                "fuzzySeasonList": [
                    {
                        "id": "56694",
                        "title": "山田轰律师事务所",
                        "cover": "https://img.example/fuzzy.jpg",
                        "year": "2026",
                        "classify": "电视剧",
                    }
                ],
            },
        }
        result = self.spider.searchContent("律师事务所", False, "1")
        self.assertEqual(
            result["list"],
            [
                {
                    "vod_id": "56433",
                    "vod_name": "神与律师事务所",
                    "vod_pic": "https://img.example/cover.jpg",
                    "vod_remarks": "2026 电视剧",
                }
            ],
        )
        self.assertNotIn("pagecount", result)


if __name__ == "__main__":
    unittest.main()
