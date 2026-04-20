# coding=utf-8
import re
import sys
from urllib.parse import quote, urljoin

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

    def _request_html(self, path_or_url):
        target = path_or_url if str(path_or_url).startswith("http") else self._build_url(path_or_url)
        response = self.fetch(target, headers=dict(self.headers), timeout=10)
        if response.status_code != 200:
            return ""
        return response.text or ""

    def _clean_text(self, text):
        return re.sub(r"\s+", " ", str(text or "").replace("\xa0", " ")).strip()

    def _parse_cards(self, html):
        root = self.html(html)
        if root is None:
            return []

        items = []
        seen = set()
        for node in root.xpath("//*[@id='movielist']//li"):
            href = "".join(node.xpath(".//*[contains(@class,'intro')]//h2//a[1]/@href")).strip()
            title = (
                "".join(node.xpath(".//*[contains(@class,'intro')]//h2//a[1]/@title")).strip()
                or "".join(node.xpath(".//*[contains(@class,'intro')]//h2//a[1]//text()")).strip()
            )
            pic = (
                "".join(node.xpath(".//*[contains(@class,'pure-img')][1]/@data-original")).strip()
                or "".join(node.xpath(".//*[contains(@class,'pure-img')][1]/@src")).strip()
                or "".join(node.xpath(".//*[contains(@class,'pure-img')]//img[1]/@data-original")).strip()
                or "".join(node.xpath(".//*[contains(@class,'pure-img')]//img[1]/@src")).strip()
                or "".join(node.xpath(".//*[contains(@class,'pure-u-5-24')]//img[1]/@data-original")).strip()
                or "".join(node.xpath(".//*[contains(@class,'pure-u-5-24')]//img[1]/@src")).strip()
            )
            remarks = self._clean_text("".join(node.xpath(".//*[contains(@class,'dou')][1]//text()")))
            if not href or not title or href in seen:
                continue
            seen.add(href)
            items.append(
                {
                    "vod_id": href,
                    "vod_name": self._normalize_title(title),
                    "vod_pic": self._build_url(pic),
                    "vod_remarks": remarks,
                }
            )
        return items

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg)
        class_path = str(tid or "").lstrip("/")
        url = self._build_url(f"{class_path}_{page}.html")
        items = self._parse_cards(self._request_html(url))
        return {"page": page, "limit": len(items), "total": page * 20 + len(items), "list": items}

    def searchContent(self, key, quick, pg="1"):
        page = int(pg)
        keyword = self._clean_text(key)
        if not keyword:
            return {"page": page, "total": 0, "list": []}

        url = self._build_url(f"/plus/search.php?q={quote(keyword)}&pagesize=10&submit=")
        if page > 1:
            url += f"&PageNo={page}"

        items = self._parse_cards(self._request_html(url))
        return {"page": page, "total": len(items), "list": items}
