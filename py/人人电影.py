# coding=utf-8
import re
import sys
from urllib.parse import urljoin

from base.spider import Spider as BaseSpider

sys.path.append("..")


class Spider(BaseSpider):
    def __init__(self):
        self.name = "人人电影"
        self.host = "https://www.rrdynb.com"
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/136.0.0.0 Safari/537.36"
            ),
            "Referer": self.host + "/",
        }
        self.categories = [
            {"type_id": "movie/list_2", "type_name": "电影"},
            {"type_id": "dianshiju/list_6", "type_name": "电视剧"},
            {"type_id": "dongman/list_13", "type_name": "动漫"},
            {"type_id": "zongyi/list_10", "type_name": "老电影"},
        ]
        self.supported_pan_patterns = [
            r"pan\.baidu\.com|yun\.baidu\.com",
            r"pan\.quark\.cn",
            r"drive\.uc\.cn",
            r"115\.com",
            r"123pan\.com|123684\.com|123865\.com|123912\.com",
            r"cloud\.189\.cn",
            r"yun\.139\.com",
        ]
        self.excluded_pan_patterns = [
            r"pan\.xunlei\.com",
            r"aliyundrive\.com",
            r"alipan\.com",
        ]

    def init(self, extend=""):
        return None

    def getName(self):
        return self.name

    def homeContent(self, filter):
        return {"class": self.categories}

    def homeVideoContent(self):
        return {"list": []}

    def _build_url(self, path):
        raw = str(path or "").strip()
        if not raw:
            return ""
        if raw.startswith(("http://", "https://")):
            return raw
        return urljoin(self.host + "/", raw)

    def _clean_search_title(self, text):
        return str(text or "").replace("<font color='red'>", "").replace("</font>", "").strip()

    def _normalize_title(self, raw_title):
        cleaned = self._clean_search_title(raw_title)
        matched = re.search(r"《(.*?)》|「(.*?)」", cleaned)
        if matched:
            return (matched.group(1) or matched.group(2) or "").strip()
        return cleaned.strip()

    def _is_supported_pan_url(self, url):
        raw = str(url or "").strip()
        if not raw:
            return False
        if any(re.search(pattern, raw, re.I) for pattern in self.excluded_pan_patterns):
            return False
        return any(re.search(pattern, raw, re.I) for pattern in self.supported_pan_patterns)
