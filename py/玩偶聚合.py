# coding=utf-8
import base64
import json
import os
import re
import sys

from base.spider import Spider as BaseSpider

sys.path.append("..")


class Spider(BaseSpider):
    def __init__(self):
        self.name = "玩偶聚合"
        self.filter_root = os.path.join(os.path.dirname(__file__), "../筛选")
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/136.0.0.0 Safari/537.36"
            )
        }
        self.site_priority = [
            "wanou",
            "muou",
            "labi",
            "zhizhen",
            "erxiao",
            "huban",
            "kuaiying",
            "shandian",
            "ouge",
        ]
        self.sites = [
            {
                "id": "wanou",
                "name": "玩偶",
                "domains": ["https://www.wogg.net"],
                "filter_files": ["wogg.json"],
                "default_categories": [("1", "电影"), ("2", "电视剧"), ("3", "动漫"), ("4", "综艺")],
            },
            {
                "id": "muou",
                "name": "木偶",
                "domains": ["https://www.muou.site"],
                "filter_files": ["mogg.json"],
                "default_categories": [("1", "电影"), ("2", "电视剧"), ("3", "动漫"), ("29", "综艺")],
            },
            {
                "id": "labi",
                "name": "蜡笔",
                "domains": ["http://xiaocge.fun"],
                "filter_files": ["labi.json"],
                "default_categories": [("1", "电影"), ("2", "电视剧"), ("3", "动漫"), ("4", "综艺")],
            },
        ]

    def init(self, extend=""):
        return None

    def getName(self):
        return self.name

    def homeVideoContent(self):
        return {"list": []}

    def _load_local_filter_groups(self, site):
        return []

    def _build_site_filters(self, site):
        groups = [
            {
                "key": "categoryId",
                "name": "分类",
                "init": site["default_categories"][0][0],
                "value": [{"n": "全部", "v": ""}]
                + [{"n": name, "v": cid} for cid, name in site["default_categories"]],
            }
        ]
        groups.extend(self._load_local_filter_groups(site))
        return groups

    def homeContent(self, filter):
        classes = [{"type_id": f"site_{site['id']}", "type_name": site["name"]} for site in self.sites]
        filters = {f"site_{site['id']}": self._build_site_filters(site) for site in self.sites}
        return {"class": classes, "filters": filters}

    def _encode_site_vod_id(self, site_id, path):
        return f"site:{site_id}:{path}"

    def _decode_site_vod_id(self, value):
        prefix, site_id, path = str(value).split(":", 2)
        if prefix != "site":
            raise ValueError("not site vod id")
        return {"site": site_id, "path": path}

    def _encode_aggregate_vod_id(self, payload):
        raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        return "agg:" + base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")

    def _decode_aggregate_vod_id(self, value):
        encoded = str(value)[4:]
        padded = encoded + "=" * (-len(encoded) % 4)
        return json.loads(base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8"))

    def _normalize_title(self, value):
        text = str(value or "").lower()
        text = re.sub(r"(4k|hdr|2160p|1080p|720p|玩偶|木偶|蜡笔)", "", text, flags=re.I)
        text = re.sub(r"[\s\-_.·,，。!！?:：()（）\[\]]+", "", text)
        return text

    def _is_same_title(self, left, right):
        left_year = str(left.get("vod_year") or "").strip()
        right_year = str(right.get("vod_year") or "").strip()
        if left_year and right_year and left_year != right_year:
            return False
        return self._normalize_title(left.get("vod_name")) == self._normalize_title(right.get("vod_name"))
