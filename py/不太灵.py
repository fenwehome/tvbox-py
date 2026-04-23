# coding=utf-8
import json
import sys
from urllib.parse import urlencode, urljoin

import requests

from base.spider import Spider as BaseSpider

sys.path.append("..")


class Spider(BaseSpider):
    def __init__(self):
        self.name = "不太灵"
        self.api_base = "https://web5.mukaku.com/prod/api/v1/"
        self.app_id = "83768d9ad4"
        self.identity = "23734adac0301bccdcb107c4aa21f96c"
        self.timeout = 10
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Referer": self.api_base,
        }
        self.classes = [
            {"type_id": "1", "type_name": "电影"},
            {"type_id": "2", "type_name": "电视剧"},
            {"type_id": "3", "type_name": "近日热门"},
            {"type_id": "4", "type_name": "本周热门"},
            {"type_id": "5", "type_name": "本月热门"},
        ]

    def init(self, extend=""):
        return None

    def getName(self):
        return self.name

    def _build_api_url(self, endpoint, params=None):
        query = {"app_id": self.app_id, "identity": self.identity}
        query.update(params or {})
        return urljoin(self.api_base, endpoint) + "?" + urlencode(query)

    def _parse_payload(self, text):
        raw = str(text or "").strip()
        if raw.startswith("callback(") and raw.endswith(")"):
            raw = raw[9:-1]
        return json.loads(raw) if raw else {}

    def _request_api(self, endpoint, params=None):
        response = requests.get(
            self._build_api_url(endpoint, params),
            headers=dict(self.headers),
            timeout=self.timeout,
            verify=False,
        )
        if response.status_code != 200:
            return [] if endpoint in {"getVideoList", "getVideoMovieList"} else None
        payload = self._parse_payload(response.text)
        if not payload or payload.get("success") is not True or payload.get("code") != 200:
            return [] if endpoint in {"getVideoList", "getVideoMovieList"} else None
        data = payload.get("data")
        if endpoint in {"getVideoList", "getVideoMovieList"}:
            if isinstance(data, dict) and isinstance(data.get("data"), list):
                return data.get("data")
            if isinstance(data, dict) and isinstance(data.get("list"), list):
                return data.get("list")
            return []
        return data

    def _map_filter_values(self, items):
        values = [{"n": "不限", "v": "0"}]
        for item in items or []:
            title = str((item or {}).get("title") or "").strip()
            if title:
                values.append({"n": title, "v": title})
        return values

    def _build_filters(self, type_data):
        if not isinstance(type_data, dict):
            return {}
        common = [
            {"key": "sc", "name": "影视类型", "value": self._map_filter_values(type_data.get("t1"))},
            {"key": "sd", "name": "制片地区", "value": self._map_filter_values(type_data.get("t2"))},
            {"key": "se", "name": "上映年份", "value": self._map_filter_values(type_data.get("t3"))},
            {"key": "sf", "name": "资源画质", "value": self._map_filter_values(type_data.get("t4"))},
            {"key": "sh", "name": "影视标签", "value": self._map_filter_values(type_data.get("t5"))},
        ]
        return {
            "1": common,
            "2": common + [{"key": "status", "name": "剧集状态", "value": [{"n": "不限", "v": "0"}]}],
        }

    def _normalize_video(self, item):
        data = item or {}
        return {
            "vod_id": str(data.get("doub_id") or data.get("id") or ""),
            "vod_name": data.get("title") or "未知标题",
            "vod_pic": data.get("image") or data.get("epic") or "",
            "vod_remarks": data.get("ejs") or data.get("zqxd") or "",
            "vod_year": data.get("years") or "",
            "vod_content": data.get("abstract") or "",
            "vod_actor": data.get("performer") or "",
            "vod_director": data.get("director") or "",
            "vod_area": data.get("production_area") or "",
        }

    def homeContent(self, filter):
        return {"class": self.classes, "filters": self._build_filters(self._request_api("getVideoTypeList", {}))}

    def homeVideoContent(self):
        items = self._request_api("getVideoList", {"sc": "3", "limit": 20}) or []
        return {"list": [self._normalize_video(item) for item in items]}
