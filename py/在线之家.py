# coding=utf-8
import json
import sys

from base.spider import Spider as BaseSpider

sys.path.append("..")


class Spider(BaseSpider):
    def __init__(self):
        self.name = "在线之家"
        self.host = "https://www.zxzjhd.com"
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/145.0.0.0 Safari/537.36"
            ),
            "Referer": self.host + "/",
        }
        self.classes = [
            {"type_id": "1", "type_name": "电影"},
            {"type_id": "2", "type_name": "美剧"},
            {"type_id": "3", "type_name": "韩剧"},
            {"type_id": "4", "type_name": "日剧"},
            {"type_id": "5", "type_name": "泰剧"},
            {"type_id": "6", "type_name": "动漫"},
        ]
        sort_values = [
            {"n": "时间", "v": "time"},
            {"n": "人气", "v": "hits"},
            {"n": "评分", "v": "score"},
        ]
        self.filter_def = {key: {"cateId": key} for key in ["1", "2", "3", "4", "5", "6"]}
        self.filters = {
            "1": [
                {
                    "key": "class",
                    "name": "剧情",
                    "init": "",
                    "value": [{"n": "全部", "v": ""}, {"n": "喜剧", "v": "喜剧"}],
                },
                {
                    "key": "area",
                    "name": "地区",
                    "init": "",
                    "value": [{"n": "全部", "v": ""}, {"n": "欧美", "v": "欧美"}],
                },
                {
                    "key": "year",
                    "name": "年份",
                    "init": "",
                    "value": [{"n": "全部", "v": ""}, {"n": "2025", "v": "2025"}],
                },
                {"key": "by", "name": "排序", "init": "time", "value": list(sort_values)},
            ],
            "2": [
                {"key": "class", "name": "剧情", "init": "", "value": [{"n": "全部", "v": ""}]},
                {
                    "key": "year",
                    "name": "年份",
                    "init": "",
                    "value": [{"n": "全部", "v": ""}, {"n": "2025", "v": "2025"}],
                },
                {"key": "by", "name": "排序", "init": "time", "value": list(sort_values)},
            ],
            "3": [
                {"key": "class", "name": "剧情", "init": "", "value": [{"n": "全部", "v": ""}]},
                {
                    "key": "year",
                    "name": "年份",
                    "init": "",
                    "value": [{"n": "全部", "v": ""}, {"n": "2025", "v": "2025"}],
                },
                {"key": "by", "name": "排序", "init": "time", "value": list(sort_values)},
            ],
            "4": [
                {"key": "class", "name": "剧情", "init": "", "value": [{"n": "全部", "v": ""}]},
                {
                    "key": "year",
                    "name": "年份",
                    "init": "",
                    "value": [{"n": "全部", "v": ""}, {"n": "2025", "v": "2025"}],
                },
                {"key": "by", "name": "排序", "init": "time", "value": list(sort_values)},
            ],
            "5": [
                {
                    "key": "year",
                    "name": "年份",
                    "init": "",
                    "value": [{"n": "全部", "v": ""}, {"n": "2025", "v": "2025"}],
                },
                {"key": "by", "name": "排序", "init": "time", "value": list(sort_values)},
            ],
            "6": [
                {"key": "class", "name": "剧情", "init": "", "value": [{"n": "全部", "v": ""}]},
                {"key": "area", "name": "地区", "init": "", "value": [{"n": "全部", "v": ""}]},
                {
                    "key": "year",
                    "name": "年份",
                    "init": "",
                    "value": [{"n": "全部", "v": ""}, {"n": "2025", "v": "2025"}],
                },
                {"key": "by", "name": "排序", "init": "time", "value": list(sort_values)},
            ],
        }

    def init(self, extend=""):
        return None

    def getName(self):
        return self.name

    def homeContent(self, filter):
        return {"class": self.classes, "filters": self.filters}

    def homeVideoContent(self):
        return {"list": []}

    def _normalize_ext(self, extend):
        if isinstance(extend, dict):
            return extend
        if not extend:
            return {}
        try:
            return json.loads(str(extend))
        except Exception:
            return {}

    def _build_url(self, value):
        raw = str(value or "").strip()
        if not raw:
            return ""
        if raw.startswith(("http://", "https://")):
            return raw
        if raw.startswith("//"):
            return "https:" + raw
        if raw.startswith("/"):
            return self.host + raw
        return self.host + "/" + raw

    def _build_category_url(self, tid, pg, extend):
        values = dict(self.filter_def.get(str(tid), {"cateId": str(tid)}))
        values.update(self._normalize_ext(extend))
        path = (
            f"{values.get('cateId', tid)}-"
            f"{values.get('area', '')}-"
            f"{values.get('by', '')}-"
            f"{values.get('class', '')}"
            f"-----{int(pg)}---"
            f"{values.get('year', '')}"
        )
        return self._build_url(f"/vodshow/{path}.html")
