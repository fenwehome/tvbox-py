import base64
import json
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
MODULE = SourceFileLoader("wanou_aggregate_spider", str(ROOT / "玩偶聚合.py")).load_module()
Spider = MODULE.Spider


class TestWanouAggregateSpider(unittest.TestCase):
    def setUp(self):
        Spider._instance = None
        self.spider = Spider()
        self.spider.init()

    def test_home_content_exposes_site_classes_and_category_filter(self):
        content = self.spider.homeContent(False)
        self.assertEqual(
            [item["type_id"] for item in content["class"][:3]],
            ["site_wanou", "site_muou", "site_labi"],
        )
        self.assertEqual(content["class"][0]["type_name"], "玩偶")
        self.assertEqual(content["filters"]["site_wanou"][0]["key"], "categoryId")
        self.assertEqual(content["filters"]["site_wanou"][0]["value"][1], {"n": "电影", "v": "1"})

    @patch.object(
        Spider,
        "_load_local_filter_groups",
        return_value=[
            {
                "key": "year",
                "name": "年份",
                "init": "",
                "value": [{"n": "全部", "v": ""}, {"n": "2025", "v": "2025"}],
            }
        ],
    )
    def test_home_content_appends_local_filter_groups_after_category_filter(self, mock_load_local_filter_groups):
        content = self.spider.homeContent(False)
        self.assertEqual(
            [item["key"] for item in content["filters"]["site_wanou"][:2]],
            ["categoryId", "year"],
        )

    def test_encode_and_decode_site_vod_id_round_trip(self):
        vod_id = self.spider._encode_site_vod_id("wanou", "/voddetail/12345.html")
        self.assertEqual(vod_id, "site:wanou:/voddetail/12345.html")
        self.assertEqual(
            self.spider._decode_site_vod_id(vod_id),
            {"site": "wanou", "path": "/voddetail/12345.html"},
        )

    def test_encode_and_decode_aggregate_vod_id_round_trip(self):
        payload = [
            {"site": "wanou", "path": "/voddetail/1.html", "name": "繁花", "year": "2024"},
            {"site": "muou", "path": "/voddetail/2.html", "name": "繁花", "year": "2024"},
        ]
        vod_id = self.spider._encode_aggregate_vod_id(payload)
        self.assertTrue(vod_id.startswith("agg:"))
        decoded = self.spider._decode_aggregate_vod_id(vod_id)
        self.assertEqual(decoded, payload)

    def test_normalize_title_removes_spaces_punctuation_and_resolution_tags(self):
        self.assertEqual(
            self.spider._normalize_title(" 繁花 4K.HDR-玩偶 "),
            "繁花",
        )

    def test_is_same_title_rejects_year_conflict(self):
        left = {"vod_name": "繁花", "vod_year": "2024"}
        right = {"vod_name": "繁花", "vod_year": "2023"}
        self.assertFalse(self.spider._is_same_title(left, right))
